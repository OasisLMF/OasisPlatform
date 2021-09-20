import asyncio
import logging
from typing import List

import autoscaler_rules
from cluster_client import ClusterClient
from models import QueueStatusContentEntry, RunningAnalysis, ModelState
from oasis_client import OasisClient
from worker_deployments import WorkerDeployment, WorkerDeployments


class AutoScaler:

    """
    TODO doc
    """

    def __init__(self, deployments: WorkerDeployments, cluster: ClusterClient, oasis_client: OasisClient):
        self.deployments = deployments
        self.cluster = cluster
        self.oasis_client = oasis_client

        self.cleanup_timer = None
        self.cleanup_deployments = set()

    async def process_queue_status_message(self, msg):
        """
        Processes a message sent from the web socket

        :param msg: The message content
        """

        running_analyses: [RunningAnalysis] = await self.parse_running_analyses(msg)

        logging.info("Analyses running: %s", running_analyses)

        model_states = self.sum_info_per_model(running_analyses)

        logging.debug("Model statuses: %s", model_states)

        await self._scale_models(model_states)

    # TODO
    def sum_info_per_model(self, analyses: []) -> dict:
        model_states = {}

        # Add all models from oasis API
        for analysis in analyses.values():
            for queue_name in analysis['queue_names']:
                queue_name = queue_name.lower()
                model_state = model_states.get(queue_name, None)
                if model_state:
                    model_state['tasks'] += analysis['tasks']
                    model_state['analyses'] += 1
                else:
                    model_states[queue_name] = ModelState(tasks=analysis['tasks'], analyses=1)

        # Add all deployments missing in Oasis API (currently not running)
        for wd in self.deployments.worker_deployments:

            id = wd.id_string()

            if id not in model_states:
                model_state = ModelState(tasks=0, analyses=0)
                model_states[id] = model_state

        return model_states

    async def _scale_deployment(self, wd: WorkerDeployment, analysis_in_progress: bool, model_state: ModelState):
        """
        Update a worker deployments number of replicas, based on what autoscaler_rules returns as desired number
        of replicas (if changed since laste time).

        :param wd: The WorkerDeployment for this model.
        :param analysis_in_progress: Is an analysis currently running for this model?
        :param model_state: Number of chunks available to be processed by the worker pool for this model.
        :return:
        """

        desired_replicas = 0

        if analysis_in_progress:

            logging.info('Analysis for model %s is running', wd.name)

            try:
                desired_replicas = autoscaler_rules.get_desired_worker_count(wd.auto_scaling, model_state)
            except ValueError as e:
                logging.error('Could not calculate desired replicas count for model %s: %s', wd.id_string(), str(e))

        if desired_replicas > 0 and wd.name in self.cleanup_deployments:
            print('desired replicas > 0. wd.name: ' + wd.name + ', cleanups: ' + str(self.cleanup_deployments))
            if wd.name in self.cleanup_deployments:
                print('Removed ' + wd.name + ' from cleanup')
                self.cleanup_deployments.remove(wd.name)

        if wd.replicas != desired_replicas:

            if desired_replicas > 0:
                await self.cluster.set_replicas(wd.name, desired_replicas)
            else:
                if self.cleanup_timer:
                    print('reset timer')
                    self.cleanup_timer.cancel()
                    self.cleanup_timer = None

                self.cleanup_deployments.add(wd.name)

                loop = asyncio.get_event_loop()
                self.cleanup_timer = loop.call_later(20, self.cleanup) # TODO 20 and doc

                print('cleanuped scheudled: ' + str(self.cleanup_deployments))

    def cleanup(self):

        logging.info('start cleanup: %s', str(self.cleanup_deployments))

        loop = asyncio.get_event_loop()

        for name in self.cleanup_deployments:
            loop.create_task(self.cluster.set_replicas(name, 0))

        self.cleanup_deployments.clear()

        logging.info('cleanup: %s', str(self.cleanup_deployments))

    async def parse_running_analyses(self, msg) -> [RunningAnalysis]:
        content: List[QueueStatusContentEntry] = msg['content']

        running_analyses: [RunningAnalysis] = {}

        for entry in content:
            analyses_list = entry['analyses']

            for analysis_entry in analyses_list:
                analysis = analysis_entry['analysis']
                tasks = analysis['sub_task_count']

                queue_names = set()
                sub_task_statuses = analysis['sub_task_statuses']
                if sub_task_statuses and len(sub_task_statuses) > 0:
                    for sub_task in sub_task_statuses:
                        if sub_task['status'] != 'COMPLETED':
                            queue_names.add(sub_task['queue_name'])

                if tasks and tasks > 0 and len(queue_names) > 0:
                    sa_id = analysis['id']
                    if sa_id not in running_analyses:
                        running_analyses[sa_id] = RunningAnalysis(id=analysis['id'], tasks=tasks, queue_names=list(queue_names))

        return running_analyses

    async def _scale_models(self, model_states: dict):

        for model, state in model_states.items():

            wd = await self.deployments.get_worker_deployment_by_name_id(model)

            if wd:

                # Load auto scaling settings everytime we scale up workers from 0
                if not wd.auto_scaling or wd.replicas == 0:
                    if not wd.oasis_model_id:

                        logging.info("Get oasis model id from API for model %s", wd.id_string())

                        wd.oasis_model_id = await self.oasis_client.get_oasis_model_id(wd.supplier_id, wd.model_id, wd.model_version_id)
                        if not wd.oasis_model_id:
                            logging.error("No model id found for model %s", wd.id_string())

                    if wd.oasis_model_id:

                        logging.info("Loading auto scaling settings from API for model %s", wd.id_string())
                        wd.auto_scaling = await self.oasis_client.get_auto_scaling(wd.oasis_model_id)

                if wd.auto_scaling:
                    analysis_in_progress = state.get('tasks', 0) > 0
                    await self._scale_deployment(wd, analysis_in_progress, state)
                else:
                    logging.warning("No auto scaling setting found for model %s", wd.id_string())

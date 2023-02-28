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
    This class handles the actual worker scaling. Summary of flow:

    1. A websocket queue-status message is sent to process_queue_status_message.
    2. The message is parsed and information such as number of analyses and tasks per model is saved.
    3. For each model:
    3.1. If the model is running:
    3.1.1. Calculate de desired worker count (desired replicas) and update the deployments replicas setting.
    3.2. If the model is not running:
    3.1.1. Add a delayed(20s) shutdown of all workers. It is aborted if any new analysis/tasks get submitted.
    """

    def __init__(self, deployments: WorkerDeployments, cluster: ClusterClient, oasis_client: OasisClient,
                 prioritized_models_limit: int, limit: int, continue_update_scaling: bool,
                 never_shutdown_fixed_workers: bool):

        self.deployments = deployments
        self.cluster = cluster
        self.oasis_client = oasis_client
        self.prioritized_models_limit = int(prioritized_models_limit) if prioritized_models_limit else None
        self.limit = int(limit) if limit else None
        self.continue_update_scaling = continue_update_scaling
        self.never_shutdown_fixed_workers = never_shutdown_fixed_workers

        # Cleanup timer used to remove all workers for a model with a delay.
        self.cleanup_timer = None
        # Worker deployment names to be scaled to 0 in next cleanup cycle.
        self.cleanup_deployments = set()

    async def process_queue_status_message(self, msg):
        """
        Processes a message sent from the web socket

        :param msg: The message content
        """

        running_analyses: [RunningAnalysis] = await self.parse_running_analyses(msg)

        logging.info('Analyses running: %s', running_analyses)

        model_states = self._aggregate_model_states(running_analyses)

        logging.debug('Model statuses: %s', model_states)

        model_states_with_wd = await self._filter_model_states_with_wd(model_states)
        prioritized_models = self._clear_unprioritized_models(model_states_with_wd)

        await self._scale_models(prioritized_models)

    def _aggregate_model_states(self, analyses: []) -> dict:
        """
        Aggregate the list of running analyses and return a dict with the model and its state.

        :param analyses: List of running analyses
        :return: Model states
        """

        model_states = {}

        # Add all models from oasis API
        for analysis in analyses.values():
            for queue_name in analysis['queue_names']:
                queue_name = queue_name.lower()
                model_state = model_states.get(queue_name, None)
                priority = analysis.get('priority', 1)
                if model_state:
                    model_state['tasks'] += analysis['tasks']
                    model_state['analyses'] += 1
                    if priority > model_state['priority']:
                        model_state['priority'] = priority
                else:
                    model_states[queue_name] = ModelState(tasks=analysis['tasks'], analyses=1, priority=priority)

        # Add all deployments missing in Oasis API (currently not running)
        for wd in self.deployments.worker_deployments:

            id = wd.id_string()

            if id not in model_states:
                model_state = ModelState(tasks=0, analyses=0, priority=1)
                model_states[id] = model_state

        return model_states

    async def _scale_deployment(self, wd: WorkerDeployment, analysis_in_progress: bool, model_state: ModelState, limit: int) -> int:
        """
        Update a worker deployments number of replicas, based on what autoscaler_rules returns as desired number
        of replicas (if changed since laste time).

        :param wd: The WorkerDeployment for this model.
        :param analysis_in_progress: Is an analysis currently running for this model?
        :param model_state: Number of taks available to be processed by the worker pool for this model.
        :param limit: None or maximum value of total number of replicas/workers for this model deployment.
        :return: Number of replicas set on deployment
        """

        desired_replicas = 0
        is_fixed_strategy = wd.auto_scaling.get('scaling_strategy') == 'FIXED_WORKERS' and self.never_shutdown_fixed_workers

        if analysis_in_progress or is_fixed_strategy:

            if analysis_in_progress:
                logging.info('Analysis for model %s is running', wd.name)
            if is_fixed_strategy:
                logging.info('Model %s is set to "FIXED_WORKERS"', wd.name)

            try:
                desired_replicas = autoscaler_rules.get_desired_worker_count(wd.auto_scaling, model_state)

                if limit is not None and desired_replicas > limit:
                    desired_replicas = limit
            except ValueError as e:
                logging.error('Could not calculate desired replicas count for model %s: %s', wd.id_string(), str(e))

        if desired_replicas > 0 and wd.name in self.cleanup_deployments:

            if wd.name in self.cleanup_deployments:
                self.cleanup_deployments.remove(wd.name)

        if wd.replicas != desired_replicas:

            if desired_replicas > 0:
                await self.cluster.set_replicas(wd.name, desired_replicas)
            else:
                if self.cleanup_timer:
                    self.cleanup_timer.cancel()
                    self.cleanup_timer = None

                self.cleanup_deployments.add(wd.name)

                loop = asyncio.get_event_loop()
                self.cleanup_timer = loop.call_later(20, self._cleanup)

                return wd.replicas

        return desired_replicas

    def _cleanup(self):
        """
        Timer function to shutdown workers with a delay from the last finished analysis. Shutdown is made by setting
        the worker deployments replicas attribute to 0.
        """

        if len(self.cleanup_deployments) > 0:

            logging.info('Start cleanup of: %s', str(self.cleanup_deployments))

            loop = asyncio.get_event_loop()

            for name in self.cleanup_deployments:
                loop.create_task(self.cluster.set_replicas(name, 0))

            self.cleanup_deployments.clear()

    async def parse_running_analyses(self, msg) -> [RunningAnalysis]:
        """
        Parse the web socket message and return a list of running analyses.

        :param msg: Web socket message
        :return: A list of running analyses and their tasks.
        """
        content: List[QueueStatusContentEntry] = msg['content']

        running_analyses: [RunningAnalysis] = {}

        for entry in content:
            analyses_list = entry['analyses']

            for analysis_entry in analyses_list:
                analysis = analysis_entry['analysis']
                tasks = analysis.get('sub_task_count', 0)

                queue_names = set()
                task_counts = analysis.get('status_count', {})
                tasks_in_queue = task_counts.get('TOTAL_IN_QUEUE', 0)
                if tasks_in_queue > 0:
                    queue_names = analysis.get('queue_names', [])

                ## REPLACED: with the code block above  ############
                # queue_names = set()
                # sub_task_statuses = analysis['sub_task_statuses']
                # if sub_task_statuses and len(sub_task_statuses) > 0:
                #    for sub_task in sub_task_statuses:
                #        if sub_task['status'] != 'COMPLETED':
                #            queue_names.add(sub_task['queue_name'])
                ####################################################

                if tasks and tasks > 0 and len(queue_names) > 0:
                    sa_id = analysis['id']
                    if sa_id not in running_analyses:
                        priority = int(analysis.get('priority', 1))
                        running_analyses[sa_id] = RunningAnalysis(id=analysis['id'], tasks=tasks, queue_names=list(queue_names), priority=priority)

        return running_analyses

    async def _scale_models(self, prioritized_models):
        """
        Iterate model_states and scale each models worker deployment based on the state and autoscaling configuration.
        The server API is queried if needed to fetch oasis model id and auto scaling settings.

        :param prioritized_models: A dict of model names and their states.
        """

        workers_total = 0

        for model, state, wd in prioritized_models:

            # Load auto scaling settings everytime we scale up workers from 0
            if not wd.auto_scaling or wd.replicas == 0 or self.continue_update_scaling:
                if not wd.oasis_model_id:

                    logging.info('Get oasis model id from API for model %s', wd.id_string())

                    wd.oasis_model_id = await self.oasis_client.get_oasis_model_id(wd.supplier_id, wd.model_id, wd.model_version_id)
                    if not wd.oasis_model_id:
                        logging.error('No model id found for model %s', wd.id_string())

                if wd.oasis_model_id:

                    wd.auto_scaling = await self.oasis_client.get_auto_scaling(wd.oasis_model_id)

            if wd.auto_scaling:
                analysis_in_progress = state.get('tasks', 0) > 0
                replicas_limit = self.limit - workers_total if self.limit else None

                workers_created = await self._scale_deployment(wd, analysis_in_progress, state, replicas_limit)
                workers_total += workers_created
            else:
                logging.warning('No auto scaling setting found for model %s', wd.id_string())

        logging.info('Total desired number of workers: ' + str(workers_total))

    def _get_highest_model_priorities(self, model_states_with_wd):
        """
        Return the highest priority levels if:
         - Multiple analyses are run with different priority.
         - OASIS_PRIORITIZED_MODELS_LIMIT is enabled.

        :param model_states_with_wd: List of (model, model state, WorkerDeployment)
        :return: The highest priority levels for these runs.
        """
        if self.prioritized_models_limit:
            priorities = sorted(list(set(map(lambda ms: ms[1].get('priority', 1), model_states_with_wd))), reverse=True)
            if len(priorities) > 1:
                priorities = priorities[0:self.prioritized_models_limit]
                return priorities
        return None

    def _clear_unprioritized_models(self, model_states_with_wd):
        """
        Reset tasks and analyses for models with less important runs if OASIS_PRIORITIZED_MODELS_LIMIT is enabled.
        This will focus on and prioritize analyses with higher priority level than others.

        :param model_states_with_wd: List of (model, model state, WorkerDeployment)
        :return: Same models as input model_states_with_wd, but with changed values for models with less priority.
        """

        priorities = self._get_highest_model_priorities(model_states_with_wd)

        if not priorities:
            return model_states_with_wd
        else:
            result = []

            for model, state, wd in model_states_with_wd:
                if priorities and state.get('priority') in priorities:
                    result.append((model, state, wd), )
                else:
                    result.append((model, ModelState(tasks=0, analyses=0, priority=1), wd))

            return result

    async def _filter_model_states_with_wd(self, model_states):
        """
        Filter and exclude models with no worker deployment in the cluster and return a list of
        tuples (model, state, WorkerDeployment)

        :param model_states: List of model states
        :return: Models with an attached WorkerDeployment.
        """

        result = []

        for model, state in model_states.items():

            wd = await self.deployments.get_worker_deployment_by_name_id(model)

            if wd:
                result.append((model, state, wd), )

        return result

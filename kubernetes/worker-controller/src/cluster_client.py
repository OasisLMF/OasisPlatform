"""
This file contains a kubernetes cluster client and a deployment watcher to monitor worker deployment changes.
"""

import asyncio
import logging

from kubernetes_asyncio import client, config
from kubernetes_asyncio.client import ApiClient, ApiException
from kubernetes_asyncio.config import ConfigException
from kubernetes_asyncio.watch import watch

from worker_deployments import WorkerDeployments


class ClusterClient:
    """
    A simple Kubernetes (wrapper) client to load configuration and update number of replicas.
    """

    def __init__(self, namespace: str):
        self.apps_v1 = None
        self.namespace = namespace

    async def load_config(self, cluster):
        """
        Load configuration for connecting to kubernetes. Depending on how this application is run we need to
        support two ways of configurations.

        :param cluster: Either 'in' if this app is run as a pod in a kubernets cluster, or 'local' (or something
        else) to connect to a local cluster on your machine.

        """

        self.apps_v1 = client.AppsV1Api()

        try:
            if cluster == 'in':
                config.load_incluster_config()
            else:
                await config.load_kube_config()
        except ConfigException as e:
            asyncio.get_event_loop().stop()
            logging.exception('Could not connect to cluster: %s', e)
            raise Exception('Could not connect co cluster', e)

    async def set_replicas(self, name: str, replicas: int):
        """
        Set the replicas attribute of a deployment. Replicas is the same as number of workers.

        :param name: Deployment name
        :param replicas: number of replicas/workers.
        :return:
        """

        logging.info('Scale %s to %s replicas', name, replicas)

        async with ApiClient() as api:
            apps_v1 = client.AppsV1Api(api)
            await apps_v1.patch_namespaced_deployment_with_http_info(name=name, namespace=self.namespace, body={
                'spec': {
                    'replicas': replicas
                }
            })


class DeploymentWatcher:
    """
    This class monitors the kubernetes cluster to detect and collect changes related to worker deployments. It's goal
    is to keep an updated cache about the state of the cluster such as available worker deployments, replicas etc.
    """

    def __init__(self, namespace: str, deployments: WorkerDeployments):
        self.namespace = namespace
        self.deployments = deployments

    async def watch(self):
        """
        Listen to the kubernetes API watch endpoint. It needs to be restarted continuously, hence the timeout.

        """

        apps_v1 = client.AppsV1Api()
        w = watch.Watch()

        keep_watching = True
        while keep_watching:
            try:
                async for event in w.stream(apps_v1.list_namespaced_deployment, namespace=self.namespace,
                                            label_selector='oasislmf/type=worker', timeout_seconds=60):

                    deployment = event['object']

                    try:
                        await self.update_deployment(event['object'], type=event['type'])
                    except Exception:
                        logging.exception('Failed to parse deployment: %s', deployment)

            except ApiException as error:
                logging.warning('Failed to watch deployments: %s', error.reason)
                keep_watching = False

        logging.error('Stopped watching kubernetes')
        w.stop()
        w.close()

        asyncio.get_event_loop().stop()

    async def update_deployment(self, deployment, type=None):
        """
        Each update received from kubernetes is parsed in here, and updates our cache in self.deployments.

        :param deployment: The updated deployment received from kubernetes
        :param type: DELETE/ADD or UPDATE
        :return:
        """

        name = deployment.metadata.name

        if type == 'DELETED':

            await self.deployments.delete(name)
        else:

            replicas = deployment.spec.replicas
            labels = deployment.metadata.labels
            supplier_id = labels.get('oasislmf/supplier-id', '')
            model_id = labels.get('oasislmf/model-id', '')
            model_version_id = labels.get('oasislmf/model-version-id', '')

            await self.deployments.update_worker(name, supplier_id, model_id, model_version_id, replicas)

    async def load_deployments(self):
        """
        Reads all available worker deployments in the cluster. Used on startup to collect the deployments before
        starting the watch for changes.
        """
        async with ApiClient() as api:
            apps_v1 = client.AppsV1Api(api)
            ret = (await apps_v1.list_namespaced_deployment(self.namespace, label_selector='oasislmf/type=worker'))
            for deployment in ret.items:
                await self.update_deployment(deployment)

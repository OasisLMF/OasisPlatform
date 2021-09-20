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

    def __init__(self):
        self.apps_v1 = None

    async def load_config(self, args):

        self.apps_v1 = client.AppsV1Api()

        try:
            if args.cluster == 'in':
                config.load_incluster_config()
            else:
                await config.load_kube_config()
        except ConfigException as e:
            asyncio.get_event_loop().stop()
            logging.exception("Could not connect to cluster: %s", e)
            raise Exception('Could not connect co cluster', e)

    async def set_replicas(self, name, replicas):

        logging.info("Scale %s to %s replicas", name, replicas)

        async with ApiClient() as api:

            apps_v1 = client.AppsV1Api(api)
            await apps_v1.patch_namespaced_deployment_with_http_info(name=name, namespace="default", body={
                "spec": {
                    "replicas": replicas
                }
            })


class DeploymentWatcher:

    def __init__(self, deployments: WorkerDeployments):
        self.deployments = deployments

    async def watch(self):

        apps_v1 = client.AppsV1Api()
        w = watch.Watch()

        keep_watching = True
        while keep_watching:
            try:
                async for event in w.stream(apps_v1.list_namespaced_deployment, namespace="default", label_selector="oasislmf/type=worker", timeout_seconds=60):

                    deployment = event['object']

                    try:
                        await self.update_deployment(event['object'], type=event['type'])
                    except Exception:
                        logging.exception("Failed to parse deployment: %s", deployment)

            except ApiException as error:
                logging.warning("Failed to watch deployments: %s", error.reason)
                keep_watching = False

        logging.error("Stopped watching kubernetes")
        w.stop()
        w.close()

        asyncio.get_event_loop().stop()

    async def update_deployment(self, deployment, type=None):

        name = deployment.metadata.name

        if type == 'DELETED':

            await self.deployments.delete(name)
        else:

            replicas = deployment.spec.replicas
            labels = deployment.metadata.labels
            supplier_id = labels.get('oasislmf/supplier-id', '')
            model_id = labels.get('oasislmf/model-id', '')
            model_version_id = labels.get('oasislmf/model-version-id', '')

            # auto_scaling = {
            #     key[len('oasislmf-autoscaling/'):]: value for (key, value) in deployment.metadata.annotations.items() if key.startswith('oasislmf-autoscaling/')
            # }
            # if len(auto_scaling) == 0 or 'type' not in auto_scaling:
            #     logging.warning("No auto scaling enabled for model supplier_id=%s, model_id=%s, model_version_id=%s - will default to 1 worker", supplier_id, model_id, model_version_id)

            await self.deployments.update_worker(name, supplier_id, model_id, model_version_id, replicas)

    async def load_deployments(self):
        async with ApiClient() as api:
            apps_v1 = client.AppsV1Api(api)
            ret = (await apps_v1.list_namespaced_deployment("default", label_selector="oasislmf/type=worker"))
            for deployment in ret.items:
                await self.update_deployment(deployment)

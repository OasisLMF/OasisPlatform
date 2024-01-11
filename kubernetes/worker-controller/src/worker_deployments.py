"""
This file contains classes to cache the models and worker deployments available the platform.
"""

import logging


class WorkerDeployment:
    """
    Represents a worker deployment in the kubernetes cluster. Each update is replicated to this object. The auto_scaling
    is actually not a part of the worker deployment in the cluster, it comes from the API, but kept here anyway.
    """

    def __init__(self, name: str, supplier_id: str, model_id: str, model_version_id: str, api_version: str = None):
        self.name = name
        self.supplier_id = supplier_id
        self.model_id = model_id
        self.model_version_id = model_version_id
        self.api_version = api_version
        self.oasis_model_id: int = None
        self.replicas: int = None
        self.auto_scaling = None

    def id_string(self):
        if self.api_version is None:
            return f'{self.supplier_id}-{self.model_id}-{self.model_version_id}'.lower()
        return f'{self.supplier_id}-{self.model_id}-{self.model_version_id}-{self.api_version}'.lower()


class WorkerDeployments:

    """
    This class keeps all worker deployments available in the cluster.
    """

    def __init__(self, args):
        """
        :param args: Parsed command line arguments
        """
        self.worker_deployments: [WorkerDeployment] = []
        self.api_host = args.api_host
        self.api_port = args.api_port
        self.username = args.username
        self.password = args.password

    async def update_worker(self, name, supplier_id, model_id, model_version_id, api_version, replicas: int):
        """
        Update the cache of worker deployments. Create a new if not found or update an already existing one.

        :param name: Deployment name in kubernetes
        :param supplier_id: Model supplier id
        :param model_id: Model id
        :param model_version_id: Model version
        :param api_version: 'V1' or 'V2' depening on the worker type
        :param replicas: Number of replicas currenty in kubernetes.
        :param auto_scaling: Auto scaling settings for this worker deployment if available.
        :return:
        """

        new_deployment = False
        model_id_string = f'{supplier_id}-{model_id}-{model_version_id}-{api_version}'

        wd: WorkerDeployment = self.get_worker_deployment(supplier_id, model_id, model_version_id, api_version)
        if wd is None:
            new_deployment = True
            wd = WorkerDeployment(name, supplier_id, model_id, model_version_id, api_version)
            self.worker_deployments.append(wd)
            logging.info('Deployment %s: New', model_id_string)

        if not new_deployment:
            if wd.replicas != replicas:
                logging.info('Deployment %s: updated replicas: %s', model_id_string, replicas)

        wd.replicas = replicas

    def get_worker_deployment(self, supplier_id, model_id, model_version_id, api_version=None) -> WorkerDeployment:
        """
        Return the WorkerDeployment for the given supplier, model and version.

        :param supplier_id: Model supplier id
        :param model_id: Model id
        :param model_version_id: Model version
        :param api_version: Worker API type 'v1' / 'v2'
        :return: A WorkerDeployment or None if not found.
        """
        # Check API version for match
        if api_version is not None:
            for wd in self.worker_deployments:
                if all([wd.supplier_id.lower() == supplier_id.lower(),
                        wd.model_id.lower() == model_id.lower(),
                        wd.model_version_id.lower() == model_version_id.lower(),
                        wd.api_version.lower() == api_version.lower()]):
                    return wd

        # return any matching model (ignore API version)
        else:
            for wd in self.worker_deployments:
                if all([wd.supplier_id.lower() == supplier_id.lower(),
                        wd.model_id.lower() == model_id.lower(),
                        wd.model_version_id.lower() == model_version_id.lower()]):
                    return wd

    async def get_worker_deployment_by_name_id(self, name_id: str) -> WorkerDeployment:
        """
        Get WorkerDeployment by concatenated name id with format <supplier>-<model>-<version>.

        :param name_id: String with format <supplier>-<model>-<version>
        :return: A WorkerDeployment or None if not found.
        """
        split = name_id.split('-')
        if len(split) == 3:
            return self.get_worker_deployment(split[0], split[1], split[2])
        if len(split) == 4:
            return self.get_worker_deployment(split[0], split[1], split[2], split[3])

    async def delete(self, name):
        """
        Delete a worker deployment

        :param name: Worker deployment name.
        """

        logging.info('Deployment %s deleted', name)

        self.worker_deployments = list(filter(lambda wd: wd.name != name, self.worker_deployments))

    def print_list(self):
        """
        Print a list of all worker deployments in this object.
        """

        logging.info('Current list of worker deployments:')
        for ws in self.worker_deployments:
            logging.info('- ' + ws.name + ' (replicas: %s)', ws.replicas)

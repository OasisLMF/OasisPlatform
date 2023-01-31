#!/usr/bin/env python3

"""
This application is used by the Oasis Kubernetes platform to control the number of worker pods for each model.

It will use two input sources to monitor the state of the platform and act on changes:

1. The Oasis API (websocket) to get updates regarding runs and their statuses.
2. The Kubernetes cluster to read and update worker deployments.

Each worker deployment has its own auto scaling configuration stored in the oasis API.

This application will update the replicas attribute in the deployment configuration to control the number of
pods. Each worker deployment has its own replicas attribute and kubernetes will monitor changes and start/stop
pods to achieve the correct number of replicas of the deployment. The worker controller will update each worker
deployments replicas attribute according to:

analyses running == 0 - set replicas to 0. This will bring down all workers for this model.
analyses running >= 1 - update replicas and set it to the desired worker count based on the auto scaling configuration.
"""

import argparse
import asyncio
import logging
from os import getenv

from cluster_client import ClusterClient, DeploymentWatcher
from oasis_client import OasisClient
import worker_deployments
from oasis_websocket import OasisWebSocket
from autoscaler import AutoScaler

logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=logging.INFO)


def str2bool(v):
    """ Func type for loading strings to boolean values using argparse
        https://stackoverflow.com/a/43357954
    """
    if v is None:
        return v
    elif isinstance(v, bool):
        return v
    elif v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise ArgumentTypeError('Boolean value expected.')


def parse_args():
    """
    Parse command line arguments.

    :return:
    """
    parser = argparse.ArgumentParser('Oasis example model worker controller')
    parser.add_argument('--api-host', help='The sever API hostname', default=getenv('OASIS_API_HOST') or 'localhost')
    parser.add_argument('--api-port', help='The server API portnumber', default=getenv('OASIS_API_PORT') or 8000)
    parser.add_argument('--secure', help='Flag if https and wss should be used', default=bool(getenv('OASIS_API_SECURE')), action='store_true')
    parser.add_argument('--username', help='The username of the worker controller user', default=getenv('OASIS_USERNAME') or 'admin')
    parser.add_argument('--password', help='The password of the worker controller user', default=getenv('OASIS_PASSWORD') or 'password')
    parser.add_argument('--namespace', help='Namespace of cluster where oasis is deployed to', default=getenv('OASIS_CLUSTER_NAMESPACE') or 'default')
    parser.add_argument('--limit', help='Hard limit for the total number of workers created', default=getenv('OASIS_TOTAL_WORKER_LIMIT'))
    parser.add_argument('--prioritized-models-limit', help='When prioritized runs are used - create workers for the models with the highest priority',
                        default=getenv('OASIS_PRIORITIZED_MODELS_LIMIT'))
    parser.add_argument(
        '--cluster', help='Type of kubernetes cluster to connect to, either "local" (~/.kube/config) or "in" to connect to the cluster the pod exists in', default=getenv('CLUSTER') or 'in')
    parser.add_argument('--continue-update-scaling', help='Auto scaling - read the scaling settings from the API for a model on every update. (for testing)',
                        type=str2bool, default=getenv('OASIS_CONTINUE_UPDATE_SCALING') or False)
    parser.add_argument('--never-shutdown-fixed-workers', help='Auto scaling - never scale to 0 for strategy FIXED_WORKERS.',
                        type=str2bool, default=getenv('OASIS_NEVER_SHUTDOWN_FIXED_WORKERS') or False)

    args = parser.parse_args()

    for key in args.__dict__:
        if args.__dict__[key] is None and key not in ['limit', 'prioritized_models_limit']:
            raise Exception(f'Missing value for {key}')

    if args.cluster != 'in' and args.cluster != 'local':
        raise Exception(f'Unsupported cluster type: {args.cluster}')

    return args


def main():
    """
    Entrypoint. Parse arguments, creates client for oasis and kubernetes cluster and starts tasks to monitor changes.
    """

    args = parse_args()

    # Create an oasis client
    oasis_client = OasisClient(args.api_host, args.api_port, args.secure, args.username, args.password)

    # Cache to keep track of all deployments in the cluster
    deployments: worker_deployments.WorkerDeployments = worker_deployments.WorkerDeployments(args)

    event_loop = asyncio.get_event_loop()

    # Create cluster client and load configuration
    cluster_client = ClusterClient(args.namespace)
    event_loop.run_until_complete(cluster_client.load_config(args.cluster))

    # Create the autoscaler to bind everything together
    autoscaler = AutoScaler(deployments, cluster_client, oasis_client, args.prioritized_models_limit, args.limit,
                            args.continue_update_scaling, args.never_shutdown_fixed_workers)

    # Create the deployment watcher and load all available deployments
    deployments_watcher = DeploymentWatcher(args.namespace, deployments)
    event_loop.run_until_complete(deployments_watcher.load_deployments())
    deployments.print_list()

    # Connect to the oasis api websocket
    oasis_web_socket = OasisWebSocket(oasis_client, autoscaler)

    # Watch changes in the clutser and oasis
    event_loop.create_task(deployments_watcher.watch())
    event_loop.create_task(oasis_web_socket.watch())

    event_loop.run_forever()


if __name__ == '__main__':
    main()

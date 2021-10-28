import asyncio
import json
import logging
import unittest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, call

from autoscaler import AutoScaler
from worker_deployments import WorkerDeployment

logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=logging.INFO)


class TestAutoscaler(unittest.TestCase):
    """
    Test the flow of the autoscaler and that it correctly set the correct number of replicas depending on
    number of runs and their configuration.
    """

    def test_parse_queue_status(self):

        wd1 = WorkerDeployment('worker-oasislmf-piwind-1', 'oasislmf', 'piwind', '1')
        wd2 = WorkerDeployment('worker-oasislmf-piwind-2', 'oasislmf', 'piwind', '2')
        wd3 = WorkerDeployment('worker-oasislmf-piwind-3', 'oasislmf', 'piwind', '3')
        wd1.replicas = 0
        wd2.replicas = 2
        wd3.replicas = 1

        async def get_worker_deployment_by_name_id(model):

            for wd in [wd1, wd2, wd3]:
                if wd.id_string().lower() == model:
                    return wd

        async def get_auto_scaling(oasis_model_id):
            if oasis_model_id == 1:
                return {
                    'scaling_strategy': 'FIXED_WORKERS',
                    'worker_count_fixed': 2
                }
            elif oasis_model_id == 2:
                return {
                    'scaling_strategy': 'QUEUE_LOAD',
                    'worker_count_max': 1
                }
            else:
                return {
                    'unexpected_config': True
                }

        deployments = MagicMock()
        deployments.get_worker_deployment_by_name_id = MagicMock(side_effect=get_worker_deployment_by_name_id)
        deployments.worker_deployments = []
        deployments.worker_deployments.append(wd1)
        deployments.worker_deployments.append(wd2)
        deployments.worker_deployments.append(wd3)

        client = MagicMock()
        client.get_oasis_model_id = AsyncMock(side_effect=lambda sid, mid, mvid: int(mvid))
        client.get_auto_scaling = AsyncMock(side_effect=get_auto_scaling)

        cluster_client = MagicMock()
        cluster_client.set_replicas = AsyncMock()

        queue_status_json = Path(__file__).parent.parent.parent / 'data/test/queue-status.3-fake.json'

        with open(queue_status_json) as json_file:
            data = json.load(json_file)

            autoscaler = AutoScaler(deployments, cluster_client, client)
            asyncio.get_event_loop().run_until_complete(autoscaler.process_queue_status_message(data))

        calls = [call(wd1.name, 2), call(wd2.name, 3), call(wd3.name, 0)]
        cluster_client.set_replicas.assert_has_calls(calls, any_order=True)


if __name__ == '__main__':
    unittest.main()

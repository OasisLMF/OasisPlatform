import asyncio
import json
import logging
import unittest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, call

from autoscaler import AutoScaler
from models import ModelState
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

        queue_status_json = Path(__file__).parent.parent.parent / 'data/test/queue-status-2-running-2-queues.json'

        with open(queue_status_json) as json_file:
            data = json.load(json_file)

            autoscaler = AutoScaler(deployments, cluster_client, client, None, None, False, False)
            asyncio.run(autoscaler.process_queue_status_message(data))

        calls = [call(wd1.name, 2), call(wd2.name, 1)]
        cluster_client.set_replicas.assert_has_calls(calls, any_order=True)

    def test_model_status_prio(self):

        wd1 = WorkerDeployment('worker-oasislmf-piwind-1', 'oasislmf', 'piwind', '1')
        wd2 = WorkerDeployment('worker-oasislmf-piwind-2', 'oasislmf', 'piwind', '2')
        wd1.replicas = 0
        wd2.replicas = 2

        async def get_worker_deployment_by_name_id(model):

            for wd in [wd1, wd2]:
                if wd.id_string().lower() == model:
                    return wd

        deployments = MagicMock()
        deployments.get_worker_deployment_by_name_id = MagicMock(side_effect=get_worker_deployment_by_name_id)
        deployments.worker_deployments = [wd1, wd2]

        autoscaler = AutoScaler(deployments, None, None, 1, None, False, False)

        model_states = {
            'celery': {'tasks': 10, 'analyses': 2, 'priority': 1},
            'model-worker-broadcast': {'tasks': 5, 'analyses': 1, 'priority': 2},
            'oasislmf-piwind-1': {'tasks': 10, 'analyses': 2, 'priority': 2},
            'oasislmf-piwind-2': {'tasks': 5, 'analyses': 1, 'priority': 1},
            'oasislmf-piwind-3': {'tasks': 5, 'analyses': 1, 'priority': 10},
        }

        prioritized_model_states = asyncio.run(autoscaler._filter_model_states_with_wd(model_states))
        self.assertEqual(2, len(prioritized_model_states))
        first = prioritized_model_states[0]
        self.assertEqual('oasislmf-piwind-1', first[0])
        self.assertEqual(10, first[1].get('tasks'))
        self.assertEqual(2, first[1].get('analyses'))
        self.assertEqual(2, first[1].get('priority'))
        second = prioritized_model_states[1]
        self.assertEqual('oasislmf-piwind-2', second[0])
        self.assertEqual(1, second[1].get('priority'))

    def test_get_highest_model_priorities(self):

        model_states_with_wd = [
            ('oasislmf-piwind-1', ModelState(tasks=10, analyses=2, priority=5), None),
            ('oasislmf-piwind-2', ModelState(tasks=10, analyses=2, priority=7), None),
            ('oasislmf-piwind-3', ModelState(tasks=0, analyses=0, priority=1), None),
        ]

        r = AutoScaler(None, None, None, 1, None, False, False)._get_highest_model_priorities(model_states_with_wd)
        self.assertEqual([7], r)

        r = AutoScaler(None, None, None, 2, None, False, False)._get_highest_model_priorities(model_states_with_wd)
        self.assertEqual([7, 5], r)

        r = AutoScaler(None, None, None, 3, None, False, False)._get_highest_model_priorities(model_states_with_wd)
        self.assertEqual([7, 5, 1], r)

        r = AutoScaler(None, None, None, None, None, False, False)._get_highest_model_priorities(model_states_with_wd)
        self.assertEqual(None, r)

    def test_clear_unprioritized_models(self):
        model_states_with_wd = [
            ('oasislmf-piwind-1', ModelState(tasks=10, analyses=2, priority=5), None),
            ('oasislmf-piwind-2', ModelState(tasks=10, analyses=2, priority=7), None),
            ('oasislmf-piwind-3', ModelState(tasks=0, analyses=0, priority=1), None),
        ]

        r = AutoScaler(None, None, None, 1, None, False, False)._clear_unprioritized_models(model_states_with_wd)
        self.assertEqual(len(model_states_with_wd), len(r))
        first = r[0]
        firstState = first[1]
        self.assertEqual('oasislmf-piwind-1', first[0])
        self.assertEqual(0, firstState.get('tasks'))
        self.assertEqual(0, firstState.get('analyses'))
        self.assertEqual(1, firstState.get('priority'))
        second = r[1]
        secondState = second[1]
        self.assertEqual('oasislmf-piwind-2', second[0])
        self.assertEqual(10, secondState.get('tasks'))
        self.assertEqual(2, secondState.get('analyses'))
        self.assertEqual(7, secondState.get('priority'))
        third = r[2]
        thirdState = third[1]
        self.assertEqual('oasislmf-piwind-3', third[0])
        self.assertEqual(0, thirdState.get('tasks'))
        self.assertEqual(0, thirdState.get('analyses'))
        self.assertEqual(1, thirdState.get('priority'))

    def test_continue_update_scaling(self):

        async def get_auto_scaling(oasis_model_id):
            return {
                'scaling_strategy': 'FIXED_WORKERS',
                'worker_count_fixed': 2
            }

        oasis_client = MagicMock()
        oasis_client.get_auto_scaling = AsyncMock(side_effect=get_auto_scaling)

        autoscaler = AutoScaler(None, None, oasis_client, None, None, True, False)
        autoscaler._scale_deployment = AsyncMock()

        wd1 = WorkerDeployment('worker-oasislmf-piwind-1', 'oasislmf', 'piwind', '1')
        wd1.auto_scaling = {
            'scaling_strategy': 'FIXED_WORKERS',
            'worker_count_fixed': 2
        }
        wd1.replicas = 2
        wd1.oasis_model_id = 10
        model_state = ModelState(tasks=10, analyses=2, priority=5)

        prioritized_models = [(wd1.name, model_state, wd1)]

        asyncio.run(autoscaler._scale_models(prioritized_models))
        self.assertEqual(1, oasis_client.get_auto_scaling.call_count)

        asyncio.run(autoscaler._scale_models(prioritized_models))
        self.assertEqual(2, oasis_client.get_auto_scaling.call_count)

    def test_never_shutdown_fixed_workers(self):

        autoscaler = AutoScaler(None, None, None, None, None, False, True)

        wd1 = WorkerDeployment('worker-oasislmf-piwind-1', 'oasislmf', 'piwind', '1')
        wd1.auto_scaling = {
            'scaling_strategy': 'FIXED_WORKERS',
            'worker_count_fixed': 2
        }
        wd1.replicas = 2
        model_state = ModelState(tasks=10, analyses=2, priority=5)

        desired_replicas = asyncio.run(autoscaler._scale_deployment(wd1, True, model_state, 10))
        self.assertEqual(2, desired_replicas)

        desired_replicas = asyncio.run(autoscaler._scale_deployment(wd1, False, model_state, 10))
        self.assertEqual(2, desired_replicas)


if __name__ == '__main__':
    unittest.main()

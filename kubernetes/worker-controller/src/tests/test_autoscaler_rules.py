import unittest
import autoscaler_rules


class TestScalingRules(unittest.TestCase):
    """
    Tests for all autoscaler rules. Check different outcomes (replicas) based on autoscaler configuration and
    the states of the models (tasks, analyses running)
    """

    def test_incorrect(self):

        as_conf = {}
        state = {}
        self.assertRaises(ValueError, lambda: autoscaler_rules.get_desired_worker_count(as_conf, state))

    def test_fixed_correct(self):

        as_conf = {
            'scaling_strategy': 'FIXED_WORKERS',
            'worker_count_fixed': 5
        }
        state = {
            'analyses': 3
        }
        desired_replicas = autoscaler_rules.get_desired_worker_count(as_conf, state)

        self.assertEqual(5, desired_replicas)

    def test_fixed_incorrect_missing_size(self):

        as_conf = {
            'scaling_strategy': 'FIXED_WORKERS'
        }
        state = {}
        self.assertRaises(ValueError, lambda: autoscaler_rules.get_desired_worker_count(as_conf, state, never_shutdown_fixed_workers=True))

    def test_queue_load_correct(self):

        as_conf = {
            'scaling_strategy': 'QUEUE_LOAD',
            'worker_count_max': 5
        }
        state = {
            'analyses': 3
        }
        desired_replicas = autoscaler_rules.get_desired_worker_count(as_conf, state)

        self.assertEqual(3, desired_replicas)

    def test_queue_load_correct_max_count(self):

        as_conf = {
            'scaling_strategy': 'QUEUE_LOAD',
            'worker_count_max': 5
        }
        state = {
            'analyses': 30
        }
        desired_replicas = autoscaler_rules.get_desired_worker_count(as_conf, state)

        self.assertEqual(5, desired_replicas)

    def test_queue_load_incorrect_missing_size(self):

        as_conf = {
            'scaling_strategy': 'QUEUE_LOAD'
        }
        state = {}
        self.assertRaises(ValueError, lambda: autoscaler_rules.get_desired_worker_count(as_conf, state))

    def test_chunks_per_worker_correct(self):

        as_conf = {
            'scaling_strategy': 'DYNAMIC_TASKS',
            'chunks_per_worker': 2,
            'worker_count_max': 10

        }
        state = {
            'tasks': 8
        }
        desired_replicas = autoscaler_rules.get_desired_worker_count(as_conf, state)

        self.assertEqual(4, desired_replicas)

    def test_chunks_per_worker_correct2(self):

        as_conf = {
            'scaling_strategy': 'DYNAMIC_TASKS',
            'chunks_per_worker': 1,
            'worker_count_max': 10

        }
        state = {
            'tasks': 80
        }
        desired_replicas = autoscaler_rules.get_desired_worker_count(as_conf, state)

        self.assertEqual(10, desired_replicas)

    def test_chunks_per_worker_correct3(self):

        as_conf = {
            'scaling_strategy': 'DYNAMIC_TASKS',
            'chunks_per_worker': 800,
            'worker_count_max': 10

        }
        state = {
            'tasks': 80
        }
        desired_replicas = autoscaler_rules.get_desired_worker_count(as_conf, state)

        self.assertEqual(1, desired_replicas)

    def test_chunks_per_worker_correct4(self):

        as_conf = {
            'scaling_strategy': 'DYNAMIC_TASKS',
            'chunks_per_worker': 1,
            'worker_count_max': 10

        }
        state = {
            'tasks': 80
        }
        desired_replicas = autoscaler_rules.get_desired_worker_count(as_conf, state)

        self.assertEqual(10, desired_replicas)

    def test_chunks_per_worker_incorrect_config(self):

        as_conf = {
            'scaling_strategy': 'DYNAMIC_TASKS',
        }
        state = {}
        self.assertRaises(ValueError, lambda: autoscaler_rules.get_desired_worker_count(as_conf, state))


if __name__ == '__main__':
    unittest.main()

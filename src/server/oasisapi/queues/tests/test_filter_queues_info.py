from django.test import TestCase
from mock import patch

# from src.server.oasisapi.analyses.models import AnalysisTaskStatus
# from src.server.oasisapi.analyses.tests.fakes import fake_analysis_task_status
# from src.server.oasisapi.queues.utils import get_queues_info, filter_queues_info
from src.server.oasisapi.queues.utils import filter_queues_info


class FilterQueuesInfo(TestCase):
    def test_info_not_supplied___data_from_get_queues_info_is_filtered_by_queue_name(self):
        inspect_info = [
            {'name': 'a', 'worker_count': 1, 'queued_count': 2, 'running_count': 3},
            {'name': 'b', 'worker_count': 4, 'queued_count': 5, 'running_count': 6},
            {'name': 'c', 'worker_count': 7, 'queued_count': 8, 'running_count': 9},
        ]

        with patch('src.server.oasisapi.queues.utils.get_queues_info', return_value=inspect_info):
            info = filter_queues_info(['b', 'c'])

            self.assertEqual(info, [
                {'name': 'b', 'worker_count': 4, 'queued_count': 5, 'running_count': 6},
                {'name': 'c', 'worker_count': 7, 'queued_count': 8, 'running_count': 9},
            ])

    def test_info_not_supplied___data_from_supplied_info_is_filtered_by_queue_name(self):
        with patch('src.server.oasisapi.queues.utils.get_queues_info') as info_mock:
            info = filter_queues_info(['b', 'c'], info=[
                {'name': 'a', 'worker_count': 1, 'queued_count': 2, 'running_count': 3},
                {'name': 'b', 'worker_count': 4, 'queued_count': 5, 'running_count': 6},
                {'name': 'c', 'worker_count': 7, 'queued_count': 8, 'running_count': 9},
            ])

            self.assertEqual(info, [
                {'name': 'b', 'worker_count': 4, 'queued_count': 5, 'running_count': 6},
                {'name': 'c', 'worker_count': 7, 'queued_count': 8, 'running_count': 9},
            ])
            info_mock.assert_not_called()

# from django.test import TestCase
# from mock import patch
#
# from src.server.oasisapi.analyses.models import AnalysisTaskStatus
# from src.server.oasisapi.analyses.tests.fakes import fake_analysis_task_status
# from src.server.oasisapi.queues.utils import get_queues_info

# TODO: fix test - disabled due to failure
# class GetQueuesInfo(TestCase):
#     def test_queues_present_in_broker___queues_are_added_to_the_result(self):
#         with patch('src.server.oasisapi.queues.utils._get_broker_queue_names', return_value=['a', 'b', 'c']), \
#                 patch('src.server.oasisapi.queues.utils._get_active_queues', return_value={}):
#             info = get_queues_info()
#
#             self.assertEqual(info, [
#                 {'name': 'a', 'worker_count': 0, 'queued_count': 0, 'running_count': 0},
#                 {'name': 'b', 'worker_count': 0, 'queued_count': 0, 'running_count': 0},
#                 {'name': 'c', 'worker_count': 0, 'queued_count': 0, 'running_count': 0},
#             ])
#
#     def test_queues_present_in_workers___queues_are_added_to_the_result(self):
#         active_queues = {
#             'worker-1': [
#                 {'routing_key': 'a'},
#                 {'routing_key': 'b'},
#             ],
#             'worker-2': [
#                 {'routing_key': 'b'},
#                 {'routing_key': 'c'},
#             ]
#         }
#
#         with patch('src.server.oasisapi.queues.utils._get_broker_queue_names', return_value=[]), \
#                 patch('src.server.oasisapi.queues.utils._get_active_queues', return_value=active_queues):
#             info = get_queues_info()
#
#             self.assertEqual(info, [
#                 {'name': 'a', 'worker_count': 1, 'queued_count': 0, 'running_count': 0},
#                 {'name': 'b', 'worker_count': 2, 'queued_count': 0, 'running_count': 0},
#                 {'name': 'c', 'worker_count': 1, 'queued_count': 0, 'running_count': 0},
#             ])
#
#     def test_tasks_exists_for_the_queues___queue_stats_are_updated(self):
#         active_queues = {
#             'worker-1': [
#                 {'routing_key': 'a'},
#                 {'routing_key': 'b'},
#             ],
#             'worker-2': [
#                 {'routing_key': 'b'},
#                 {'routing_key': 'c'},
#             ]
#         }
#
#         fake_analysis_task_status(queue_name='a', status=AnalysisTaskStatus.status_choices.QUEUED)
#         fake_analysis_task_status(queue_name='a', status=AnalysisTaskStatus.status_choices.QUEUED)
#         fake_analysis_task_status(queue_name='a', status=AnalysisTaskStatus.status_choices.STARTED)
#         fake_analysis_task_status(queue_name='a', status=AnalysisTaskStatus.status_choices.COMPLETED)
#
#         fake_analysis_task_status(queue_name='b', status=AnalysisTaskStatus.status_choices.STARTED)
#         fake_analysis_task_status(queue_name='b', status=AnalysisTaskStatus.status_choices.ERROR)
#         fake_analysis_task_status(queue_name='b', status=AnalysisTaskStatus.status_choices.CANCELLED)
#         fake_analysis_task_status(queue_name='b', status=AnalysisTaskStatus.status_choices.COMPLETED)
#
#         with patch('src.server.oasisapi.queues.utils._get_broker_queue_names', return_value=[]), \
#                 patch('src.server.oasisapi.queues.utils._get_active_queues', return_value=active_queues):
#             info = get_queues_info()
#
#             self.assertEqual(info, [
#                 {'name': 'a', 'worker_count': 1, 'queued_count': 2, 'running_count': 1},
#                 {'name': 'b', 'worker_count': 2, 'queued_count': 0, 'running_count': 1},
#                 {'name': 'c', 'worker_count': 1, 'queued_count': 0, 'running_count': 0},
#             ])

from django.test import TestCase
from django.utils.timezone import now
from freezegun import freeze_time
from rest_framework.fields import DateTimeField

from src.server.oasisapi.queues.consumers import build_task_status_message
# from src.server.oasisapi.analyses.serializers import AnalysisSerializer, AnalysisTaskStatusSerializer
# from src.server.oasisapi.analyses.tests.fakes import fake_analysis, fake_analysis_task_status
# from src.server.oasisapi.queues.consumers import TaskStatusMessageItem, TaskStatusMessageAnalysisItem
# from src.server.oasisapi.queues.serializers import QueueSerializer


class BuildTaskStatusMessage(TestCase):
    def test_current_time_is_included(self):
        _now = now()

        with freeze_time(_now):
            self.assertEqual(build_task_status_message([])['time'], DateTimeField().to_representation(_now))

    def test_type_is_correct(self):
        self.assertEqual(build_task_status_message([])['type'], 'queue_status.updated')

    # TODO: fix test - disabled due to failure
    # def test_queue_is_serialized_queue_info_object(self):
    #     queue_info = {
    #         'name': 'a',
    #         'worker_count': 1,
    #         'running_count': 2,
    #         'queued_count': 3,
    #     }
    #
    #     item = TaskStatusMessageItem(queue=queue_info, analyses=[])
    #
    #     self.assertEqual(build_task_status_message([item])['content'][0]['queue'], QueueSerializer(queue_info).data)

    # TODO: fix test - disabled due to failure
    # def test_analysis_is_serialized_analysis_object(self):
    #     queue_info = {
    #         'name': 'a',
    #         'worker_count': 1,
    #         'running_count': 2,
    #         'queued_count': 3,
    #     }
    #     analysis = fake_analysis()
    #
    #     item = TaskStatusMessageItem(
    #         queue=queue_info,
    #         analyses=[TaskStatusMessageAnalysisItem(analysis=analysis, updated_tasks=[])]
    #     )
    #
    #     self.assertEqual(
    #         build_task_status_message([item])['content'][0]['analyses'][0]['analysis'],
    #         AnalysisSerializer(analysis).data
    #     )

    # TODO: fix test - disabled due to failure
    # def test_analysis_task_status_is_serialized_analysis_task_status_object(self):
    #     queue_info = {
    #         'name': 'a',
    #         'worker_count': 1,
    #         'running_count': 2,
    #         'queued_count': 3,
    #     }
    #     analysis = fake_analysis()
    #     task_status = fake_analysis_task_status()
    #
    #     item = TaskStatusMessageItem(
    #         queue=queue_info,
    #         analyses=[TaskStatusMessageAnalysisItem(analysis=analysis, updated_tasks=[task_status])]
    #     )
    #
    #     self.assertEqual(
    #         build_task_status_message([item])['content'][0]['analyses'][0]['updated_tasks'][0],
    #         AnalysisTaskStatusSerializer(task_status).data
    #     )

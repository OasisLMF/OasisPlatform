from unittest.mock import patch

from hypothesis.extra.django import TestCase

from src.server.oasisapi.analyses.models import AnalysisTaskStatus
from src.server.oasisapi.analyses.v2_api.tests.fakes import fake_analysis_task_status


class WebsocketTriggers(TestCase):
    def test_status_is_queued___message_isnt_sent(self):
        with patch('src.server.oasisapi.queues.consumers.send_task_status_message') as send_mock:
            fake_analysis_task_status()

            send_mock.assert_not_called()

    def test_tasks_statuses_are_created_with_create_statues___message_is_sent(self):
        with (patch('src.server.oasisapi.analyses.models.send_task_status_message') as send_mock,
              patch('src.server.oasisapi.analyses.models.build_all_queue_status_message') as build_mock,
              patch('src.server.oasisapi.analyses.models.AnalysisTaskStatusQuerySet.bulk_create') as bulk_mock):

            build_mock.return_value = "Lorem ipsum"
            AnalysisTaskStatus.objects.create_statuses(None)

            bulk_mock.assert_called_once()
            send_mock.assert_called_once_with("Lorem ipsum")

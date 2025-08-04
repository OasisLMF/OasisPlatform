from django.test import TestCase
from mock import patch, MagicMock
from src.server.oasisapi.queues.utils import get_queues_info


class GetQueuesInfo(TestCase):
    def test_queues_present_in_broker___queues_are_added_to_the_result(self):
        pending_queue = MagicMock()
        started_queue = MagicMock()
        queued_queue = MagicMock()
        pending_queue.values.return_value.annotate.return_value = [
            {'queue_name': 'c', 'count': 186}
        ]
        started_queue.values.return_value.annotate.return_value = [
            {'queue_name': 'a', 'count': 22}, {'queue_name': 'b', 'count': 7}, {'queue_name': 'c', 'count': 13}
        ]
        queued_queue.values.return_value.annotate.return_value = []

        def filter_side_effect(status):
            if status == "PENDING":
                return pending_queue
            elif status == "STARTED":
                return started_queue
            elif status == "QUEUED":
                return queued_queue
            raise ValueError(status)

        with (patch('src.server.oasisapi.queues.utils._get_broker_queue_names', return_value=['a', 'b', 'c']),
              patch('src.server.oasisapi.queues.utils.celery_app_v2'),
              patch('src.server.oasisapi.queues.utils._get_queue_message_count', return_value=494),
              patch('src.server.oasisapi.queues.utils._get_queue_consumers', return_value=64),
              patch('src.server.oasisapi.analyses.models.AnalysisTaskStatus') as fake_task_status):
            fake_task_status.objects.filter.side_effect = filter_side_effect
            fake_task_status.status_choices.PENDING = "PENDING"
            fake_task_status.status_choices.QUEUED = "QUEUED"
            fake_task_status.status_choices.STARTED = "STARTED"
            info = get_queues_info()

            self.assertEqual(info, [
                {'name': 'a', 'pending_count': 0, 'queued_count': 0, 'running_count': 22, 'queue_message_count': 494, 'worker_count': 64},
                {'name': 'b', 'pending_count': 0, 'queued_count': 0, 'running_count': 7, 'queue_message_count': 494, 'worker_count': 64},
                {'name': 'c', 'pending_count': 186, 'queued_count': 0, 'running_count': 13, 'queue_message_count': 494, 'worker_count': 64},
            ])

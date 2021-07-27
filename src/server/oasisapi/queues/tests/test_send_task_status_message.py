from unittest.mock import Mock, patch

from django.test import TestCase
from freezegun import freeze_time

from src.server.oasisapi.queues.consumers import build_task_status_message, send_task_status_message


class SendTaskStatusMessage(TestCase):
    class LayerMock:
        def group_send(self):
            pass

    def test_build_status_message_is_sent_to_the_channel_layer(self):
        sync_call = Mock()
        layer = self.LayerMock()

        with freeze_time(), patch('src.server.oasisapi.queues.consumers.get_channel_layer', return_value=layer), \
                patch('src.server.oasisapi.queues.consumers.async_to_sync', return_value=sync_call) as async_to_sync_mock:
            send_task_status_message(build_task_status_message([]))

            async_to_sync_mock.assert_called_once_with(layer.group_send)
            sync_call.assert_called_once_with('queue_status', build_task_status_message([]))

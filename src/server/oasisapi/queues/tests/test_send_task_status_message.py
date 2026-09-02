from unittest.mock import Mock, patch

from django.test import TestCase, override_settings
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

    @override_settings(DISABLE_WORKER_WS=True)
    def test_worker_ws_is_disabled___channel_layer_is_not_used(self):
        with patch('src.server.oasisapi.queues.consumers.get_channel_layer') as mock_get_channel_layer:
            send_task_status_message(build_task_status_message([]))

            mock_get_channel_layer.assert_not_called()

    @override_settings(DISABLE_WORKER_WS=False)
    def test_channel_layer_raises_an_exception___error_is_swallowed(self):
        layer = self.LayerMock()

        with patch('src.server.oasisapi.queues.consumers.get_channel_layer', return_value=layer), \
                patch('src.server.oasisapi.queues.consumers.async_to_sync', side_effect=Exception('unreachable')):
            try:
                send_task_status_message(build_task_status_message([]))
            except Exception:
                self.fail('send_task_status_message should not propagate channel layer errors')

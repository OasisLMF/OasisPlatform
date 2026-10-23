from unittest.mock import AsyncMock, patch
from asgiref.sync import sync_to_async
from django.db.models.expressions import CombinedExpression
from django.test import TestCase
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import AnonymousUser, User
from rest_framework_simplejwt.tokens import AccessToken

from src.server.oasisapi.routing import application
from src.server.oasisapi.queues.consumers import AnalysisStatusConsumer
from src.server.oasisapi.analyses.models import Analysis
from src.server.oasisapi.analyses.v2_api.tests.fakes import fake_analysis


class TestQueueStatusConsumer(TestCase):
    @patch('src.server.oasisapi.queues.consumers.build_all_queue_status_message')
    async def test_connection_with_valid_token(self, mock_build_message):
        # Wrap synchronous database operations
        mock_build_message.return_value = {"status": "mocked-queue-return"}
        user = await sync_to_async(User.objects.create_user)(
            username='testuser',
            password='testpassword'
        )
        token = await sync_to_async(AccessToken.for_user)(user)

        communicator = WebsocketCommunicator(
            application,
            "ws/v2/queue-status/",
            headers=[
                (b"authorization", f"Bearer {token}".encode())
            ]
        )

        channel_layer = get_channel_layer('default')
        communicator.channel_layer = channel_layer
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        self.assertEqual(communicator.scope["user"], user)
        self.assertNotIsInstance(communicator.scope["user"], AnonymousUser)
        await communicator.disconnect()

    async def test_connection_with_invalid_token(self):
        communicator = WebsocketCommunicator(
            application, "ws/v2/queue-status/?token=invalidtoken"
        )

        # Use an in-memory channel layer for testing
        channel_layer = get_channel_layer('default')
        communicator.channel_layer = channel_layer

        connected, close_code = await communicator.connect()
        self.assertFalse(connected)
        self.assertEqual(close_code, 1000)

        # Check that the user is anonymous
        self.assertIsInstance(communicator.scope["user"], AnonymousUser)

        await communicator.disconnect()

    async def test_connection_without_token(self):
        communicator = WebsocketCommunicator(application, "ws/v2/queue-status/")

        # Use an in-memory channel layer for testing
        channel_layer = get_channel_layer('default')
        communicator.channel_layer = channel_layer

        connected, close_code = await communicator.connect()
        self.assertFalse(connected)
        self.assertEqual(close_code, 1000)

        # Check that the user is anonymous
        self.assertIsInstance(communicator.scope["user"], AnonymousUser)

        await communicator.disconnect()


class TestAnalysisStatusConsumer(TestCase):
    async def test_analysis_pk_missing___save_is_not_called(self):
        consumer = AnalysisStatusConsumer()

        with patch('src.server.oasisapi.queues.consumers.update_analysis_progress', new_callable=AsyncMock) as mock_update:
            await consumer.handle_content({})

            mock_update.assert_not_called()

    async def test_events_total_is_provided___num_events_total_is_set(self):
        consumer = AnalysisStatusConsumer()

        with patch('src.server.oasisapi.queues.consumers.update_analysis_progress', new_callable=AsyncMock) as mock_update:
            await consumer.handle_content({'analysis_pk': '1', 'events_total': '42'})

            mock_update.assert_awaited_once_with('1', {'num_events_total': 42})

    async def test_outputs_total_is_provided___num_outputs_total_is_set(self):
        consumer = AnalysisStatusConsumer()

        with patch('src.server.oasisapi.queues.consumers.update_analysis_progress', new_callable=AsyncMock) as mock_update:
            await consumer.handle_content({'analysis_pk': '1', 'outputs_total': '51'})

            mock_update.assert_awaited_once_with('1', {'num_outputs_total': 51})

    async def test_counts_are_provided___counts_are_incremented(self):
        consumer = AnalysisStatusConsumer()

        with patch('src.server.oasisapi.queues.consumers.update_analysis_progress', new_callable=AsyncMock) as mock_update:
            await consumer.handle_content({'analysis_pk': '1', 'events_complete': '3', 'gul_ready': 1, 'outputs_complete': '2'})

            pk, updates = mock_update.await_args.args
            self.assertEqual('1', pk)
            self.assertEqual({'num_events_complete', 'num_gul_ready', 'num_outputs_complete'}, set(updates))
            for field, value in [('num_events_complete', 3), ('num_gul_ready', 1), ('num_outputs_complete', 2)]:
                expr = updates[field]
                self.assertIsInstance(expr, CombinedExpression)
                self.assertEqual('+', expr.connector)
                self.assertEqual(field, expr.lhs.name)
                self.assertEqual(value, expr.rhs.value)

    async def test_ping_has_no_progress_keys___analysis_is_not_updated(self):
        consumer = AnalysisStatusConsumer()

        with patch('src.server.oasisapi.queues.consumers.update_analysis_progress', new_callable=AsyncMock) as mock_update:
            await consumer.handle_content({'analysis_pk': '1', 'outputs_done': 1})

            mock_update.assert_not_called()

    async def test_ping_is_received___only_progress_columns_are_written(self):
        """The ping is applied without saving the instance, so it can't write back a stale status over the run's completion."""
        analysis = await sync_to_async(fake_analysis)(status=Analysis.status_choices.RUN_STARTED)
        await sync_to_async(Analysis.objects.filter(pk=analysis.pk).update)(status=Analysis.status_choices.RUN_COMPLETED)

        with patch.object(Analysis, 'save') as mock_save:
            await AnalysisStatusConsumer().handle_content({'analysis_pk': analysis.pk, 'outputs_complete': 1})

        mock_save.assert_not_called()
        await sync_to_async(analysis.refresh_from_db)()
        self.assertEqual((Analysis.status_choices.RUN_COMPLETED, 1), (analysis.status, analysis.num_outputs_complete))

    async def test_run_progress_pings_are_received___analysis_counts_are_updated(self):
        analysis = await sync_to_async(fake_analysis)()
        consumer = AnalysisStatusConsumer()

        for ping in [
            {'analysis_pk': analysis.pk, 'events_total': '10'},
            {'analysis_pk': analysis.pk, 'gul_ready': 1},
            {'analysis_pk': analysis.pk, 'gul_ready': 1},
            {'analysis_pk': analysis.pk, 'events_complete': 10},
            {'analysis_pk': analysis.pk, 'outputs_total': 3},
            {'analysis_pk': analysis.pk, 'outputs_complete': 1},
            {'analysis_pk': analysis.pk, 'outputs_complete': 1},
        ]:
            await consumer.handle_content(ping)

        await sync_to_async(analysis.refresh_from_db)()
        self.assertEqual(
            (10, 10, 2, 3, 2),
            (analysis.num_events_total, analysis.num_events_complete, analysis.num_gul_ready,
             analysis.num_outputs_total, analysis.num_outputs_complete),
        )

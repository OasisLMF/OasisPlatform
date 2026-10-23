from unittest.mock import AsyncMock, Mock, patch
from asgiref.sync import sync_to_async
from django.db.models.expressions import CombinedExpression
from django.test import TestCase
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import AnonymousUser, User
from rest_framework_simplejwt.tokens import AccessToken

from src.server.oasisapi.routing import application
from src.server.oasisapi.queues.consumers import AnalysisStatusConsumer
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

        with patch('src.server.oasisapi.queues.consumers.get_analysis', new_callable=AsyncMock) as mock_get_analysis:
            await consumer.handle_content({})

            mock_get_analysis.assert_not_called()

    async def test_events_total_is_provided___num_events_total_is_set_and_saved(self):
        consumer = AnalysisStatusConsumer()
        analysis = Mock(save=AsyncMock())

        with patch('src.server.oasisapi.queues.consumers.get_analysis', new_callable=AsyncMock) as mock_get_analysis, \
                patch('src.server.oasisapi.queues.consumers.sync_to_async', side_effect=lambda fn: fn):
            mock_get_analysis.return_value = analysis

            await consumer.handle_content({'analysis_pk': '1', 'events_total': '42'})

            mock_get_analysis.assert_awaited_once_with(pk='1')
            self.assertEqual(42, analysis.num_events_total)
            analysis.save.assert_awaited_once()

    async def test_events_complete_is_provided___num_events_complete_is_incremented_and_saved(self):
        consumer = AnalysisStatusConsumer()
        analysis = Mock(save=AsyncMock())

        with patch('src.server.oasisapi.queues.consumers.get_analysis', new_callable=AsyncMock) as mock_get_analysis, \
                patch('src.server.oasisapi.queues.consumers.sync_to_async', side_effect=lambda fn: fn):
            mock_get_analysis.return_value = analysis

            await consumer.handle_content({'analysis_pk': '1', 'events_complete': '3'})

            expr = analysis.num_events_complete
            self.assertIsInstance(expr, CombinedExpression)
            self.assertEqual('+', expr.connector)
            self.assertEqual('num_events_complete', expr.lhs.name)
            self.assertEqual(3, expr.rhs.value)
            analysis.save.assert_awaited_once()

    async def test_outputs_total_is_provided___num_outputs_total_is_set_and_saved(self):
        consumer = AnalysisStatusConsumer()
        analysis = Mock(save=AsyncMock())

        with patch('src.server.oasisapi.queues.consumers.get_analysis', new_callable=AsyncMock) as mock_get_analysis, \
                patch('src.server.oasisapi.queues.consumers.sync_to_async', side_effect=lambda fn: fn):
            mock_get_analysis.return_value = analysis

            await consumer.handle_content({'analysis_pk': '1', 'outputs_total': '51'})

            self.assertEqual(51, analysis.num_outputs_total)
            analysis.save.assert_awaited_once()

    async def test_gul_ready_and_outputs_complete_are_provided___counts_are_incremented_and_saved(self):
        consumer = AnalysisStatusConsumer()
        analysis = Mock(save=AsyncMock())

        with patch('src.server.oasisapi.queues.consumers.get_analysis', new_callable=AsyncMock) as mock_get_analysis, \
                patch('src.server.oasisapi.queues.consumers.sync_to_async', side_effect=lambda fn: fn):
            mock_get_analysis.return_value = analysis

            await consumer.handle_content({'analysis_pk': '1', 'gul_ready': 1, 'outputs_complete': '2'})

            for field, value in [('num_gul_ready', 1), ('num_outputs_complete', 2)]:
                expr = getattr(analysis, field)
                self.assertIsInstance(expr, CombinedExpression)
                self.assertEqual('+', expr.connector)
                self.assertEqual(field, expr.lhs.name)
                self.assertEqual(value, expr.rhs.value)
            analysis.save.assert_awaited_once()

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

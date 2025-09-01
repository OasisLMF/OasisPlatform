import asyncio
from unittest.mock import patch
from asgiref.sync import sync_to_async
from django.test import TestCase
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import AnonymousUser, User
from rest_framework_simplejwt.tokens import AccessToken

from src.server.oasisapi.routing import application


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

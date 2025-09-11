import asyncio
from asgiref.sync import sync_to_async
from django.test import TransactionTestCase
from django.contrib.auth.models import AnonymousUser, User
from rest_framework_simplejwt.tokens import AccessToken
import pytest

from src.server.oasisapi.routing import TokenAuthMiddleware


@pytest.mark.django_db(transaction=True)
class TestTokenAuthMiddleware(TransactionTestCase):
    def test_middleware_with_valid_token(self):
        async def test():
            # Move database operations inside the async context
            user = await sync_to_async(User.objects.create_user)(
                username='testuser',
                password='testpassword'
            )
            token = await sync_to_async(AccessToken.for_user)(user)

            scope = {
                "type": "websocket",
                "headers": [(b"authorization", f"Bearer {token}".encode())],
            }

            async def dummy_inner(scope, receive, send):
                pass

            middleware = TokenAuthMiddleware(dummy_inner)
            await middleware(scope, None, None)

            # Convert assertions to async as well
            scope_user = scope["user"]
            self.assertEqual(scope_user, user)
            self.assertNotIsInstance(scope_user, AnonymousUser)

        asyncio.run(test())

    def test_middleware_with_invalid_token(self):
        scope = {
            "type": "websocket",
            "headers": [(b"authorization", b"Bearer invalidtoken")],
        }

        async def dummy_inner(scope, receive, send):
            pass

        middleware = TokenAuthMiddleware(dummy_inner)

        async def test():
            await middleware(scope, None, None)

            self.assertIsInstance(scope["user"], AnonymousUser)

        asyncio.run(test())

    def test_middleware_without_token(self):
        scope = {
            "type": "websocket",
            "headers": [],
        }

        async def dummy_inner(scope, receive, send):
            pass

        middleware = TokenAuthMiddleware(dummy_inner)

        async def test():
            await middleware(scope, None, None)

            self.assertIsInstance(scope["user"], AnonymousUser)

        asyncio.run(test())

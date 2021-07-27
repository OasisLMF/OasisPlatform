from asgiref.sync import sync_to_async
from channels.auth import UserLazyObject
from channels.middleware import BaseMiddleware
from channels.routing import ProtocolTypeRouter, URLRouter
from django.contrib.auth.models import AnonymousUser
from django.urls import path
from rest_framework_simplejwt.authentication import JWTAuthentication

from src.server.oasisapi.queues.routing import websocket_urlpatterns

url_patterns = [
    path('ws/', URLRouter(websocket_urlpatterns))
]


async def get_user(scope):
    header_value = next((v for k, v in scope['headers'] if k == b'authorization'), None)
    if not header_value:
        return AnonymousUser()

    backend = JWTAuthentication()
    token = backend.get_raw_token(header_value)
    token = backend.get_validated_token(token)

    try:
        async_get_user = sync_to_async(backend.get_user, thread_sensitive=True)
        user = await async_get_user(token)
        return user
    except Exception as e:
        return AnonymousUser()


class JwtAuthMiddleware(BaseMiddleware):
    def populate_scope(self, scope):
        # Add it to the scope if it's not there already
        if 'user' not in scope:
            scope['user'] = UserLazyObject()

    async def resolve_scope(self, scope):
        scope['user']._wrapped = await get_user(scope)


application = ProtocolTypeRouter({
    'websocket': JwtAuthMiddleware(
        URLRouter(
            url_patterns
        )
    ),
})

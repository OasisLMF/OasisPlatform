from urllib.parse import parse_qs
import logging

from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from channels.routing import ProtocolTypeRouter, URLRouter
from django.contrib.auth.models import AnonymousUser
from django.urls import re_path
from mozilla_django_oidc.contrib.drf import OIDCAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication

from src.server.oasisapi import settings
from src.server.oasisapi.oidc.keycloak_auth import KeycloakOIDCAuthenticationBackend
from src.server.oasisapi.queues.routing import websocket_urlpatterns

url_patterns = [
    re_path('ws/', URLRouter(websocket_urlpatterns))
]

logger = logging.getLogger(__name__)


async def get_user(token_key):
    logger.info(f'Attempting to authenticate user with token: {token_key}')
    try:
        header_value = f'Bearer {token_key}'.encode()
        if not header_value:
            logger.warning('No token provided, returning AnonymousUser')
            return AnonymousUser()

        if settings.API_AUTH_TYPE == 'keycloak':
            logger.info('Using Keycloak authentication')
            backend = KeycloakOIDCAuthenticationBackend()
            authentication = OIDCAuthentication(backend)
            request = type('', (), {'META': {'HTTP_AUTHORIZATION': header_value}})()
            user, access_token = await sync_to_async(authentication.authenticate, thread_sensitive=True)(request)
            logger.info(f'Successfully authenticated user: {user}')
            return user
        else:
            logger.info('Using JWT authentication')
            backend = JWTAuthentication()
            token = backend.get_raw_token(header_value)
            token = backend.get_validated_token(token)
            user = await sync_to_async(backend.get_user, thread_sensitive=True)(token)
            logger.info(f'Successfully authenticated user: {user}')
            return user
    except Exception as e:
        logger.error(f'Error authenticating user: {e}')
        return AnonymousUser()


class TokenAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode("utf-8")
        query_params = parse_qs(query_string)
        token_key = query_params.get("token", [None])[0]

        if token_key:
            scope["user"] = await get_user(token_key)
        else:
            scope["user"] = AnonymousUser()

        return await self.inner(scope, receive, send)


application = ProtocolTypeRouter({
    'websocket': TokenAuthMiddleware(
        URLRouter(
            url_patterns
        )
    ),
})

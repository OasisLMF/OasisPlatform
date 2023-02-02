from asgiref.sync import sync_to_async
from channels.auth import UserLazyObject
from channels.middleware import BaseMiddleware
from channels.routing import ProtocolTypeRouter, URLRouter
from django.contrib.auth.models import AnonymousUser
from django.urls import path
from mozilla_django_oidc.contrib.drf import OIDCAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication

from src.server.oasisapi import settings
from src.server.oasisapi.oidc.keycloak_auth import KeycloakOIDCAuthenticationBackend
from src.server.oasisapi.queues.routing import websocket_urlpatterns

url_patterns = [
    path('ws/', URLRouter(websocket_urlpatterns))
]


async def get_user(scope):

    try:
        header_value = next((v for k, v in scope['headers'] if k == b'authorization'), None)
        if not header_value:
            return AnonymousUser()

        if settings.API_AUTH_TYPE == 'keycloak':

            backend = KeycloakOIDCAuthenticationBackend()
            authentication = OIDCAuthentication(backend)
            async_authentication = sync_to_async(authentication.authenticate, thread_sensitive=True)

            request = type('', (), {'META': {'HTTP_AUTHORIZATION': header_value}})()
            user, access_token = await async_authentication(request)
            return user
        else:

            backend = JWTAuthentication()
            token = backend.get_raw_token(header_value)
            token = backend.get_validated_token(token)

            async_authentication = sync_to_async(backend.get_user, thread_sensitive=True)
            user = await async_authentication(token)
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

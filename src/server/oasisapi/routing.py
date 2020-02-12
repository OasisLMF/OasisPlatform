from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import path, include

from src.server.oasisapi.queues.routing import websocket_urlpatterns

url_patterns = [
    path('ws/', include(websocket_urlpatterns))
]

application = ProtocolTypeRouter({
    'websocket': AuthMiddlewareStack(
        URLRouter(
            url_patterns
        )
    ),
})

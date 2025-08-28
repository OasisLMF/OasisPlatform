"""
ASGI entrypoint. Configures Django and then runs the application
defined in the ASGI_APPLICATION setting.
"""
import os
import django
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "src.server.oasisapi.settings")
django.setup()

# Import your websocket routing
from src.server.oasisapi.routing import websocket_urlpatterns  # Adjust path as needed

# Create the application
if os.getenv('OASIS_DISABLE_HTTP', default=True):
    # Only websocket routing
    application = ProtocolTypeRouter({
        'websocket': AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        ),
    })
else:
    # Both HTTP and websocket routing
    application = ProtocolTypeRouter({
        'http': get_asgi_application(),
        'websocket': AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        ),
    })

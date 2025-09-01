"""
ASGI entrypoint. Configures Django and then runs the application
defined in the ASGI_APPLICATION setting.
"""
import os
import django
# from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "src.server.oasisapi.settings")
django.setup()

# Import your websocket routing
from src.server.oasisapi.routing import application

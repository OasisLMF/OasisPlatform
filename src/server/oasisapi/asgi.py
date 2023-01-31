"""
ASGI entrypoint. Configures Django and then runs the application
defined in the ASGI_APPLICATION setting.
"""

import os
import django
from channels.routing import get_default_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "src.server.oasisapi.settings")
django.setup()

application = get_default_application()

# ONLY run the websocket from here (add safeguard to remove HTTP router)
# if 'http' in application.application_mapping:
#    del application.application_mapping['http']

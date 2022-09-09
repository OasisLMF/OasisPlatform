# wsgi.py
from django.core.wsgi import get_wsgi_application
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "src.server.oasisapi.settings")
application = get_wsgi_application()

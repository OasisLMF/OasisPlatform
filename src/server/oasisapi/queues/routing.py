from django.urls import path

from src.server.oasisapi.queues import consumers

websocket_urlpatterns = [
    path('v2/queue-status/', consumers.QueueStatusConsumer),
]

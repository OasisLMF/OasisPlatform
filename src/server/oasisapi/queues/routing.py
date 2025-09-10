from django.urls import re_path

from src.server.oasisapi.queues import consumers

websocket_urlpatterns = [
    re_path('v2/queue-status/', consumers.QueueStatusConsumer.as_asgi()),
    re_path('analysis-status/', consumers.AnalysisStatusConsumer.as_asgi())
]

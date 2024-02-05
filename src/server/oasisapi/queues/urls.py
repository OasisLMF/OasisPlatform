from rest_framework.routers import SimpleRouter
from django.conf.urls import url, include
from .viewsets import QueueViewSet
from .viewsets import WebsocketViewSet


app_name = 'queue'
v2_api_router = SimpleRouter()
v2_api_router.include_root_view = False
v2_api_router.register('queue', QueueViewSet, basename='queue')
v2_api_router.register('queue-status', WebsocketViewSet, basename='queue')

urlpatterns = [
    url(r'', include(v2_api_router.urls)),
]

from drf_yasg.utils import swagger_auto_schema
from rest_framework import views
from rest_framework.response import Response
from ..schemas.custom_swagger import HEALTHCHECK


class HealthcheckView(views.APIView):
    """
    Gets the current status of the api
    """

    http_method_names = ['get']
    authentication_classes = []
    permission_classes = []

    @swagger_auto_schema(responses={200: HEALTHCHECK})
    def get(self, request):
        return Response({'status': 'OK'})

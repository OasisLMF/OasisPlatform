from rest_framework import views
from rest_framework.response import Response


class HealthcheckView(views.APIView):
    """
    Gets the current status of the api
    """

    http_method_names = ['get']
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response({'status': 'OK'})

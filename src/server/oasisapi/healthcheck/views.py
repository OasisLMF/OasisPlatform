import logging

from django.db import connection
from drf_yasg.utils import swagger_auto_schema
from rest_framework import views, status
from rest_framework.response import Response

from ..celery_app import celery_app
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
        """
        Check db and celery connectivity and return a 200 if healthy, 503 if not.
        """

        code = status.HTTP_200_OK

        if not self.celery_is_ok():
            status_text = 'ERROR - celery down'
            code = status.HTTP_503_SERVICE_UNAVAILABLE
        elif not self.db_is_ok():
            status_text = 'ERROR - db down'
            code = status.HTTP_503_SERVICE_UNAVAILABLE
        else:
            status_text = 'OK'

        return Response({'status': status_text}, code)

    def celery_is_ok(self) -> bool:
        """
        Verify a healthy celery connection.

        :return: True if healthy, False it not.
        """
        try:
            i = celery_app.control.inspect()
            availability = i.ping()
            if not availability:
                return False
        except Exception as e:
            logging.error('Celery error: %s', e)
            return False
        return True

    def db_is_ok(self):
        """
        Verify a healthy database connection.

        :return: True if healthy, False it not.
        """
        try:
            connection.ensure_connection()
        except Exception as e:
            logging.error('Database error: %s', e)
            return False
        return True

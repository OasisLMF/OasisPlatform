import logging

from django.db import connection
from django.conf import settings as django_settings

from drf_yasg.utils import swagger_auto_schema
from rest_framework import views, status
from rest_framework.response import Response

from ..celery_app_v1 import celery_app_v1
from ..celery_app_v2 import celery_app_v2
from ..schemas.custom_swagger import HEALTHCHECK


class HealthcheckView(views.APIView):
    """
    Gets the current status of the api
    """

    http_method_names = ['get']
    authentication_classes = []
    permission_classes = []

    @swagger_auto_schema(responses={200: HEALTHCHECK}, tags=['info'])
    def get(self, request):
        """
        Check db and celery connectivity and return a 200 if healthy, 503 if not.
        """
        code = status.HTTP_200_OK
        status_text = 'OK'

        if not django_settings.CONSOLE_DEBUG:
            if not self.celery_v1_is_ok():
                status_text = 'ERROR - celery v1 down'
                code = status.HTTP_503_SERVICE_UNAVAILABLE
            elif not self.celery_v2_is_ok():
                status_text = 'ERROR - celery v2 down'
                code = status.HTTP_503_SERVICE_UNAVAILABLE
            elif not self.db_is_ok():
                status_text = 'ERROR - db down'
                code = status.HTTP_503_SERVICE_UNAVAILABLE

        return Response({'status': status_text}, code)

    def celery_v1_is_ok(self) -> bool:
        """
        Verify a healthy celery connection.

        :return: True if healthy, False it not.
        """
        try:
            i = celery_app_v1.control.inspect()
            availability = i.ping()
            if not availability:
                return False
        except Exception as e:
            logging.error('Celery error: %s', e)
            return False
        return True

    def celery_v2_is_ok(self) -> bool:
        """
        Verify a healthy celery connection.

        :return: True if healthy, False it not.
        """
        try:
            i = celery_app_v2.control.inspect()
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

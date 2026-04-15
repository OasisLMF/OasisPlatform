import logging
import time
import subprocess
from django.db import connection
from django.conf import settings as django_settings

from drf_spectacular.utils import extend_schema
from rest_framework import views, status
from rest_framework.response import Response

from ..celery_app_v1 import v1 as celery_app_v1
from ..celery_app_v2 import v2 as celery_app_v2
from ..schemas.custom_swagger import HEALTHCHECK


class HealthcheckViewShallow(views.APIView):
    """
    Gets the current status of the api
    """

    http_method_names = ['get']
    authentication_classes = []
    permission_classes = []

    @extend_schema(responses={200: HEALTHCHECK})
    def get(self, request):
        return Response({'status': 'OK'})


class HealthcheckViewDeep(views.APIView):
    """
    Gets the current status of the api, checking the connecting to celery and database 
    """

    http_method_names = ['get']
    authentication_classes = []
    permission_classes = []

    @extend_schema(responses={200: HEALTHCHECK}, tags=['info'])
    def get(self, request):
        """
        Check db and celery connectivity and return a 200 if healthy, 503 if not.
        """
        logger = logging.getLogger(__name__)
        logger.info("***************************Begin healthcheck********************************")
        code = status.HTTP_200_OK
        status_text = 'OK'

        logger.info("Starting health check")

        if not django_settings.CONSOLE_DEBUG:
            start_time = time.time()

            celery_v1_start = time.time()
            if not self.celery_v1_is_ok():
                status_text = 'ERROR - celery v1 down'
                code = status.HTTP_503_SERVICE_UNAVAILABLE
                logger.error("Celery v1 is down (took %.2f seconds)", time.time() - celery_v1_start)
            else:
                logger.info("Celery v1 is healthy (took %.2f seconds)", time.time() - celery_v1_start)

            celery_v2_start = time.time()
            if not self.celery_v2_is_ok():
                status_text = 'ERROR - celery v2 down'
                code = status.HTTP_503_SERVICE_UNAVAILABLE
                logger.error("Celery v2 is down (took %.2f seconds)", time.time() - celery_v2_start)
            else:
                logger.info("Celery v2 is healthy (took %.2f seconds)", time.time() - celery_v2_start)

            db_start = time.time()
            if not self.db_is_ok():
                status_text = 'ERROR - db down'
                code = status.HTTP_503_SERVICE_UNAVAILABLE
                logger.error("Database is down (took %.2f seconds)", time.time() - db_start)
            else:
                logger.info("Database is healthy (took %.2f seconds)", time.time() - db_start)

            logger.info("Total health check time: %.2f seconds", time.time() - start_time)
            # Measure the time taken to print the `top` command output
            start_time = time.time()
            logger.info(self.get_top_output())
            elapsed_time = time.time() - start_time
            logger.info(f"Time taken to print the result: {elapsed_time:.2f} seconds")
            logger.info("***************************Finish healthcheck********************************")

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

    import subprocess

    def get_top_output(self):
        try:
            # Run the `top` command and capture its output
            return subprocess.run(['top', '-b', '-n', '1'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True).stdout
        except Exception as e:
            return None

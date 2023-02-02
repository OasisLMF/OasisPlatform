from django.conf import settings
from drf_yasg.utils import swagger_auto_schema
from rest_framework import views
from rest_framework.response import Response
from .peril import PERIL_GROUPS, PERILS
from ..schemas.custom_swagger import SERVER_INFO


class PerilcodesView(views.APIView):
    """
    Return a list of all support OED peril codes in the oasislmf package
    """
    http_method_names = ['get']
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        peril_codes = {PERILS[p]['id']: {'desc': PERILS[p]['desc']} for p in PERILS.keys()}
        peril_groups = {
            PERIL_GROUPS[g]['id']: {
                'desc': PERIL_GROUPS[g]['desc'],
                'peril_ids': PERIL_GROUPS[g]['peril_ids']
            } for g in PERIL_GROUPS.keys()
        }

        return Response({
            'peril_codes': peril_codes,
            'peril_groups': peril_groups
        })


class ServerInfoView(views.APIView):
    """
    Return a list of all support OED peril codes in the oasislmf package
    """

    @swagger_auto_schema(responses={200: SERVER_INFO})
    def get(self, request):
        server_version = ""
        server_config = dict()

        try:
            with open('VERSION', 'r') as ver:
                server_version = ver.read().strip()
        except FileNotFoundError:
            server_version = ""

        server_config['DEBUG'] = settings.DEBUG
        server_config['LANGUAGE_CODE'] = settings.LANGUAGE_CODE
        server_config['TIME_ZONE'] = settings.TIME_ZONE

        # Backends
        server_config['DEFAULT_FILE_STORAGE'] = settings.DEFAULT_FILE_STORAGE
        server_config['DB_ENGINE'] = settings.DB_ENGINE

        # Storage
        server_config['STORAGE_TYPE'] = settings.STORAGE_TYPE
        server_config['MEDIA_ROOT'] = settings.MEDIA_ROOT
        server_config['AWS_STORAGE_BUCKET_NAME'] = settings.AWS_STORAGE_BUCKET_NAME
        server_config['AWS_LOCATION'] = settings.AWS_LOCATION
        server_config['AWS_SHARED_BUCKET'] = settings.AWS_SHARED_BUCKET
        server_config['AWS_QUERYSTRING_EXPIRE'] = settings.AWS_QUERYSTRING_EXPIRE
        server_config['AWS_QUERYSTRING_AUTH'] = settings.AWS_QUERYSTRING_AUTH

        # Auth Conf
        if settings.API_AUTH_TYPE == 'keycloak':
            server_config['API_AUTH_TYPE'] = settings.API_AUTH_TYPE
            server_config['OIDC_OP_AUTHORIZATION_ENDPOINT'] = settings.OIDC_OP_AUTHORIZATION_ENDPOINT
            server_config['OIDC_OP_TOKEN_ENDPOINT'] = settings.OIDC_OP_TOKEN_ENDPOINT
            server_config['OIDC_OP_USER_ENDPOINT'] = settings.OIDC_OP_USER_ENDPOINT
        else:
            server_config['API_AUTH_TYPE'] = "simple_jwt"
            server_config['ROTATE_REFRESH_TOKEN'] = settings.SIMPLE_JWT['ROTATE_REFRESH_TOKENS']
            server_config['ACCESS_TOKEN_LIFETIME'] = settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME']
            server_config['REFRESH_TOKEN_LIFETIME'] = settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME']

        return Response({
            'version': server_version,
            'config': server_config
        })

__all__ = [
    'FILE_RESPONSE',
    'HEALTHCHECK',
    'TOKEN_REFRESH_HEADER',
    'FILE_FORMAT_PARAM',
    'FILE_VALIDATION_PARAM',
]

from drf_yasg import openapi
from drf_yasg.openapi import Schema


FILE_RESPONSE = openapi.Response(
    'File Download',
    schema=Schema(type=openapi.TYPE_FILE),
    headers={
        "Content-Disposition": {
            "description": "filename",
            "type": openapi.TYPE_STRING,
            "default": 'attachment; filename="<FILE>"'
        },
        "Content-Type": {
            "description": "mime type",
            "type": openapi.TYPE_STRING
        },

    })

HEALTHCHECK = Schema(
    title='HealthCheck',
    type='object',
    properties={
        "status": Schema(title='status', read_only=True, type='string', enum=['OK'])
    }
)

SERVER_INFO = Schema(
    title='ServerInfo',
    type='object',
    required=["version", "config"],
    properties={
        "version": Schema(
            title='Server version',
            description="Version of oasis platform",
            read_only=True,
            type='string',
        ),
        "config": Schema(
            title='Server config',
            description="Oasis server public configuration",
            type='object',
        )
    }
)

TOKEN_REFRESH_HEADER = openapi.Parameter(
    'authorization',
    'header',
    description="Refresh Token",
    type='string',
    default='Bearer <refresh_token>'
)

FILE_FORMAT_PARAM = openapi.Parameter(
    'file_format',
    openapi.IN_QUERY,
    description="File format returned, default is `csv`",
    type=openapi.TYPE_STRING,
    enum=['csv', 'parquet']
)

FILE_VALIDATION_PARAM = openapi.Parameter(
    'validate',
    openapi.IN_QUERY,
    description="Validate OED files on upload, default `True`",
    type=openapi.TYPE_BOOLEAN,
)

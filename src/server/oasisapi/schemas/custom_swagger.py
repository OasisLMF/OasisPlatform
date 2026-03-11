__all__ = [
    'FILE_RESPONSE',
    'FILE_LIST_RESPONSE',
    'HEALTHCHECK',
    'TOKEN_REFRESH_HEADER',
    'FILE_FORMAT_PARAM',
    'RUN_MODE_PARAM',
    'SUBTASK_STATUS_PARAM',
    'SUBTASK_SLUG_PARAM',
    'FILE_VALIDATION_PARAM',
    'FILENAME_PARAM',
]

from rest_framework import serializers
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, OpenApiTypes, inline_serializer

FILE_RESPONSE = OpenApiResponse(
    description='File Download',
    response=OpenApiTypes.BINARY,
)

FILE_LIST_RESPONSE = OpenApiResponse(
    description='File List',
    response=inline_serializer(
        name='FileListResponse',
        fields={
            'files': serializers.ListField(child=serializers.CharField()),
        },
    ),
)

HEALTHCHECK = inline_serializer(
    name='HealthCheck',
    fields={
        'status': serializers.ChoiceField(choices=['OK'], read_only=True),
    },
)

SERVER_INFO = inline_serializer(
    name='ServerInfo',
    fields={
        'version': serializers.CharField(read_only=True),
        'config': serializers.DictField(),
        'components': serializers.DictField(),
    },
)

TOKEN_REFRESH_HEADER = OpenApiParameter(
    name='authorization',
    location=OpenApiParameter.HEADER,
    description='Refresh Token',
    type=OpenApiTypes.STR,
    default='Bearer <refresh_token>',
)

FILE_FORMAT_PARAM = OpenApiParameter(
    name='file_format',
    location=OpenApiParameter.QUERY,
    required=False,
    description="File format returned, default is `csv`",
    type=OpenApiTypes.STR,
    enum=['csv', 'parquet'],
)

RUN_MODE_PARAM = OpenApiParameter(
    name='run_mode_override',
    location=OpenApiParameter.QUERY,
    required=False,
    description="Override task run_mode, `V1 = Single server` or `V2 = distributed`",
    type=OpenApiTypes.STR,
    enum=['V1', 'V2'],
)

SUBTASK_STATUS_PARAM = OpenApiParameter(
    name='subtask_status',
    location=OpenApiParameter.QUERY,
    description="Filter response by status.",
    type=OpenApiTypes.STR,
    enum=['PENDING', 'QUEUED', 'STARTED', 'COMPLETED', 'CANCELLED', 'ERROR'],
)

SUBTASK_SLUG_PARAM = OpenApiParameter(
    name='subtask_slug',
    location=OpenApiParameter.QUERY,
    description="Filter response by slug name containing string.",
    type=OpenApiTypes.STR,
)

FILE_VALIDATION_PARAM = OpenApiParameter(
    name='validate',
    location=OpenApiParameter.QUERY,
    required=False,
    description="Validate OED files on upload, default `True`",
    type=OpenApiTypes.BOOL,
)

FILENAME_PARAM = OpenApiParameter(
    name='filename',
    location=OpenApiParameter.QUERY,
    required=True,
    description="Filename to extract from tarfile.",
    type=OpenApiTypes.STR,
)

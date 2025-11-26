__all__ = [
    'FILE_RESPONSE',
    'FILE_HEADERS',
    'FILE_LIST_RESPONSE',
    'HEALTHCHECK',
    'SERVER_INFO',
    'TOKEN_REFRESH_HEADER',
    'FILE_FORMAT_PARAM',
    'RUN_MODE_PARAM',
    'SUBTASK_STATUS_PARAM',
    'SUBTASK_SLUG_PARAM',
    'FILE_VALIDATION_PARAM',
    'FILENAME_PARAM',
]

from drf_spectacular.utils import OpenApiResponse, OpenApiParameter, OpenApiTypes


# -------------------------------
# Responses
# -------------------------------
FILE_RESPONSE = OpenApiResponse(
    response=OpenApiTypes.BINARY,
    description='File Download',
)

FILE_HEADERS = [
    OpenApiParameter(
        name='Content-Disposition',
        location=OpenApiParameter.HEADER,
        type=str,
        description='filename (e.g., attachment; filename="<FILE>")',
    ),
    OpenApiParameter(
        name='Content-Type',
        location=OpenApiParameter.HEADER,
        type=str,
        description='mime type',
    ),
]

FILE_LIST_RESPONSE = OpenApiResponse(
    response={'type': 'array', 'items': {'type': 'string'}},
    description='File List',
)

HEALTHCHECK = OpenApiResponse(
    response={
        'type': 'object',
        'properties': {
            'status': {'type': 'string', 'enum': ['OK'], 'readOnly': True}
        },
    },
    description='HealthCheck',
)

SERVER_INFO = OpenApiResponse(
    response={
        'type': 'object',
        'required': ['version', 'config', 'components'],
        'properties': {
            'version': {
                'type': 'string',
                'description': 'Version of oasis platform',
                'readOnly': True,
            },
            'config': {'type': 'object', 'description': 'Oasis server public configuration'},
            'components': {'type': 'object', 'description': 'Versions of oasis components'},
        },
    },
    description='Server Info',
)

# -------------------------------
# Parameters
# -------------------------------
TOKEN_REFRESH_HEADER = OpenApiParameter(
    name='authorization',
    location=OpenApiParameter.HEADER,
    description='Refresh Token',
    required=True,
    type=OpenApiTypes.STR,
    default='Bearer <refresh_token>',
)

FILE_FORMAT_PARAM = OpenApiParameter(
    name='file_format',
    location=OpenApiParameter.QUERY,
    description='File format returned, default is `csv`',
    required=False,
    type=OpenApiTypes.STR,
    enum=['csv', 'parquet'],
)

RUN_MODE_PARAM = OpenApiParameter(
    name='run_mode_override',
    location=OpenApiParameter.QUERY,
    description='Override task run_mode, `V1 = Single server` or `V2 = distributed`',
    required=False,
    type=OpenApiTypes.STR,
    enum=['V1', 'V2'],
)

SUBTASK_STATUS_PARAM = OpenApiParameter(
    name='subtask_status',
    location=OpenApiParameter.QUERY,
    description='Filter response by status.',
    required=False,
    type=OpenApiTypes.STR,
    enum=['PENDING', 'QUEUED', 'STARTED', 'COMPLETED', 'CANCELLED', 'ERROR'],
)

SUBTASK_SLUG_PARAM = OpenApiParameter(
    name='subtask_slug',
    location=OpenApiParameter.QUERY,
    description='Filter response by slug name containing string.',
    required=False,
    type=OpenApiTypes.STR,
)

FILE_VALIDATION_PARAM = OpenApiParameter(
    name='validate',
    location=OpenApiParameter.QUERY,
    description='Validate OED files on upload, default `True`',
    required=False,
    type=OpenApiTypes.BOOL,
)

FILENAME_PARAM = OpenApiParameter(
    name='filename',
    location=OpenApiParameter.QUERY,
    description='Filename to extract from tarfile.',
    required=True,
    type=OpenApiTypes.STR,
)

from .celery_base_conf import *

# Highest priority available
CELERY_QUEUE_MAX_PRIORITY = 10

# Set to make internal and subtasks inherit priority
CELERY_INHERIT_PARENT_PRIORITY = True

# Default Queue Name
CELERY_DEFAULT_QUEUE = "celery-v2"

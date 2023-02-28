import logging


def set_aws_log_level(log_level):
    # Set log level for s3boto3
    try:
        LOG_LEVEL = getattr(logging, log_level.upper())
    except AttributeError:
        LOG_LEVEL = logging.WARNING

    logging.getLogger('boto3').setLevel(LOG_LEVEL)
    logging.getLogger('botocore').setLevel(LOG_LEVEL)
    logging.getLogger('nose').setLevel(LOG_LEVEL)
    logging.getLogger('s3transfer').setLevel(LOG_LEVEL)
    logging.getLogger('urllib3').setLevel(LOG_LEVEL)


def set_azure_log_level(log_level):
    try:
        LOG_LEVEL = getattr(logging, log_level.upper())
    except AttributeError:
        LOG_LEVEL = logging.WARNING
    logging.getLogger('azure').setLevel(LOG_LEVEL)

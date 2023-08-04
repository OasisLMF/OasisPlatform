from __future__ import absolute_import

import logging
import tempfile
import uuid
from io import StringIO
from pathlib import Path

import yaml
from celery.utils.log import get_task_logger
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils.timezone import now

from converter.config import Config
from converter.controller import Controller
from .models import RelatedFile
from ..celery_app import celery_app
from ....common.filestore.filestore import get_filestore
from ....conf import celeryconf as celery_conf

logger = get_task_logger(__name__)


def build_converter_logger(f):
    converter_logger = logging.Logger(str(uuid.uuid4()))

    handler = logging.StreamHandler(f)
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter(
        '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
    ))
    converter_logger.addHandler(handler)

    return converter_logger


@celery_app.task(name='run_file_conversion', **celery_conf.worker_task_kwargs)
def run_file_conversion(file_id):
    instance = RelatedFile.objects.get(id=file_id)
    if not (
        RelatedFile.ConversionState.is_ready(instance.conversion_state) or
        instance.conversion_state == RelatedFile.ConversionState.PENDING
    ):
        logger.error(f"Conversion for file {file_id} is already in progress")
        return None

    instance.conversion_time = now()
    instance.conversion_state = RelatedFile.ConversionState.IN_PROGRESS
    instance.save()

    mapping_file = instance.mapping_file
    mapping_content = yaml.load(mapping_file.file.read(), yaml.SafeLoader)

    filestore = get_filestore()

    _, signed_input_url = filestore.get_storage_url(instance.file.name)

    input_file_path = Path(instance.file.name)
    input_suffixes = "".join(input_file_path.suffixes)
    input_without_suffixes = str(input_file_path)[0:-len(input_suffixes)]
    output_filename, signed_output_url = filestore.get_storage_url(
        f"{input_without_suffixes}-converted{input_suffixes}",
    )

    _, signed_mapping_url = filestore.get_storage_url(mapping_file.file.name)

    log_file = StringIO()
    try:
        # create a logger, we do this so that we dont interfere with the default logging
        # and we can inject filters to extract any sensitive formation
        converter_logger = build_converter_logger(log_file)

        # if validation files are provided setup the config for the transformation
        validation_config = {}
        if mapping_file.input_validation_file:
            validation_config[mapping_content["input_format"]["name"]] = filestore.get_storage_url(
                mapping_file.input_validation_file.name
            )[1]
        if mapping_file.output_validation_file:
            validation_config[mapping_content["output_format"]["name"]] = filestore.get_storage_url(
                mapping_file.output_validation_file.name
            )[1]

        Controller(Config(overrides={
            "parallel": False,
            "transformations": {
                mapping_content["file_type"].lower(): {
                    "extractor": {
                        "path": settings.DEFAULT_CONVERTER_CONNECTOR,
                        "options": {
                            "path": signed_input_url,
                            **settings.DEFAULT_CONVERTER_CONNECTOR_OPTIONS,
                        }
                    },
                    "input_format": mapping_content["input_format"],
                    "output_format": mapping_content["output_format"],
                    "loader": {
                        "path": settings.DEFAULT_CONVERTER_CONNECTOR,
                        "options": {
                            "path": signed_output_url,
                            **settings.DEFAULT_CONVERTER_CONNECTOR_OPTIONS,
                        }
                    },
                    "runner": {
                        "path": settings.DEFAULT_CONVERTER_RUNNER,
                        "options": settings.DEFAULT_CONVERTER_RUNNER_OPTIONS,
                    },
                    "mapping": {
                        "options": {
                            "file_override": signed_mapping_url,
                        },
                        "validation": validation_config,
                    },
                }
            }
        }), raise_errors=True, logger=converter_logger, redact_logs=not settings.DEBUG).run()

        instance.converted_file = output_filename
        instance.conversion_state = RelatedFile.ConversionState.DONE
    except Exception:
        instance.conversion_state = RelatedFile.ConversionState.ERROR
        raise
    finally:
        instance.conversion_log_file = ContentFile(log_file.getvalue(), name=f"{uuid.uuid4()}.log")
        instance.save()

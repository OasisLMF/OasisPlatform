from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
import logging

from ..celery_app_v2 import v2 as celery_app_v2
from celery.utils.log import get_task_logger
from ..analyses.v2_api.utils import store_file
from src.server.oasisapi.files.models import RelatedFile

logger = get_task_logger(__name__)


@celery_app_v2.task(name='record_combine_output', ignore_result=True)
def record_combine_output(result, analysis_id, user_id):
    from ..analyses.models import Analysis
    success, file_path_or_error = result
    analysis = Analysis.objects.get(pk=analysis_id)
    initiator = get_user_model().objects.get(pk=user_id)

    logger.info('inside record_combine_output task')
    logger.info('args: {}'.format({
        'result': result,
        'analysis_id': analysis_id,
        'user_id': user_id
    }))

    logging.info('inside record_combine_output task')

    if success:
        logger.info(f'Combine task completed successfully for analysis {analysis_id}')

        analysis.output_file = store_file(file_path_or_error,
                                          'application/gzip', initiator,
                                          filename=f'analysis_{analysis_id}_outputs.tar.gz')
        analysis.status = analysis.status_choices.RUN_COMPLETED
    else:
        logger.error(f'Combine task failed for analysis {analysis_id}: {file_path_or_error}')
        error_file = ContentFile(content=str(file_path_or_error), name=f'analysis_{analysis_id}_errors.txt')
        analysis.run_traceback_file = RelatedFile.objects.create(
            file=error_file, content_type='text/plain', creator=initiator, filename=error_file.name,
            store_as_filename=True)
        analysis.status = analysis.status_choices.RUN_ERROR

    analysis.save()

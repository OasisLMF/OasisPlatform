from src.server.oasisapi.queues.consumers import send_task_status_message, TaskStatusMessageAnalysisItem, \
    TaskStatusMessageItem, build_task_status_message, build_all_queue_status_message
from ...queues.utils import filter_queues_info
from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)


def task_updated(instance, *args, **kwargs):
    # we post all new queues together in a group
    if instance.status != instance.status_choices.PENDING:
        send_task_status_message(build_task_status_message(
            [TaskStatusMessageItem(
                queue=q,
                analyses=[TaskStatusMessageAnalysisItem(
                    analysis=instance.analysis,
                    updated_tasks=[instance],
                )],
            ) for q in filter_queues_info(instance.queue_name)]
        ))


def analysis_updated(instance, *args, **kwargs):
    """ Sends a queue notification whenever the task is finished to update workers """
    if instance.status in ['RUN_COMPLETED', 'RUN_CANCELLED', 'RUN_ERROR']:
        send_task_status_message(build_all_queue_status_message())

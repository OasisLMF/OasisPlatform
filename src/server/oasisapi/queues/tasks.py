from celery.task import task
from .utils import get_queues_info
from ..analyses.models import Analysis
from ..analyses.consumers import send_task_status_message, TaskStatusMessageItem, TaskStatusMessageAnalysisItem


@task(name='send_queue_status_digest')
def send_queue_status_digest():
    # filter queues with some nodes or activity
    all_queues = get_queues_info()
    active_queues = list(q for q in all_queues if (q['worker_count'] or q['running_count'] or q['queued_count']))

    status_message = []
    for q in active_queues:
        status_message.append(TaskStatusMessageItem(
            queue=q,
            analyses=[TaskStatusMessageAnalysisItem(
                analysis=a,
                updated_tasks=[]
            ) for a in Analysis.objects.filter(sub_task_statuses__queue_name=q['name']).distinct()]
        ))

    send_task_status_message(status_message)

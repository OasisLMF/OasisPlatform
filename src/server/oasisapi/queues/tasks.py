from celery.task import task
from src.server.oasisapi.queues.consumers import send_task_status_message, build_all_queue_status_message


@task(name='send_queue_status_digest')
def send_queue_status_digest():
    send_task_status_message(build_all_queue_status_message())

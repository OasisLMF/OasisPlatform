# from celery.decorators import task
from celery import Celery
from src.server.oasisapi.queues.consumers import send_task_status_message, build_all_queue_status_message

app_queues = Celery()


@app_queues.task(name='send_queue_status_digest')
def send_queue_status_digest():
    send_task_status_message(build_all_queue_status_message())

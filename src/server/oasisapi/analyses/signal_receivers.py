from .consumers import send_task_status_message


def task_updated(instance, *args, **kwargs):
    # we post all new queues together in a group
    if instance.status != instance.status_choices.QUEUED:
        send_task_status_message(instance.analysis, [instance], [])

from functools import reduce
from typing import Union, List, Dict, Optional, Collection

from django.conf import settings
from django.db.models import Count
from kombu import Connection

from src.server.oasisapi.celery_app import celery_app

QueueInfo = Dict[str, int]


def _get_queue_consumers(queue_name):
    with celery_app.pool.acquire(block=True) as conn:
        chan = conn.channel()
        name, message_count, consumers = chan.queue_declare(queue=queue_name, passive=True)
        return consumers


def _get_queue_message_count(queue_name):
    with celery_app.pool.acquire(block=True) as conn:
        chan = conn.channel()
        name, message_count, consumers = chan.queue_declare(queue=queue_name, passive=True)
        return message_count


def _add_to_dict(d, k, v):
    d[k] = v
    return d


def _get_broker_queue_names():
    if settings.BROKER_URL.startswith('amqp://'):
        c = Connection(settings.BROKER_URL)
        return (q['name'] for q in c.connection.client.manager.get_queues() if 'pidbox' not in q['name'] and 'celeryev' not in q['name'])
    if settings.BROKER_URL.startswith('redis://'):
        c = Connection(settings.BROKER_URL)
        return (q['name'] for q in c.connection.client.manager.channel.active_queues if 'pidbox' not in q['name'] and 'celeryev' not in q['name'])
    elif settings.BROKER_URL.startswith('memory://'):
        #
        # TODO: figure out how to get this to work for memory broker
        #
        return (celery_app.conf.task_default_routing_key, )

    raise NotImplementedError('Support for your broker is not yet supported')


def get_queues_info() -> List[QueueInfo]:
    """
    Gets a list of dictionaries containing information about the queues in the system.

    The list entries contain:
        name: The name of the queue
        queued_count: The number of tasks currently in the queue
        running_count: The number of tasks currently running on a worker
        worker_count: The number of workers currently assigned to the queue

    :return: The list of info dictionaries
    """
    from src.server.oasisapi.analyses.models import AnalysisTaskStatus

    # setup an entry for every element in the broker (this will include
    # queues with no workers yet)
    res = [
        {
            'name': q,
            'pending_count': 0,
            'queued_count': 0,
            'running_count': 0,
            'queue_message_count': _get_queue_message_count(q),
            'worker_count': _get_queue_consumers(q),
        } for q in _get_broker_queue_names()
    ]

    # get the stats of the running and queued tasks
    pending = reduce(
        lambda current, value: _add_to_dict(current, value['queue_name'], value['count']),
        AnalysisTaskStatus.objects.filter(
            status=AnalysisTaskStatus.status_choices.PENDING,
        ).values(
            'queue_name',
        ).annotate(
            count=Count('pk'),
        ),
        {}
    )

    running = reduce(
        lambda current, value: _add_to_dict(current, value['queue_name'], value['count']),
        AnalysisTaskStatus.objects.filter(
            status=AnalysisTaskStatus.status_choices.STARTED,
        ).values(
            'queue_name',
        ).annotate(
            count=Count('pk'),
        ),
        {}
    )

    queued = reduce(
        lambda current, value: _add_to_dict(current, value['queue_name'], value['count']),
        AnalysisTaskStatus.objects.filter(
            status=AnalysisTaskStatus.status_choices.QUEUED,
        ).values(
            'queue_name',
        ).annotate(
            count=Count('pk'),
        ),
        {}
    )

    for entry in res:
        entry['pending_count'] = pending.get(entry['name'], 0)
        entry['queued_count'] = queued.get(entry['name'], 0)
        entry['running_count'] = running.get(entry['name'], 0)

    return res


def filter_queues_info(
    queue_names: Optional[Union[Collection[str], str]] = None,
    info: Optional[List[Dict[str, int]]] = None
) -> List[Dict[str, int]]:
    """
    Filters the info to only include the queues with the given names.

    :param queue_names: Either a string giving the queue name or a list
        of strings giving the queue names to include in the result.
    :param info: The unfiltered queue info list. If omitted the info is
        fetched from the broker

    :return: The list of info dictionaries
    """
    info = info or get_queues_info()

    return [
        q for q in info if (queue_names is None or q['name'] in queue_names or q['name'] == queue_names)
    ]

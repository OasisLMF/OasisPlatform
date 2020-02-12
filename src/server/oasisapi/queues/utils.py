from functools import reduce
from typing import Union, List, Dict, Optional, Collection

from django.conf import settings
from django.db.models import Count
from pyrabbit import Client

from src.conf import iniconf
from src.server.oasisapi.celery import celery_app


QueueInfo = Dict[str, int]


def _add_to_dict(d, k, v):
    d[k] = v
    return d


def _get_broker_queue_names():
    if settings.BROKER_URL.startswith('amqp://'):
        c = Client(
            '{}:{}/'.format(
                iniconf.settings.get('celery', 'rabbit_host', fallback='127.0.0.1'),
                iniconf.settings.get('celery', 'rabbit_management_port', fallback=15672),
            ),
            iniconf.settings.get('celery', 'rabbit_user', fallback='rabbit'),
            iniconf.settings.get('celery', 'rabbit_pass', fallback='rabbit'),
        )
        return (q['name'] for q in c.get_queues())
    elif settings.BROKER_URL.startswith('memory://'):
        #
        # TODO: figure out how to get this to work for memory broker
        #
        return (celery_app.conf.task_default_routing_key, )

    raise NotImplementedError('Support for your broker is not yet supported')


def _get_active_queues():
    if settings.BROKER_URL.startswith('memory://'):
        #
        # TODO: figure out how to get this to work for memory broker
        #
        return {}

    return celery_app.control.inspect().active_queues()


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
            'queued_count': 0,
            'running_count': 0,
            'worker_count': 0,
        } for q in _get_broker_queue_names()
    ]

    # increment the number of workers available for each queue
    for worker in _get_active_queues().values():
        for queue in worker:
            try:
                next(r for r in res if r['name'] == queue['routing_key'])['worker_count'] += 1
            except StopIteration:
                # in case there are workers around still for inactive queues add it here
                res.append({
                    'name': queue['routing_key'],
                    'queued_count': 0,
                    'running_count': 0,
                    'worker_count': 1,
                })

    # get the stats of the running and queued tasks
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
        entry['queued_count'] = queued.get(entry['name'], 0)
        entry['running_count'] = running.get(entry['name'], 0)

    return res


def filter_queues_info(
    queue_names: Union[Collection[str], str],
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
        q for q in info if (q['name'] in queue_names or q['name'] == queue_names)
    ]

from functools import reduce
from typing import Union, List, Dict, Optional, Collection

from django.db.models import Count
from pyrabbit import Client

from src.conf.iniconf import settings
from src.server.oasisapi.celery import celery_app


def _add_to_dict(d, k, v):
    d[k] = v
    return d


def get_queues_info() -> List[Dict[str, int]]:
    """
    Gets a list of dictionaries containing information about the queues in the system.

    The list entries contain:
        name: The name of the queue
        queued_count: The number of tasks currently in the queue
        assigned_count: The number of tasks currently assigned to a worker
        worker_count: The number of workers currently assigned to the queue

    :return: The list of info dictionaries
    """
    from src.server.oasisapi.analyses.models import AnalysisTaskStatus

    # setup an entry for every element in the broker (this will include
    # queues with no workers yet)
    c = Client(
        '{}:{}/'.format(
            settings.get('celery', 'rabbit_host', fallback='127.0.0.1'),
            settings.get('celery', 'rabbit_management_port', fallback=15672),
        ),
        settings.get('celery', 'rabbit_user'),
        settings.get('celery', 'rabbit_pass'),
    )

    res = [
        {
            'name': q['name'],
            'queued_count': 0,
            'running_count': 0,
            'worker_count': 0,
        } for q in c.get_queues()
    ]

    # increment the number of workers available for each queue
    for worker in celery_app.control.inspect().active_queues().values():
        for queue in worker:
            try:
                print(queue)
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

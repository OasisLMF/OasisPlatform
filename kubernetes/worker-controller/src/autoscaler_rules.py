import logging
import math

from models import ModelState


def get_desired_worker_count(auto_scaling: dict, model_state: ModelState):

    """
    This function is called for each worker deployment (model) having one or more
    analyses running.

    The purpose of the function is to return the desired number of workers (replicas)
    based on this worker deployments type of auto scaling and chunk size.

    If the auto scaling configuration is wrong or incomplete the default worker count
    will be defaulted to 1.
TODO
    :param auto_scaling: Auto scaling configuration (see oasis-models helm chart)
    :param model_state: Number of chunks for this model
    :return: Desired number of workers to scale to.
    """

    strategy = auto_scaling.get('scaling_strategy')

    if strategy:

        if strategy == 'FIXED_WORKERS':

            count = get_req_setting(auto_scaling, 'worker_count_fixed')

            return int(count)

        # TODO
        elif strategy == 'QUEUE_LOAD':

            worker_count_max = get_req_setting(auto_scaling, 'worker_count_max')
            analyses = model_state['analyses']

            return min(analyses, worker_count_max)

        elif strategy == 'DYNAMIC_TASKS':

            chunks_per_worker = auto_scaling.get('chunks_per_worker')
            worker_count_max = get_req_setting(auto_scaling, 'worker_count_max')

            workers = math.ceil(int(model_state.get('tasks', 0)) / int(chunks_per_worker))
            return min(workers, int(worker_count_max))

        else:
            raise ValueError(f'Unsupported scaling strategy: {strategy}')
    else:
        raise ValueError(f'No valid auto scaling configuration for model: {auto_scaling}')

    return 1


def get_req_setting(auto_scaling: dict, name: str):
    value = auto_scaling.get(name, None)
    if not value:
        raise ValueError(f'Missing required attribute \'{name}\'')
    return value

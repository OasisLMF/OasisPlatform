import math

from models import ModelState


def get_desired_worker_count(autoscaling_setting: dict, model_state: ModelState):
    """
    This function is called for each worker deployment (model) having one or more
    analyses running.

    The purpose of the function is to return the desired number of workers (replicas)
    based on this worker deployments type of auto scaling and model state (number of
    tasks and running analyses).

    :param autoscaling_setting: Auto scaling configuration (see oasis API for more details)
    :param model_state: State of this model such as number of running analyses and tasks.
    :return: Desired number of workers to scale to.
    """

    strategy = autoscaling_setting.get('scaling_strategy')

    if strategy:

        if strategy == 'FIXED_WORKERS':

            count = get_req_setting(autoscaling_setting, 'worker_count_fixed')

            return int(count)

        elif strategy == 'QUEUE_LOAD':

            worker_count_max = get_req_setting(autoscaling_setting, 'worker_count_max')
            analyses = model_state['analyses']

            return min(analyses, worker_count_max)

        elif strategy == 'DYNAMIC_TASKS':

            chunks_per_worker = autoscaling_setting.get('chunks_per_worker')
            worker_count_max = get_req_setting(autoscaling_setting, 'worker_count_max')

            workers = math.ceil(int(model_state.get('tasks', 0)) / int(chunks_per_worker))
            return min(workers, int(worker_count_max))

        else:
            raise ValueError(f'Unsupported scaling strategy: {strategy}')
    else:
        raise ValueError(f'No valid auto scaling configuration for model: {autoscaling_setting}')


def get_req_setting(autoscaling_setting: dict, name: str):
    """
    Return the value of name in the auto_scaling setting. If not found, raise exception.

    :param autoscaling_setting: Autoscaling setting
    :param name: Name of setting
    :return: Value.
    """
    value = autoscaling_setting.get(name, None)
    if not value:
        raise ValueError(f'Missing required attribute \'{name}\'')
    return value

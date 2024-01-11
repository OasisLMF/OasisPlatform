import math

from models import ModelState


def get_desired_worker_count(autoscaling_setting: dict, model_state: ModelState, never_shutdown_fixed_workers: bool = False):
    """
    This function is called for each worker deployment (model) having one or more
    analyses running.

    The purpose of the function is to return the desired number of workers (replicas)
    based on this worker deployments type of auto scaling and model state (number of
    tasks and running analyses).

    :param autoscaling_setting: Auto scaling configuration (see oasis API for more details)
    :param model_state: State of this model such as number of running analyses and tasks.
    :param never_shutdown_fixed_workers: Debug model which dosn't spin down workers when in fixed mode
    :return: Desired number of workers to scale to.
    """

    strategy = autoscaling_setting.get('scaling_strategy')
    worker_count_min = int(autoscaling_setting.get('worker_count_min', 0))
    analysis_in_progress = any([
        model_state.get('tasks', 0) > 0,
        model_state.get('analyses', 0) > 0
    ])

    # Guard for missing options
    if not strategy:
        raise ValueError(f'No valid auto scaling configuration for model: {autoscaling_setting}')

    if strategy in ['QUEUE_LOAD', 'DYNAMIC_TASKS']:
        worker_count_max = get_req_setting(autoscaling_setting, 'worker_count_max')

    # Debugging model (keep all fixed workers alive)
    if strategy == 'FIXED_WORKERS' and never_shutdown_fixed_workers:
        return max(
            int(get_req_setting(autoscaling_setting, 'worker_count_fixed')),
            worker_count_min,
        )

    # Scale down to Minimum worker count
    if not analysis_in_progress:
        return worker_count_min

    # Run a fixed set of workers when analysis is on queue
    elif strategy == 'FIXED_WORKERS':
        count = int(get_req_setting(autoscaling_setting, 'worker_count_fixed'))
        return max(
            count,
            worker_count_min,
        )

    # Run one worker per analysis in progress
    elif strategy == 'QUEUE_LOAD':
        analyses = model_state['analyses']
        return max(
            min(analyses, worker_count_max),
            worker_count_min,
        )

    # Run `n` workers based on number of tasks on queue
    elif strategy == 'DYNAMIC_TASKS':
        chunks_per_worker = autoscaling_setting.get('chunks_per_worker')
        workers = math.ceil(int(model_state.get('tasks', 0)) / int(chunks_per_worker))
        return max(
            min(workers, worker_count_max),
            worker_count_min,
        )

    else:
        raise ValueError(f'Unsupported scaling strategy: {strategy}')



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

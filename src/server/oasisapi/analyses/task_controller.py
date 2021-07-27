import uuid
from itertools import chain as iterchain
from importlib import import_module
from math import ceil
from typing import List, Type, TYPE_CHECKING, Tuple, Optional

from celery import signature, chord
from celery.canvas import Signature, chain
from django.contrib.auth.models import User
from kombu.common import Broadcast
from oasislmf.utils.data import get_dataframe

from src.conf.iniconf import settings

if TYPE_CHECKING:
    from src.server.oasisapi.analyses.models import Analysis, AnalysisTaskStatus


class TaskParams:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class Controller:
    INPUT_GENERATION_CHUNK_SIZE = settings.getint('worker', 'INPUT_GENERATION_CHUNK_SIZE', fallback=1)

    @classmethod
    def get_subtask_signature(cls, task_name, analysis, initiator, run_data_uuid, slug, queue, params: TaskParams) -> Signature:
        """
        Generates a signature representing the subtask. This task will have the initiator_id, analysis_id and
        slug set along with other provided kwargs.

        :param task_name: The name of the task as registered with celery
        :param analysis: The analysis object to run the task for
        :param initiator: The initiator who started the parent task
        :param run_data_uuid: The suffix for the runs current data directory
        :param slug: The slug identifier for the task, this should be unique for a given analysis
        :param queue: The name of the queue the task will be published to
        :param params: The parameters to send to the task
        :return: Signature representing the task
        """
        from src.server.oasisapi.analyses.tasks import record_sub_task_success, record_sub_task_failure
        sig = signature(
            task_name,
            queue=queue,
            args=params.args,
            kwargs={
                'initiator_id': initiator.pk,
                'analysis_id': analysis.pk,
                'slug': slug,
                'run_data_uuid': run_data_uuid,
                **params.kwargs,
            },
        )

        # add task to set the status of the sub task status record on success
        sig.link(record_sub_task_success.s(analysis_id=analysis.pk, initiator_id=initiator.pk, task_slug=slug))
        # add task to set the status of the sub task status record on failure
        sig.link_error(record_sub_task_failure.s(analysis_id=analysis.pk, initiator_id=initiator.pk, task_slug=slug))

        return sig

    @classmethod
    def get_subtask_status(cls, analysis: 'Analysis', name: str, slug: str, queue_name: str) -> 'AnalysisTaskStatus':
        """
        Gets the task status object for a given subtask.

        :param analysis: The analysis object to run the task for
        :param name: A human readable name for the task
        :param slug: The slug identifier for the task, this should be unique for a given analysis
        :param queue_name: The name of the queue the task is sent to
        :return: An uncommitted AnalysisTaskStatus object representing the task
        """
        from src.server.oasisapi.analyses.models import AnalysisTaskStatus

        return AnalysisTaskStatus(
            analysis=analysis,
            slug=slug,
            name=name,
            queue_name=queue_name,
        )

    @classmethod
    def get_subtask_statuses_and_signature(
        cls,
        task_name,
        analysis,
        initiator,
        run_data_uuid,
        status_name,
        status_slug,
        queue,
        params: Optional[TaskParams] = None,
    ) -> Tuple[List['AnalysisTaskStatus'], Signature]:
        """
        Gets all teh status objects and signature for a given subtask

        :param task_name: The name of the task as registered with celery
        :param analysis: The analysis object to run the task for
        :param initiator: The initiator who started the parent task
        :param run_data_uuid: The suffix for the runs current data directory
        :param status_name: A human readable name for the task
        :param status_slug: The slug identifier for the task, this should be unique for a given analysis
        :param queue: The name of the queue the task will be published to
        :param params: The parameters to send to the task
        :return: Signature representing the task
        """
        params = params or TaskParams()
        return (
            [cls.get_subtask_status(analysis, status_name, status_slug, queue)],
            cls.get_subtask_signature(task_name, analysis, initiator, run_data_uuid, status_slug, queue, params),
        )

    @classmethod
    def get_subchord_statuses_and_signature(
        cls,
        task_name,
        analysis,
        initiator,
        run_data_uuid,
        status_name,
        status_slug,
        queue,
        params: List[TaskParams],
        body: Tuple[List['AnalysisTaskStatus'], Signature],
    ) -> Tuple[List['AnalysisTaskStatus'], Signature]:
        """
        Gets all the status objects and signature for a given subchord

        :param task_name: The name of the task as registered with celery
        :param analysis: The analysis object to run the task for
        :param initiator: The initiator who started the parent task
        :param run_data_uuid: The suffix for the runs current data directory
        :param status_name: A human readable name for the task
        :param status_slug: The slug identifier for the task, this should be unique for a given analysis
        :param queue: The name of the queue the task will be published to
        :param params: The parameters to send to the task
        :param body: A tuple containing the statuses and signature of the body task
        :return: Signature representing the task
        """
        statuses, tasks = zip(*[
            cls.get_subtask_statuses_and_signature(task_name, analysis, initiator, run_data_uuid, f'{status_name} {idx}', f'{status_slug}-{idx}', queue, params=p)
            for idx, p in enumerate(params)
        ])

        c = chord(tasks, body=body[1], queue=queue)
        c.link_error(signature('chord_error_callback'))

        return list(iterchain(*statuses, body[0])), c

    @classmethod
    def _split_tasks_and_statuses(cls, joined: List[Tuple[List['AnalysisTaskStatus'], Signature]]) -> Tuple[List['AnalysisTaskStatus'], List[Signature]]:
        """
        Takes a list of status list, signature tuples. Returns a tuple of a flattened
        status list and a list of signatures.

        :param joined: List of objects to split
        :return: The flattened status and signatures tuple
        """
        return tuple(zip(*joined))

    @classmethod
    def _start(
        cls,
        analysis,
        initiator,
        tasks: List[Signature],
        statuses: List['AnalysisTaskStatus'],
        run_data_uuid: str,
        traceback_property: str,
        failure_status: str,
    ) -> chain:
        """
        Starts the task running

        :param analysis: The analysis to run the tasks for
        :param initiator: The user starting the task
        :param tasks: Signatures for the subtasks to run
        :param statuses: Statuses for storing the status of the subtasks
        :param run_data_uuid: The suffix for the runs current data directory
        :param traceback_property: The property to store the traceback on failure
        :param failure_status: The Status to use when the task fails

        :return: The chain representing the running task, this has already been sent
            to the broker
        """
        from src.server.oasisapi.analyses.models import AnalysisTaskStatus
        analysis.sub_task_statuses.all().delete()
        AnalysisTaskStatus.objects.create_statuses(iterchain(*statuses))

        c = chain(*tasks)
        c.link_error(signature(
            'handle_task_failure',
            kwargs={
                'analysis_id': analysis.pk,
                'initiator_id': initiator.pk,
                'run_data_uuid': run_data_uuid,
                'traceback_property': traceback_property,
                'failure_status': failure_status,
            },
        ))
        c.delay({})
        return c

    @classmethod
    def get_generate_inputs_queue(cls, analysis: 'Analysis', initiator: User) -> str:
        """
        Gets the name of the queue to send the input generation tasks to.

        :param analysis: The analysis to generate input data for
        :param initiator: The user who initiated the task

        :return: The name of the queue
        """
        return str(analysis.model)

    @classmethod
    def get_inputs_generation_tasks(cls, analysis: 'Analysis', initiator: User, run_data_uuid: str,) -> Tuple[List['AnalysisTaskStatus'], List[Signature]]:
        """
        Gets the tasks to chain together for input generation

        :param analysis: The analysis to tun the tasks for
        :param initiator: The user starting the tasks
        :param run_data_uuid: The suffix for the runs current data directory

        :return: Tuple containing the statuses to create and signatures to chain
        """
        location_data = get_dataframe(src_buf=analysis.portfolio.location_file.read().decode())

        num_chunks = ceil(len(location_data) / cls.INPUT_GENERATION_CHUNK_SIZE)

        queue = cls.get_generate_inputs_queue(analysis, initiator)
        base_kwargs = {
            'loc_file': analysis.portfolio.get_link('location_file'),
            'settings_file': analysis.get_link('settings_file'),
            'complex_data_files': analysis.create_complex_model_data_file_dicts() or None,
        }
        files_kwargs = {
            'loc_file': analysis.portfolio.get_link('location_file'),
            'acc_file': analysis.portfolio.get_link('accounts_file'),
            'info_file': analysis.portfolio.get_link('reinsurance_info_file'),
            'scope_file': analysis.portfolio.get_link('reinsurance_scope_file'),
            'analysis_settings_file': analysis.get_link('settings_file'),
            'complex_data_files': analysis.create_complex_model_data_file_dicts() or None,
        }

        return cls._split_tasks_and_statuses([
            cls.get_subtask_statuses_and_signature(
                'prepare_input_generation_params',
                analysis,
                initiator,
                run_data_uuid,
                'Prepare input generation params',
                'prepare-input-generation-params',
                queue,
                TaskParams(**base_kwargs),
            ),
            cls.get_subchord_statuses_and_signature(
                'prepare_keys_file_chunk',
                analysis,
                initiator,
                run_data_uuid,
                'Prepare keys file',
                'prepare-keys-file',
                queue,
                [
                    TaskParams(
                        idx,
                        num_chunks,
                        **base_kwargs,
                    ) for idx in range(num_chunks)
                ],
                cls.get_subtask_statuses_and_signature(
                    'collect_keys',
                    analysis,
                    initiator,
                    run_data_uuid,
                    'Collect keys',
                    'collect-keys',
                    queue,
                    TaskParams(**base_kwargs),
                ),
            ),
            cls.get_subtask_statuses_and_signature(
                'write_input_files',
                analysis,
                initiator,
                run_data_uuid,
                'Write input files',
                'write-input-files',
                queue,
                TaskParams(**files_kwargs),
            ),
            cls.get_subtask_statuses_and_signature(
                'record_input_files',
                analysis,
                initiator,
                run_data_uuid,
                'Record input files',
                'record-input-files',
                'celery',
            ),
            cls.get_subtask_statuses_and_signature(
                'cleanup_input_generation',
                analysis,
                initiator,
                run_data_uuid,
                'Cleanup input generation',
                'cleanup-input-generation',
                queue,
            ),
        ])

    @classmethod
    def generate_inputs(cls, analysis: 'Analysis', initiator: User) -> chain:
        """
        Starts the input generation chain

        :param analysis: The analysis to start input generation for
        :param initiator: The user starting the input generation
        :param run_data_uuid: The suffix for the runs current data directory

        :return: The started chain
        """
        from src.server.oasisapi.analyses.models import Analysis

        run_data_uuid = uuid.uuid4().hex
        statuses, tasks = cls.get_inputs_generation_tasks(analysis, initiator, run_data_uuid)

        task = analysis.generate_inputs_task_id = cls._start(
            analysis,
            initiator,
            tasks,
            statuses,
            run_data_uuid,
            'input_generation_traceback_file',
            Analysis.status_choices.INPUTS_GENERATION_ERROR,
        ).id or ''  # TODO: is shouldn't return None but is for some reason so for no guard against it
        analysis.save()
        return task

    @classmethod
    def get_generate_losses_queue(cls, analysis: 'Analysis', initiator: User) -> str:
        """
        Gets the name of the queue to send the loss generation tasks to.

        :param analysis: The analysis to generate loss data for
        :param initiator: The user who initiated the task

        :return: The name of the queue
        """
        return str(analysis.model)

    @classmethod
    def get_loss_generation_tasks(cls, analysis: 'Analysis', initiator: User, run_data_uuid: str):
        """
        Gets the tasks to chain together for loss generation

        :param analysis: The analysis to tun the tasks for
        :param initiator: The user starting the tasks
        :param run_data_uuid: The suffix for the runs current data directory

        :return: Tuple containing the statuses to create and signatures to chain
        """
        default_num_chunks = settings.getint('worker', 'default_num_analysis_chunks', fallback=4)
        num_chunks = analysis.model.num_analysis_chunks or default_num_chunks

        queue = cls.get_generate_losses_queue(analysis, initiator)
        base_kwargs = {
            'input_location': analysis.get_link('input_file'),
            'analysis_settings_file': analysis.get_link('settings_file'),
            'complex_data_files': analysis.create_complex_model_data_file_dicts() or None,
        }

        return cls._split_tasks_and_statuses([
            cls.get_subtask_statuses_and_signature(
                'prepare_losses_generation_params',
                analysis,
                initiator,
                run_data_uuid,
                'Prepare losses generation params',
                'prepare-losses-generation-params',
                queue,
                TaskParams(
                    num_chunks=num_chunks,
                    **base_kwargs,
                )
            ),
            cls.get_subtask_statuses_and_signature(
                'prepare_losses_generation_directory',
                analysis,
                initiator,
                run_data_uuid,
                'Prepare losses generation directory',
                'prepare-losses-generation-directory',
                queue,
                TaskParams(**base_kwargs),
            ),
            cls.get_subchord_statuses_and_signature(
                'generate_losses_chunk',
                analysis,
                initiator,
                run_data_uuid,
                'Generate losses chunk',
                'generate-losses-chunk',
                queue,
                [TaskParams(idx, num_chunks, **base_kwargs,) for idx in range(num_chunks)],
                cls.get_subtask_statuses_and_signature(
                    'generate_losses_output',
                    analysis,
                    initiator,
                    run_data_uuid,
                    'Generate losses output',
                    'generate_losses_output',
                    queue,
                    TaskParams(**base_kwargs),
                ),
            ),
            cls.get_subtask_statuses_and_signature(
                'record_losses_files',
                analysis,
                initiator,
                run_data_uuid,
                'Record losses files',
                'record-losses-files',
                'celery',
                TaskParams(**base_kwargs),
            ),
            cls.get_subtask_statuses_and_signature(
                'cleanup_losses_generation',
                analysis,
                initiator,
                run_data_uuid,
                'Cleanup losses generation',
                'cleanup-losses-generation',
                'model-worker-broadcast',
                TaskParams(**base_kwargs),
            ),
        ])

    @classmethod
    def generate_losses(cls, analysis: 'Analysis', initiator: User):
        """
        Starts the loss generation chain

        :param analysis: The analysis to start loss generation for
        :param initiator: The user starting the loss generation

        :return: The started chain
        """
        from src.server.oasisapi.analyses.models import Analysis

        run_data_uuid = uuid.uuid4().hex
        statuses, tasks = cls.get_loss_generation_tasks(analysis, initiator, run_data_uuid)

        task = analysis.run_task_id = cls._start(
            analysis,
            initiator,
            tasks,
            statuses,
            run_data_uuid,
            'run_traceback_file',
            Analysis.status_choices.RUN_ERROR,
        ).id or ''  # TODO: is shouldn't return None but is for some reason so for no guard against it
        analysis.save()
        return task


def get_analysis_task_controller() -> Type[Controller]:
    """
    Gets the controller class for running analysis commands

    This can be overridden by setting the worker.ANALYSIS_TASK_CONTROLLER setting.

    :return: The type of controller specified
    """
    controller_path = settings.get(
        'worker',
        'ANALYSIS_TASK_CONTROLLER',
        fallback='src.server.oasisapi.analyses.task_controller.Controller'
    )

    controller_module, controller_class = controller_path.rsplit('.', maxsplit=1)
    return getattr(
        import_module(controller_module),
        controller_class
    )

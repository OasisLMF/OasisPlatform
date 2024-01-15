import uuid
from importlib import import_module
from itertools import chain as iterchain
from math import ceil
from typing import List, Type, TYPE_CHECKING, Tuple, Optional

from celery import signature, chord
from celery.canvas import Signature, chain
from django.contrib.auth.models import User

from src.conf.iniconf import settings
from ...files.models import file_storage_link

if TYPE_CHECKING:
    from src.server.oasisapi.analyses.models import Analysis, AnalysisTaskStatus

import logging


class TaskParams:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class Controller:

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
        from src.server.oasisapi.analyses.v2_api.tasks import record_sub_task_success, record_sub_task_failure
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
            cls.get_subtask_statuses_and_signature(task_name, analysis, initiator, run_data_uuid,
                                                   f'{status_name} {idx}', f'{status_slug}-{idx}', queue, p)
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
    def _create_chain(
            cls,
            analysis,
            initiator,
            tasks: List[Signature],
            run_data_uuid: str,
            traceback_property: str,
            failure_status: str,
    ) -> chain:
        """
        Create a chain of all tasks

        :param analysis: The analysis to run the tasks for
        :param initiator: The user starting the task
        :param tasks: Signatures for the subtasks to run
        :param run_data_uuid: The suffix for the runs current data directory
        :param traceback_property: The property to store the traceback on failure
        :param failure_status: The Status to use when the task fails

        :return: The chain representing the tasks
        """
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
        return c

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

        c = cls._create_chain(
            analysis,
            initiator,
            tasks,
            run_data_uuid,
            traceback_property,
            failure_status,
        )
        c.delay({}, priority=analysis.priority)
        return c

    @classmethod
    def get_generate_inputs_queue(cls, analysis: 'Analysis', initiator: User) -> str:
        """
        Gets the name of the queue to send the input generation tasks to.

        :param analysis: The analysis to generate input data for
        :param initiator: The user who initiated the task

        :return: The name of the queue
        """
        return str(analysis.model) + '-v2'

    @classmethod
    def get_inputs_generation_tasks(
            cls, analysis: 'Analysis', initiator: User, run_data_uuid: str, num_chunks: int,
            analysis_finish_status='READY') -> Tuple[List['AnalysisTaskStatus'], List[Signature]]:
        """
        Gets the tasks to chain together for input generation

        :param analysis: The analysis to tun the tasks for
        :param initiator: The user starting the tasks
        :param run_data_uuid: The suffix for the runs current data directory
        :param num_chunks: The number of lookup chunks to split task into
        :param analysis_finish_status: The status to set once the input generation finish, READY as default, but
        generate_input_and_run will set it to RUN_STARTED.

        :return: Tuple containing the statuses to create and signatures to chain
        """
        queue = cls.get_generate_inputs_queue(analysis, initiator)
        base_kwargs = {
            'loc_file': file_storage_link(analysis.portfolio.location_file),
            'analysis_settings_file': file_storage_link(analysis.settings_file),
            'complex_data_files': analysis.create_complex_model_data_file_dicts() or None,
        }
        files_kwargs = {
            'loc_file': file_storage_link(analysis.portfolio.location_file),
            'acc_file': file_storage_link(analysis.portfolio.accounts_file),
            'info_file': file_storage_link(analysis.portfolio.reinsurance_info_file),
            'scope_file': file_storage_link(analysis.portfolio.reinsurance_scope_file),
            'analysis_settings_file': file_storage_link(analysis.settings_file),
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
            cls.get_subtask_statuses_and_signature(
                'pre_analysis_hook',
                analysis,
                initiator,
                run_data_uuid,
                'Pre analysis hook',
                'pre-analysis-hook',
                queue,
                TaskParams(**files_kwargs),
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
                'celery-v2',
                TaskParams(analysis_finish_status=analysis_finish_status),
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
    def generate_inputs(cls, analysis: 'Analysis', initiator: User, loc_lines: int) -> chain:
        """
        Starts the input generation chain

        :param analysis: The analysis to start input generation for
        :param initiator: The user starting the input generation
        :param run_data_uuid: The suffix for the runs current data directory

        :return: The started chain
        """
        from src.server.oasisapi.analyses.models import Analysis

        # fetch the number of lookup chunks and store in analysis
        num_chunks = cls._get_inputs_generation_chunks(analysis, loc_lines)

        run_data_uuid = uuid.uuid4().hex
        statuses, tasks = cls.get_inputs_generation_tasks(analysis, initiator, run_data_uuid, num_chunks)

        # Add chunk info to analysis
        analysis.lookup_chunks = num_chunks
        analysis.save()

        chain = cls._start(
            analysis,
            initiator,
            tasks,
            statuses,
            run_data_uuid,
            'input_generation_traceback_file',
            Analysis.status_choices.INPUTS_GENERATION_ERROR,
        )
        return chain

    @classmethod
    def _get_inputs_generation_chunks(cls, analysis, loc_lines):
        # loc_lines = sum(1 for line in analysis.portfolio.location_file.read())

        # Get options
        if analysis.chunking_options is not None:
            chunking_options = analysis.chunking_options        # Use options from Analysis
        else:
            chunking_options = analysis.model.chunking_options  # Use defaults set on model

        # Set chunks
        if chunking_options.lookup_strategy == 'FIXED_CHUNKS':
            num_chunks = min(chunking_options.fixed_lookup_chunks, loc_lines)
        elif chunking_options.lookup_strategy == 'DYNAMIC_CHUNKS':
            loc_lines_per_chunk = chunking_options.dynamic_locations_per_lookup
            num_chunks = min(ceil(loc_lines / loc_lines_per_chunk), chunking_options.dynamic_chunks_max)

        return num_chunks

    @classmethod
    def get_generate_losses_queue(cls, analysis: 'Analysis', initiator: User) -> str:
        """
        Gets the name of the queue to send the loss generation tasks to.

        :param analysis: The analysis to generate loss data for
        :param initiator: The user who initiated the task

        :return: The name of the queue
        """
        return str(analysis.model) + '-v2'

    @classmethod
    def get_loss_generation_tasks(cls, analysis: 'Analysis', initiator: User, run_data_uuid: str, num_chunks: int):
        """
        Gets the tasks to chain together for loss generation

        :param analysis: The analysis to tun the tasks for
        :param initiator: The user starting the tasks
        :param run_data_uuid: The suffix for the runs current data directory
        :param num_chunks: The number of loss chunks to split task into

        :return: Tuple containing the statuses to create and signatures to chain
        """
        queue = cls.get_generate_losses_queue(analysis, initiator)
        base_kwargs = {
            'input_location': file_storage_link(analysis.input_file),
            'analysis_settings_file': file_storage_link(analysis.settings_file),
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
                ),
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
                'celery-v2',
                TaskParams(**base_kwargs),
            ),
            cls.get_subtask_statuses_and_signature(
                'cleanup_losses_generation',
                analysis,
                initiator,
                run_data_uuid,
                'Cleanup losses generation',
                'cleanup-losses-generation',
                queue,
                TaskParams(**base_kwargs),
            ),
        ])

    @classmethod
    def generate_losses(cls, analysis: 'Analysis', initiator: User, events_total: int):
        """
        Starts the loss generation chain

        :param analysis: The analysis to start loss generation for
        :param initiator: The user starting the loss generation

        :return: The started chain
        """
        logging.info("-- Generate losses --")
        from src.server.oasisapi.analyses.models import Analysis

        num_chunks = cls._get_loss_generation_chunks(analysis, events_total)
        logging.info("result: {num_chunks}")
        run_data_uuid = uuid.uuid4().hex
        statuses, tasks = cls.get_loss_generation_tasks(analysis, initiator, run_data_uuid, num_chunks)

        # add chunk info to analysis
        analysis.analysis_chunks = num_chunks
        analysis.save()

        chain = cls._start(
            analysis,
            initiator,
            tasks,
            statuses,
            run_data_uuid,
            'run_traceback_file',
            Analysis.status_choices.RUN_ERROR,
        )
        return chain

    @classmethod
    def _get_loss_generation_chunks(cls, analysis, events_total):
        logging.info("-- call Generate losses get chunks --")
        # Get options
        if analysis.chunking_options is not None:
            chunking_options = analysis.chunking_options        # Use options from Analysis
        else:
            chunking_options = analysis.model.chunking_options  # Use defaults set on model

        # fetch number of event chunks
        if chunking_options.loss_strategy == 'FIXED_CHUNKS':
            num_chunks = chunking_options.fixed_analysis_chunks
        elif chunking_options.loss_strategy == 'DYNAMIC_CHUNKS':
            events_per_chunk = chunking_options.dynamic_events_per_analysis
            num_chunks = min(ceil(events_total / events_per_chunk), chunking_options.dynamic_chunks_max)

        logging.info(f'loss_strategy: {chunking_options.loss_strategy}')
        logging.info(f'dynamic_events_per_analysis: {chunking_options.dynamic_events_per_analysis}')
        logging.info(f'events_total: {events_total}')
        logging.info(f'events_per_chunk: {events_per_chunk}')
        logging.info(f'dynamic_chunks_max: {chunking_options.dynamic_chunks_max}')
        logging.info(f'ceil(events_total / events_per_chunk): {ceil(events_total / events_per_chunk)}')

        return num_chunks

    @classmethod
    def generate_input_and_losses(cls, analysis: 'Analysis', initiator: User):
        """
        Starts the input generation chain

        :param analysis: The analysis to start input generation for
        :param initiator: The user starting the input generation
        :param run_data_uuid: The suffix for the runs current data directory

        :return: The started chain
        """
        """TODO
        Starts the loss generation chain

        :param analysis: The analysis to start loss generation for
        :param initiator: The user starting the loss generation

        :return: The started chain
        """
        from src.server.oasisapi.analyses.models import Analysis

        # fetch the number of lookup chunks and store in analysis
        input_num_chunks = cls._get_inputs_generation_chunks(analysis)
        # fetch number of event chunks
        loss_num_chunks = cls._get_loss_generation_chunks(analysis)

        input_run_data_uuid = uuid.uuid4().hex
        loss_run_data_uuid = uuid.uuid4().hex

        input_statuses, input_tasks = cls.get_inputs_generation_tasks(
            analysis, initiator, input_run_data_uuid, input_num_chunks, 'RUN_STARTED')
        loss_statuses, loss_tasks = cls.get_loss_generation_tasks(
            analysis, initiator, loss_run_data_uuid, loss_num_chunks)

        statuses = input_statuses + loss_statuses
        tasks = input_tasks + loss_tasks

        # Add chunk info to analysis
        analysis.lookup_chunks = input_num_chunks + loss_num_chunks
        analysis.sub_task_count = len(tasks)
        analysis.save()

        from src.server.oasisapi.analyses.models import AnalysisTaskStatus
        analysis.sub_task_statuses.all().delete()
        AnalysisTaskStatus.objects.create_statuses(iterchain(*statuses))

        input_chain = cls._create_chain(
            analysis,
            initiator,
            input_tasks,
            input_run_data_uuid,
            'input_generation_traceback_file',
            Analysis.status_choices.INPUTS_GENERATION_ERROR)
        loss_chain = cls._create_chain(
            analysis,
            initiator,
            loss_tasks,
            loss_run_data_uuid,
            'run_traceback_file',
            Analysis.status_choices.RUN_ERROR)

        # task = input_chain.delay({}, priority=analysis.priority, link=[loss_chain])
        # task = chain(input_chain, loss_chain).apply_async(priority=analysis.priority)
        task = chain(input_chain, loss_chain).delay({}, priority=analysis.priority, ignore_result=True)
        # task = input_chain.link(loss_chain).delay({}, priority=analysis.priority)
        # NO
        # task = input_chain.apply_async(link=[loss_chain()])
        # task = input_chain.apply_async(args={}, kwargs={}, priority=analysis.pk) #, link=[loss_chain])

        analysis.generate_inputs_task_id = task.id
        analysis.run_task_id = task.id
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
        fallback='src.server.oasisapi.analyses.v2_api.task_controller.Controller'
    )

    controller_module, controller_class = controller_path.rsplit('.', maxsplit=1)
    return getattr(
        import_module(controller_module),
        controller_class
    )

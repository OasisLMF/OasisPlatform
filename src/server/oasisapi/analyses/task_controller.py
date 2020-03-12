import os
from itertools import chain as iterchain
from importlib import import_module
from math import ceil
from typing import List, Type, TYPE_CHECKING, Tuple, Optional

from celery import signature, chord
from celery.canvas import Signature, chain
from django.contrib.auth.models import User
from oasislmf.utils.data import get_dataframe

from src.conf.iniconf import settings

if TYPE_CHECKING:
    from src.server.oasisapi.analyses.models import Analysis, AnalysisTaskStatus


class TaskParams:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class Controller:
    INPUT_GENERATION_CHUNK_SIZE = settings.get('worker', 'INPUT_GENERATION_CHUNK_SIZE', fallback=1)

    @classmethod
    def get_subtask_signature(cls, task_name, analysis, initiator, slug, queue, params: TaskParams) -> Signature:
        from src.server.oasisapi.analyses.tasks import record_sub_task_success, record_sub_task_failure
        sig = signature(
            task_name,
            queue=queue,
            args=params.args,
            kwargs={'initiator_id': initiator.pk, 'analysis_id': analysis.pk, 'slug': slug, **params.kwargs},
        )

        # add task to set the status of the sub task status record on success
        sig.link(record_sub_task_success.s(analysis_id=analysis.pk, initiator_id=initiator.pk, task_slug=slug))
        # add task to set the status of the sub task status record on failure
        sig.link_error(record_sub_task_failure.s(analysis_id=analysis.pk, initiator_id=initiator.pk, task_slug=slug))

        return sig

    @classmethod
    def get_subtask_status(cls, analysis: 'Analysis', name: str, slug: str, queue_name: str) -> 'AnalysisTaskStatus':
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
        status_name,
        status_slug,
        queue,
        params: Optional[TaskParams] = None,
    ) -> Tuple[List['AnalysisTaskStatus'], Signature]:
        params = params or TaskParams()
        return (
            [cls.get_subtask_status(analysis, status_name, status_slug, queue)],
            cls.get_subtask_signature(task_name, analysis, initiator, status_slug, queue, params),
        )

    @classmethod
    def get_subchord_statuses_and_signature(
        cls,
        task_name,
        analysis,
        initiator,
        status_name,
        status_slug,
        queue,
        params: List[TaskParams],
        body: Tuple[List['AnalysisTaskStatus'], Signature],
    ) -> Tuple[List['AnalysisTaskStatus'], Signature]:
        statuses, tasks = zip(*[
            cls.get_subtask_statuses_and_signature(task_name, analysis, initiator, f'{status_name} {idx}', f'{status_slug}-{idx}', queue, params=p)
            for idx, p in enumerate(params)
        ])

        c = chord(tasks, body=body[1], queue=queue)
        c.link_error(signature('chord_error_callback'))

        return list(iterchain(*statuses, body[0])), c

    @classmethod
    def _split_tasks_and_statuses(cls, joined):
        return list(zip(*joined))

    @classmethod
    def _start(
        cls,
        analysis,
        initiator,
        tasks: List[Signature],
        statuses: List['AnalysisTaskStatus'],
        run_dir_patterns: List[str],
        traceback_property: str,
        failure_status: str,
    ):
        from src.server.oasisapi.analyses.models import AnalysisTaskStatus
        analysis.sub_task_statuses.all().delete()
        AnalysisTaskStatus.objects.create_statuses(iterchain(*statuses))

        c = chain(*tasks)
        c.link_error(signature(
            'handle_task_failure',
            kwargs={
                'analysis_id': analysis.pk,
                'initiator_id': initiator.pk,
                'run_dir_patterns': run_dir_patterns,
                'traceback_property': traceback_property,
                'failure_status': failure_status,
            },
        ))
        c.delay()
        return c.id

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
    def get_inputs_generation_tasks(cls, analysis: 'Analysis', initiator: User):
        media_root = settings.get('worker', 'MEDIA_ROOT')
        # Handle case where URL is returned from analysis.portfolio.location_file.get_link()
        location_data = get_dataframe(src_fp=os.path.join(media_root, analysis.portfolio.location_file.get_link()))

        num_chunks = ceil(len(location_data) / cls.INPUT_GENERATION_CHUNK_SIZE)

        queue = cls.get_generate_inputs_queue(analysis, initiator)

        return cls._split_tasks_and_statuses([
            cls.get_subtask_statuses_and_signature(
                'prepare_input_generation_params',
                analysis,
                initiator,
                'Prepare input generation params',
                'prepare-input-generation-params',
                queue,
                TaskParams(
                    loc_file=analysis.portfolio.location_file.get_link(),
                    acc_file=analysis.portfolio.accounts_file.get_link(),
                    info_file=analysis.portfolio.reinsurance_info_file.get_link(),
                    scope_file=analysis.portfolio.reinsurance_scope_file.get_link(),
                    settings_file=analysis.settings_file.get_link(),
                    complex_data_files=analysis.create_complex_model_data_file_dicts() or None,
                )
            ),
            cls.get_subtask_statuses_and_signature(
                'prepare_inputs_directory',
                analysis,
                initiator,
                'Prepare input directory',
                'prepare-input-directory',
                queue,
            ),
            cls.get_subchord_statuses_and_signature(
                'prepare_keys_file_chunk',
                analysis,
                initiator,
                'Prepare keys file',
                'prepare-keys-file',
                queue,
                [TaskParams(idx, num_chunks) for idx in range(num_chunks)],
                cls.get_subtask_statuses_and_signature(
                    'collect_keys',
                    analysis,
                    initiator,
                    'Collect keys',
                    'collect-keys',
                    queue,
                ),
            ),
            cls.get_subtask_statuses_and_signature(
                'write_input_files',
                analysis,
                initiator,
                'Write input files',
                'write-input-files',
                queue,
            ),
            cls.get_subtask_statuses_and_signature(
                'record_input_files',
                analysis,
                initiator,
                'Record input files',
                'record-input-files',
                'celery',
            ),
            cls.get_subtask_statuses_and_signature(
                'cleanup_input_generation',
                analysis,
                initiator,
                'Cleanup input generation',
                'cleanup-input-generation',
                queue,
            ),
        ])

    @classmethod
    def generate_inputs(cls, analysis: 'Analysis', initiator: User):
        from src.server.oasisapi.analyses.models import Analysis
        statuses, tasks = cls.get_inputs_generation_tasks(analysis, initiator)

        task = analysis.generate_inputs_task_id = cls._start(
            analysis,
            initiator,
            tasks,
            statuses,
            [
                f'input-generation-oasis-files-dir-{analysis.pk}-*',
                f'input-generation-input-data-dir-{analysis.pk}-*',
            ],
            'input_generation_traceback_file',
            Analysis.status_choices.INPUTS_GENERATION_ERROR,
        )
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
    def get_loss_generation_tasks(cls, analysis: 'Analysis', initiator: User):
        media_root = settings.get('worker', 'MEDIA_ROOT')
        # Handle case where URL is returned from analysis.portfolio.location_file.get_link()
        location_data = get_dataframe(src_fp=os.path.join(media_root, analysis.portfolio.location_file.get_link()))

        num_chunks = ceil(len(location_data) / cls.INPUT_GENERATION_CHUNK_SIZE)

        queue = cls.get_generate_losses_queue(analysis, initiator)

        return cls._split_tasks_and_statuses([
            cls.get_subtask_statuses_and_signature(
                'extract_losses_generation_inputs',
                analysis,
                initiator,
                'Extract losses generation inputs',
                'extract-losses-generation-inputs',
                queue,
                TaskParams(
                    inputs_location=analysis.input_file.file.name,
                    complex_data_files=analysis.create_complex_model_data_file_dicts(),
                )
            ),
            cls.get_subtask_statuses_and_signature(
                'prepare_losses_generation_params',
                analysis,
                initiator,
                'Prepare losses generation params',
                'prepare-losses-generation-params',
                queue,
                TaskParams(
                    analysis_settings_file=analysis.settings_file.file.name if analysis.settings_file else None,
                    num_chunks=num_chunks,
                )
            ),
            cls.get_subtask_statuses_and_signature(
                'prepare_losses_generation_directory',
                analysis,
                initiator,
                'Prepare losses generation directory',
                'prepare-losses-generation-directory',
                queue,
            ),
            cls.get_subchord_statuses_and_signature(
                'generate_losses_chunk',
                analysis,
                initiator,
                'Generate losses chunk',
                'generate-losses-chunk',
                queue,
                [TaskParams(idx, num_chunks) for idx in range(num_chunks)],
                cls.get_subtask_statuses_and_signature(
                    'generate_losses_output',
                    analysis,
                    initiator,
                    'Generate losses output',
                    'generate_losses_output',
                    queue,
                ),
            ),
            cls.get_subtask_statuses_and_signature(
                'record_losses_files',
                analysis,
                initiator,
                'Record losses files',
                'record-losses-files',
                'celery',
            ),
            cls.get_subtask_statuses_and_signature(
                'cleanup_losses_generation',
                analysis,
                initiator,
                'Cleanup losses generation',
                'cleanup-losses-generation',
                queue,
            ),
        ])

    @classmethod
    def generate_losses(cls, analysis: 'Analysis', initiator: User):
        from src.server.oasisapi.analyses.models import Analysis
        statuses, tasks = cls.get_loss_generation_tasks(analysis, initiator)

        task = analysis.run_task_id = cls._start(
            analysis,
            initiator,
            tasks,
            statuses,
            [
                f'loss-generation-oasis-files-dir-{analysis.pk}-*',
                f'loss-generation-input-data-dir-{analysis.pk}-*',
            ],
            'run_traceback_file',
            Analysis.status_choices.RUN_ERROR,
        )
        analysis.save()
        return task


def get_analysis_task_controller() -> Type[Controller]:
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

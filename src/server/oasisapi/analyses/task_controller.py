import json
import os
from itertools import chain as iterchain
from collections import Iterable
from importlib import import_module
from math import ceil
from typing import List, Union, Type, TYPE_CHECKING, Tuple, Optional

from celery import signature, chord
from celery.canvas import Signature, chain
from django.contrib.auth.models import User
from django.utils.timezone import now
from oasislmf.utils.data import get_dataframe

from src.common.data import STORED_FILENAME, ORIGINAL_FILENAME
from src.conf.iniconf import settings

if TYPE_CHECKING:
    from src.server.oasisapi.analyses import Analysis, AnalysisTaskStatus


class TaskParams:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class BaseController:
    GENERATE_INPUTS_TASK_NAME = 'generate_input'
    GENERATE_LOSSES_TASK_NAME = 'run_analysis'

    @classmethod
    def get_chord_error_callback(cls):
        return signature('chord_error_callback')

    @classmethod
    def _start(
        cls,
        analysis: 'Analysis',
        initiator: 'User',
        queue: str,
        task_name: str,
        params: Union[List[TaskParams], TaskParams],
        success_callback: Signature,
        error_callback: Signature,
    ):
        """
        Generates and queues the task/chord and returns all the
        tasks generated.

        :param analysis: The analysis to start the task for
        :param queue: The name of the queue to add the tasks to
        :param task_name: The name of the task to create
        :param params: The parameters to send to the task
        :param success_callback: The task to queue once all tasks have completed
        :param error_callback: The task to queue if any of the tasks have failed
        """
        from src.server.oasisapi.analysis_models.models import QueueModelAssociation

        _now = now()

        # create the queue association so that the model can be posted to the websocket
        QueueModelAssociation.objects.get_or_create(model=analysis.model, queue_name=queue)

        if not isinstance(params, Iterable):
            sig = cls.get_subtask_signature(task_name, analysis, initiator, '', queue, params)

            # add task to record the results on success
            sig.link(success_callback)

            # add task to record the results on failure
            sig.link_error(error_callback)

            sig.delay()
        else:
            # if there is a list of param objects start a chord
            signatures = [
                cls.get_subtask_signature(task_name, analysis, initiator, '', queue, p)
                for p in params
            ]

            success_callback.link_error(error_callback)
            success_callback.link_error(cls.get_chord_error_callback())
            c = chord(signatures, body=success_callback)
            c.delay()

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

    #
    # Generate inputs
    #

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
    def get_generate_inputs_task_name(cls, analysis: 'Analysis', initiator: User) -> str:
        """
        Gets the name of the task to call to generate input data for an analysis

        :param analysis: The analysis to generate input data for
        :param initiator: The user who initiated the task

        :return: The name of the task
        """
        return cls.GENERATE_INPUTS_TASK_NAME

    @classmethod
    def get_generate_inputs_tasks_params(cls, analysis: 'Analysis', initiator: User) -> Union[List[TaskParams], TaskParams]:
        """
        Gets a list of args to pass to the input generation task. This should return
        a list of `TaskParams` or a `TaskParams` object containing the positional and keyword
        arguments for the task(s).

        If a list is returned each entry in the list will instantiate a task in a chord which
        will be collated.

        :param analysis: The analysis to generate input data for
        :param initiator: The user who initiated the task

        :return: The name of the queue
        """
        loc_file = analysis.portfolio.location_file.file.name
        acc_file = analysis.portfolio.accounts_file.file.name if analysis.portfolio.accounts_file else None
        info_file = analysis.portfolio.reinsurance_info_file.file.name if analysis.portfolio.reinsurance_info_file else None
        scope_file = analysis.portfolio.reinsurance_scope_file.file.name if analysis.portfolio.reinsurance_scope_file else None
        settings_file = analysis.settings_file.file.name if analysis.settings_file else None
        complex_data_files = analysis.create_complex_model_data_file_dicts()

        return TaskParams(
            loc_file=loc_file,
            acc_file=acc_file,
            info_file=info_file,
            scope_file=scope_file,
            settings_file=settings_file,
            complex_data_files=complex_data_files,
        )

    @classmethod
    def generate_inputs(cls, analysis: 'Analysis', initiator: User):
        """
        Sends the input generation tasks to the model worker.

        :param analysis: The analysis to generate input data for
        :param initiator: The user who initiated the task
        """
        from src.server.oasisapi.analyses.models import AnalysisTaskStatus

        queue = cls.get_generate_inputs_queue(analysis, initiator)
        params = cls.get_generate_inputs_tasks_params(analysis, initiator)

        # delete all statuses so that new ones can me created
        analysis.sub_task_statuses.all().delete()
        AnalysisTaskStatus.objects.create_statuses(
            AnalysisTaskStatus(
                analysis=analysis,
                slug=f'input-generation-{idx}',
                name=f'Input Generation {idx}',
            )
            for idx, p in enumerate(params if isinstance(params, Iterable) else [params])
        )

        cls._start(
            analysis,
            initiator,
            queue,
            cls.get_generate_inputs_task_name(analysis, initiator),
            params,
            cls.get_generate_inputs_results_callback(analysis, initiator),
            cls.get_generate_inputs_error_callback(analysis, initiator),
        )

    @classmethod
    def get_generate_inputs_results_callback(cls, analysis: 'Analysis', initiator: User):
        """
        Generates a signature for recording the generated inputs against the analysis.
        This should be linked to the input generation task.

        :param analysis: The analysis to generate input data for
        :param initiator: The user who initiated the task

        :return: The signature for the input recording task.
        """
        return signature(
            'generate_input_success',
            args=(analysis.pk, initiator.pk),
        )

    @classmethod
    def get_generate_inputs_error_callback(cls, analysis: 'Analysis', initiator: User):
        """
        Generates a signature for recording errors in the input generation process.
        This should be linked as the error callback to the input generation task.

        :param analysis: The analysis to generate input data for
        :param initiator: The user who initiated the task

        :return: The signature for the error recording task.
        """
        return signature(
            'record_generate_inputs_failure',
            args=(analysis.pk, initiator.pk),
        )

    #
    # loss generation
    #

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
    def get_generate_losses_task_name(cls, analysis: 'Analysis', initiator: User) -> str:
        """
        Gets the name of the task to call to generate loss data for an analysis

        :param analysis: The analysis to generate loss data for
        :param initiator: The user who initiated the task

        :return: The name of the task
        """
        return cls.GENERATE_LOSSES_TASK_NAME

    @classmethod
    def get_generate_losses_tasks_params(cls, analysis: 'Analysis', initiator: User) -> Union[List[TaskParams], TaskParams]:
        """
        Gets a list of args to pass to the loss generation task. This should return
        a list of `TaskParams` or a `TaskParams` object containing the positional and keyword
        arguments for the task(s).

        If a list is returned each entry in the list will instantiate a task in a chord which
        will be collated.

        :param analysis: The analysis to generate input data for
        :param initiator: The user who initiated the task

        :return: The name of the queue
        """
        complex_data_files = [
            {STORED_FILENAME: f.get_filestore(), ORIGINAL_FILENAME: f.get_filename()}
            for f in analysis.complex_model_data_files.all()
        ]

        return TaskParams(
            input_location=analysis.input_file.file.name,
            analysis_settings_file=analysis.settings_file.file.name,
            complex_data_files=complex_data_files or None
        )

    @classmethod
    def generate_losses(cls, analysis: 'Analysis', initiator: User):
        """
        Sends the loss generation tasks to the model worker.

        :param analysis: The analysis to generate input data for
        :param initiator: The user who initiated the task
        """
        cls._start(
            analysis,
            initiator,
            cls.get_generate_losses_queue(analysis, initiator),
            cls.get_generate_losses_task_name(analysis, initiator),
            cls.get_generate_losses_tasks_params(analysis, initiator),
            cls.get_generate_losses_results_callback(analysis, initiator),
            cls.get_generate_losses_error_callback(analysis, initiator),
        )

    @classmethod
    def get_generate_losses_results_callback(cls, analysis: 'Analysis', initiator: User) -> Signature:
        """
        Generates a signature for recording the generated losses against the analysis.
        This should be linked to the losses generation task.

        :param analysis: The analysis to generate input data for
        :param initiator: The user who initiated the task

        :return: The signature for the losses recording task.
        """
        return signature(
            'record_run_analysis_result',
            args=(analysis.pk, initiator.pk),
        )

    @classmethod
    def get_generate_losses_error_callback(cls, analysis: 'Analysis', initiator: User) -> Signature:
        """
        Generates a signature for recording errors in the losses generation process.
        This should be linked as the error callback to the losses generation task.

        :param analysis: The analysis to generate input data for
        :param initiator: The user who initiated the task

        :return: The signature for the error recording task.
        """
        return signature(
            'record_run_analysis_failure',
            args=(analysis.pk, initiator.pk),
        )


class ChunkedController(BaseController):
    INPUT_GENERATION_CHUNK_SIZE = settings.get('worker', 'INPUT_GENERATION_CHUNK_SIZE', fallback=1)

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
        body: Tuple['AnalysisTaskStatus', Signature],
    ) -> Tuple[List['AnalysisTaskStatus'], Signature]:
        statuses, tasks = zip(*[
            cls.get_subtask_statuses_and_signature(task_name, analysis, initiator, f'{status_name} {idx}', f'{status_slug}-{idx}', queue, params=p)
            for idx, p in enumerate(params)
        ])

        return (
            list(iterchain(*statuses, body[0])),
            chord(tasks, body=body[1], queue=queue)
        )

    @classmethod
    def generate_inputs(cls, analysis: 'Analysis', initiator: User):
        from src.server.oasisapi.analyses.models import AnalysisTaskStatus

        media_root = settings.get('worker', 'MEDIA_ROOT')
        location_data = get_dataframe(src_fp=os.path.join(media_root, analysis.portfolio.location_file.file.name))

        num_chunks = ceil(len(location_data) / cls.INPUT_GENERATION_CHUNK_SIZE)

        queue = cls.get_generate_inputs_queue(analysis, initiator)

        statuses_and_tasks = [
            cls.get_subtask_statuses_and_signature(
                'prepare_input_generation_params',
                analysis,
                initiator,
                'Prepare input generation params',
                'prepare-input-generation-params',
                queue,
                TaskParams(
                    loc_file=analysis.portfolio.location_file.file.name,
                    acc_file=analysis.portfolio.accounts_file.file.name if analysis.portfolio.accounts_file else None,
                    info_file=analysis.portfolio.reinsurance_info_file.file.name if analysis.portfolio.reinsurance_info_file else None,
                    scope_file=analysis.portfolio.reinsurance_scope_file.file.name if analysis.portfolio.reinsurance_scope_file else None,
                    settings_file=analysis.settings_file.file.name if analysis.settings_file else None,
                    complex_data_files=analysis.create_complex_model_data_file_dicts(),
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
        ]

        # setup each of the task status objects for each subtask
        statuses, tasks = list(zip(*statuses_and_tasks))

        analysis.sub_task_statuses.all().delete()
        AnalysisTaskStatus.objects.create_statuses(iterchain(*statuses))

        c = chain(*tasks)
        c.link_error(signature('cleanup_input_generation_on_error', args=(analysis.pk, )))

        analysis.generate_inputs_task_id = c.delay().id
        analysis.save()

    @classmethod
    def generate_losses(cls, analysis: 'Analysis', initiator: User):
        from src.server.oasisapi.analyses.models import AnalysisTaskStatus

        num_chunks = 4

        queue = cls.get_generate_inputs_queue(analysis, initiator)

        statuses_and_tasks = [
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
        ]

        # setup each of the task status objects for each subtask
        statuses, tasks = list(zip(*statuses_and_tasks))

        analysis.sub_task_statuses.all().delete()
        AnalysisTaskStatus.objects.create_statuses(iterchain(*statuses))

        c = chain(*tasks)
        c.link_error(signature('cleanup_loss_generation_on_error', args=(analysis.pk, )))

        analysis.generate_losses_task_id = c.delay().id
        analysis.save()


def get_analysis_task_controller() -> Type[BaseController]:
    controller_path = settings.get(
        'worker',
        'ANALYSIS_TASK_CONTROLLER',
        fallback='src.server.oasisapi.analyses.task_controller.BaseController'
    )

    controller_module, controller_class = controller_path.rsplit('.', maxsplit=1)
    return getattr(
        import_module(controller_module),
        controller_class
    )

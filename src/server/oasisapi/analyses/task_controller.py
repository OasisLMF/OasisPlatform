from collections import Iterable
from typing import List, Tuple, Dict, Union, Type
from importlib import import_module

from celery import signature, chord
from celery.canvas import Signature
from django.contrib.auth.models import User

from src.conf.iniconf import settings


class TaskParams:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class BaseController:
    GENERATE_INPUTS_TASK_NAME = 'generate_input'
    GENERATE_LOSSES_TASK_NAME = 'generate_losses'

    @classmethod
    def task_or_chord(
        cls,
        queue: str,
        task_name: str,
        params: Union[List[TaskParams], TaskParams],
        success_callback: Signature,
        error_callback: Signature,
    ):
        if not isinstance(params, Iterable):
            return signature(
                task_name,
                args=params.args,
                kwargs=params.kwargs,
                queue=queue,
            ).link(
                success_callback
            ).link_error(
                error_callback
            )
        else:
            # if there is a list of param objects start a chord
            chord(
                signature(
                    task_name,
                    args=p.args,
                    kwargs=p.kwargs,
                    queue=queue,
                ) for p in params
            ).link(
                success_callback
            ).link_error(
                error_callback
            ).delay()

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

        return TaskParams(analysis.pk, loc_file, acc_file, info_file, scope_file, settings_file, complex_data_files)

    @classmethod
    def generate_inputs(cls, analysis: 'Analysis', initiator: User):
        """
        Sends the input generation tasks to the model worker.

        :param analysis: The analysis to generate input data for
        :param initiator: The user who initiated the task
        """
        cls.task_or_chord(
            cls.get_generate_inputs_queue(analysis, initiator),
            cls.get_generate_inputs_task_name(analysis, initiator),
            cls.get_generate_inputs_tasks_params(analysis, initiator),
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
            'record_generate_inputs_results',
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
        return TaskParams(analysis.pk, initiator.pk)

    @classmethod
    def generate_losses(cls, analysis: 'Analysis', initiator: User):
        """
        Sends the loss generation tasks to the model worker.

        :param analysis: The analysis to generate input data for
        :param initiator: The user who initiated the task
        """
        cls.task_or_chord(
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
            'record_generate_losses_results',
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
            'record_generate_losses_failure',
            args=(analysis.pk, initiator.pk),
        )


def get_analysis_task_controller() -> Type[BaseController]:
    controller_path = settings().get(
        'worker',
        'ANALYSIS_TASK_CONTROLLER',
        fallback='src.server.oasisapi.analyses.task_controller.BaseController'
    )

    controller_module, controller_class = controller_path.rsplit('.', maxsplit=1)
    return getattr(
        import_module(controller_module),
        controller_class
    )

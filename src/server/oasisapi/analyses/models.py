from __future__ import absolute_import, print_function

from typing import List

from celery.result import AsyncResult

from src.server.oasisapi.celery import celery_app
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from model_utils.models import TimeStampedModel
from model_utils.choices import Choices
from rest_framework.exceptions import ValidationError
from rest_framework.reverse import reverse

from src.server.oasisapi.queues.consumers import send_task_status_message, TaskStatusMessageItem, TaskStatusMessageAnalysisItem
from ..files.models import RelatedFile
from ..analysis_models.models import AnalysisModel
from ..data_files.models import DataFile
from ..portfolios.models import Portfolio
from ..queues.utils import filter_queues_info
from ....common.data import STORED_FILENAME, ORIGINAL_FILENAME
from ....conf import iniconf


class AnalysisTaskStatusQuerySet(models.QuerySet):
    @classmethod
    def _send_socket_messages(cls, objects):
        queue_names = set(o.queue_name for o in objects)
        queues = filter_queues_info(queue_names)

        # build and send the
        status_message = [TaskStatusMessageItem(
            queue=q,
            analyses=[],
        ) for q in queues]

        for message_item in status_message:
            analyses = {}

            for status in filter(lambda s: s.queue_name == message_item.queue['name'], objects):
                analyses.setdefault(status.analysis, []).append(status)

            message_item.analyses.extend([TaskStatusMessageAnalysisItem(
                analysis=analysis,
                updated_tasks=statuses,
            ) for analysis, statuses in analyses.items()])

        send_task_status_message(status_message)

    def create_statuses(self, objs):
        """
        Creates all statuses initialising `queued_time`

        :param objs: A list of instances to create, they should all be for the same
            queue and analysis
        """
        statuses = self.bulk_create(objs)

        self._send_socket_messages(statuses)

    def update(self, **kwargs):
        res = super().update(**kwargs)

        self._send_socket_messages(self)

        return res


class AnalysisTaskStatus(models.Model):
    status_choices = Choices(
        ('PENDING', 'Task waiting to be added to the queue'),
        ('QUEUED', 'Task added to queue'),
        ('STARTED', 'Task started'),
        ('COMPLETED', 'Task completed'),
        ('CANCELLED', 'Task cancelled'),
        ('ERROR', 'Task error'),
    )

    queue_name = models.CharField(max_length=255, blank=False, editable=False)
    task_id = models.CharField(max_length=36, blank=True, default='', editable=False)
    analysis = models.ForeignKey('Analysis', related_name='sub_task_statuses', on_delete=models.CASCADE, editable=False)
    status = models.CharField(
        max_length=max(len(c) for c in status_choices._db_values),
        choices=status_choices,
        default=status_choices.PENDING,
        editable=False,
    )
    pending_time = models.DateTimeField(null=True, auto_now_add=True, editable=False)
    queue_time = models.DateTimeField(null=True, default=None, editable=False)
    start_time = models.DateTimeField(null=True, default=None, editable=False)
    end_time = models.DateTimeField(null=True, default=None, editable=False)
    name = models.CharField(max_length=255, editable=False)
    slug = models.SlugField(max_length=255, editable=False)

    output_log = models.ForeignKey(
        RelatedFile,
        on_delete=models.SET_NULL,
        blank=True, null=True,
        default=None,
        related_name='analysis_run_status_output_logs',
        editable=False,
    )
    error_log = models.ForeignKey(
        RelatedFile,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        default=None,
        related_name='analysis_run_status_error_logs',
        editable=False,
    )

    objects = AnalysisTaskStatusQuerySet.as_manager()

    class Meta:
        constraints = (
            models.UniqueConstraint(fields=['task_id'], condition=~models.Q(task_id=''), name='unique_task_id'),
        )
        unique_together = (
            ('analysis', 'slug',)
        )

    def get_output_log_url(self, request=None):
        return reverse('analysis-task-status-output-log', kwargs={'version': 'v1', 'pk': self.pk}, request=request)

    def get_error_log_url(self, request=None):
        return reverse('analysis-task-status-error-log', kwargs={'version': 'v1', 'pk': self.pk}, request=request)


class Analysis(TimeStampedModel):
    status_choices = Choices(
        ('NEW', 'New'),
        ('INPUTS_GENERATION_ERROR', 'Inputs generation error'),
        ('INPUTS_GENERATION_CANCELLED', 'Inputs generation cancelled'),
        ('INPUTS_GENERATION_STARTED', 'Inputs generation started'),
        ('INPUTS_GENERATION_QUEUED', 'Inputs generation added to queue'),
        ('READY', 'Ready'),
        ('RUN_QUEUED', 'Run added to queue'),
        ('RUN_STARTED', 'Run started'),
        ('RUN_COMPLETED', 'Run completed'),
        ('RUN_CANCELLED', 'Run cancelled'),
        ('RUN_ERROR', 'Run error'),
    )

    input_generation_traceback_file_id = None

    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='analyses')
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name='analyses', help_text=_('The portfolio to link the analysis to'))
    model = models.ForeignKey(AnalysisModel, on_delete=models.CASCADE, related_name='analyses', help_text=_('The model to link the analysis to'))
    name = models.CharField(help_text='The name of the analysis', max_length=255)
    status = models.CharField(max_length=max(len(c) for c in status_choices._db_values), choices=status_choices, default=status_choices.NEW, editable=False)
    task_started = models.DateTimeField(editable=False, null=True, default=None)
    task_finished = models.DateTimeField(editable=False, null=True, default=None)
    run_task_id = models.CharField(max_length=255, editable=False, default='', blank=True)
    generate_inputs_task_id = models.CharField(max_length=255, editable=False, default='', blank=True)
    complex_model_data_files = models.ManyToManyField(DataFile, blank=True, related_name='complex_model_files_analyses')

    settings_file = models.ForeignKey(RelatedFile, on_delete=models.CASCADE, blank=True, null=True, default=None, related_name='settings_file_analyses')
    input_file = models.ForeignKey(RelatedFile, on_delete=models.CASCADE, blank=True, null=True, default=None, related_name='input_file_analyses')
    input_generation_traceback_file = models.ForeignKey(RelatedFile, on_delete=models.SET_NULL, blank=True, null=True, default=None, related_name='input_generation_traceback_analyses')
    output_file = models.ForeignKey(RelatedFile, on_delete=models.CASCADE, blank=True, null=True, default=None, related_name='output_file_analyses')
    run_traceback_file = models.ForeignKey(RelatedFile, on_delete=models.SET_NULL, blank=True, null=True, default=None, related_name='run_traceback_file_analyses')
    run_log_file = models.ForeignKey(RelatedFile, on_delete=models.SET_NULL, blank=True, null=True, default=None, related_name='run_log_file_analyses')

    lookup_errors_file = models.ForeignKey(RelatedFile, on_delete=models.CASCADE, blank=True, null=True, default=None, related_name='lookup_errors_file_analyses')
    lookup_success_file = models.ForeignKey(RelatedFile, on_delete=models.CASCADE, blank=True, null=True, default=None, related_name='lookup_success_file_analyses')
    lookup_validation_file = models.ForeignKey(RelatedFile, on_delete=models.CASCADE, blank=True, null=True, default=None, related_name='lookup_validation_file_analyses')
    summary_levels_file = models.ForeignKey(RelatedFile, on_delete=models.CASCADE, blank=True, null=True, default=None, related_name='summary_levels_file_analyses')

    class Meta:
        verbose_name_plural = 'analyses'

    def __str__(self):
        return self.name

    def get_link(self, file_attribute):
        """
        returns the file link based on if file is connected
        if not then return 'None'

        """
        file_fields = [
            'settings_file',
            'input_file',
            'input_generation_traceback_file',
            'output_file',
            'run_traceback_file',
            'run_log_file',
            'lookup_errors_file',
            'lookup_success_file',
            'lookup_validation_file',
            'summary_levels_file',
        ]
        if file_attribute in file_fields:
            related_file = getattr(self, file_attribute)
            if related_file:
                return related_file.get_storage_reference()
        return None

    def get_absolute_url(self, request=None):
        return reverse('analysis-detail', kwargs={'version': 'v1', 'pk': self.pk}, request=request)

    def get_absolute_run_url(self, request=None):
        return reverse('analysis-run', kwargs={'version': 'v1', 'pk': self.pk}, request=request)

    def get_absolute_cancel_url(self, request=None):
        return reverse('analysis-cancel', kwargs={'version': 'v1', 'pk': self.pk}, request=request)

    def get_absolute_generate_inputs_url(self, request=None):
        return reverse('analysis-generate-inputs', kwargs={'version': 'v1', 'pk': self.pk}, request=request)

    def get_absolute_cancel_inputs_generation_url(self, request=None):
        return reverse('analysis-cancel-generate-inputs', kwargs={'version': 'v1', 'pk': self.pk}, request=request)

    def get_absolute_copy_url(self, request=None):
        return reverse('analysis-copy', kwargs={'version': 'v1', 'pk': self.pk}, request=request)

    def get_absolute_settings_file_url(self, request=None):
        return reverse('analysis-settings-file', kwargs={'version': 'v1', 'pk': self.pk}, request=request)

    def get_absolute_settings_url(self, request=None):
        return reverse('analysis-settings', kwargs={'version': 'v1', 'pk': self.pk}, request=request)

    def get_absolute_input_file_url(self, request=None):
        return reverse('analysis-input-file', kwargs={'version': 'v1', 'pk': self.pk}, request=request)

    def get_absolute_lookup_errors_file_url(self, request=None):
        return reverse('analysis-lookup-errors-file', kwargs={'version': 'v1', 'pk': self.pk}, request=request)

    def get_absolute_lookup_success_file_url(self, request=None):
        return reverse('analysis-lookup-success-file', kwargs={'version': 'v1', 'pk': self.pk}, request=request)

    def get_absolute_lookup_validation_file_url(self, request=None):
        return reverse('analysis-lookup-validation-file', kwargs={'version': 'v1', 'pk': self.pk}, request=request)

    def get_absolute_summary_levels_file_url(self, request=None):
        return reverse('analysis-summary-levels-file', kwargs={'version': 'v1', 'pk': self.pk}, request=request)

    def get_absolute_input_generation_traceback_file_url(self, request=None):
        return reverse('analysis-input-generation-traceback-file', kwargs={'version': 'v1', 'pk': self.pk}, request=request)

    def get_absolute_output_file_url(self, request=None):
        return reverse('analysis-output-file', kwargs={'version': 'v1', 'pk': self.pk}, request=request)

    def get_absolute_run_traceback_file_url(self, request=None):
        return reverse('analysis-run-traceback-file', kwargs={'version': 'v1', 'pk': self.pk}, request=request)

    def get_absolute_run_log_file_url(self, request=None):
        return reverse('analysis-run-log-file', kwargs={'version': 'v1', 'pk': self.pk}, request=request)


    def validate_run(self):
        valid_choices = [
            self.status_choices.READY,
            self.status_choices.RUN_COMPLETED,
            self.status_choices.RUN_ERROR,
            self.status_choices.RUN_CANCELLED,
        ]
        if self.status not in valid_choices:
            raise ValidationError(
                {'status': ['Analysis must be in one of the following states [{}]'.format(', '.join(valid_choices))]}
            )

        errors = {}
        if self.model.deleted:
            errors['model'] = ['Model pk "{}" has been deleted'.format(self.model.id)]

        if not self.settings_file:
            errors['settings_file'] = ['Must not be null']

        if not self.input_file:
            errors['input_file'] = ['Must not be null']

        if errors:
            self.status = self.status_choices.RUN_ERROR
            self.save()

            raise ValidationError(detail=errors)

    def run_callback(self, body):
        self.status = self.status_choices.RUN_STARTED
        self.save()

    @property
    def run_analysis_signature(self):
        return celery_app.signature(
            'start_loss_generation_task',
            options={'queue': iniconf.settings.get('worker', 'LOSSES_GENERATION_CONTROLLER_QUEUE', fallback='celery')}
        )

    def run(self, initiator):
        self.validate_run()

        self.status = self.status_choices.RUN_QUEUED

        task = self.run_analysis_signature
        task.on_error(celery_app.signature('handle_task_failure', kwargs={
            'analysis_id': self.pk,
            'initiator_id': initiator.pk,
            'traceback_property': 'run_traceback_file',
            'failure_status': Analysis.status_choices.RUN_ERROR,
        }))
        task_id = task.delay(self.pk, initiator.pk).id

        self.run_task_id = task_id
        self.task_started = timezone.now()
        self.task_finished = None
        self.save()

    def cancel(self):
        _now = timezone.now()

        # cleanup the the sub tasks
        qs = self.sub_task_statuses.filter(
            status__in=[AnalysisTaskStatus.status_choices.QUEUED, AnalysisTaskStatus.status_choices.STARTED]
        )

        for task_id in qs.values_list('task_id', flat=True):
            AsyncResult(task_id).revoke(signal='SIGKILL', terminate=True)

        qs.update(status=AnalysisTaskStatus.status_choices.CANCELLED, end_time=_now)

        # set the status on the analysis
        status_map = {
            Analysis.status_choices.INPUTS_GENERATION_STARTED: Analysis.status_choices.INPUTS_GENERATION_CANCELLED,
            Analysis.status_choices.INPUTS_GENERATION_QUEUED: Analysis.status_choices.INPUTS_GENERATION_CANCELLED,
            Analysis.status_choices.RUN_QUEUED: Analysis.status_choices.RUN_CANCELLED,
            Analysis.status_choices.RUN_STARTED: Analysis.status_choices.RUN_CANCELLED,
        }

        if self.status in status_map:
            self.status = status_map[self.status]
            self.task_finished = _now
            self.save()

    @property
    def generate_input_signature(self):
        return celery_app.signature(
            'start_input_generation_task',
            options={
                'queue': iniconf.settings.get('worker', 'INPUT_GENERATION_CONTROLLER_QUEUE', fallback='celery'),
            }
        )

    def generate_inputs(self, initiator):
        valid_choices = [
            self.status_choices.NEW,
            self.status_choices.INPUTS_GENERATION_ERROR,
            self.status_choices.INPUTS_GENERATION_CANCELLED,
            self.status_choices.READY,
            self.status_choices.RUN_COMPLETED,
            self.status_choices.RUN_CANCELLED,
            self.status_choices.RUN_ERROR,
        ]

        errors = {}
        if self.status not in valid_choices:
            errors['status'] = ['Analysis status must be one of [{}]'.format(', '.join(valid_choices))]

        if self.model.deleted:
            errors['model'] = ['Model pk "{}" has been deleted'.format(self.model.id)]

        if not self.portfolio.location_file:
            errors['portfolio'] = ['"location_file" must not be null']

        if errors:
            raise ValidationError(errors)

        self.status = self.status_choices.INPUTS_GENERATION_QUEUED
        self.lookup_errors_file = None
        self.lookup_success_file = None
        self.lookup_validation_file = None
        self.summary_levels_file = None
        self.input_generation_traceback_file_id = None

        task = self.generate_input_signature
        task.on_error(celery_app.signature('handle_task_failure', kwargs={
            'analysis_id': self.pk,
            'initiator_id': initiator.pk,
            'traceback_property': 'input_generation_traceback_file',
            'failure_status': Analysis.status_choices.INPUTS_GENERATION_ERROR,
        }))
        task_id = task.delay(self.pk, initiator.pk).id

        self.generate_inputs_task_id = task_id
        self.task_started = timezone.now()
        self.task_finished = None
        self.save()

    def create_complex_model_data_file_dicts(self):
        """Creates a list of tuples containing metadata for the complex model data files.

        Returns:
            list of dict: Dicts containing (stored filename, original filename) as the keys.

        """
        complex_data_files = [
            {
                STORED_FILENAME: cmdf.file.get_link(),
                ORIGINAL_FILENAME: cmdf.file.filename
            } for cmdf in self.complex_model_data_files.all()
        ]
        return complex_data_files

    def copy(self):
        new_instance = self
        new_instance.pk = None
        new_instance.name = '{} - Copy'.format(new_instance.name)
        new_instance.run_task_id = ''
        new_instance.generate_inputs_task_id = ''
        new_instance.status = self.status_choices.NEW
        new_instance.lookup_errors_file = None
        new_instance.lookup_success_file = None
        new_instance.lookup_validation_file = None
        new_instance.summary_levels_file = None
        new_instance.output_file = None
        return new_instance

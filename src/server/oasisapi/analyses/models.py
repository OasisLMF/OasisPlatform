from __future__ import absolute_import, print_function

from celery.result import AsyncResult
from copy import deepcopy
from django.conf import settings as django_settings
from django.core.files.base import File
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from model_utils.choices import Choices
from model_utils.models import TimeStampedModel
from rest_framework.exceptions import ValidationError
from rest_framework.reverse import reverse

from src.server.oasisapi.celery_app_v1 import v1 as celery_app_v1
from src.server.oasisapi.celery_app_v2 import v2 as celery_app_v2
from src.server.oasisapi.queues.consumers import send_task_status_message, TaskStatusMessageItem, \
    TaskStatusMessageAnalysisItem, build_task_status_message
from ..analysis_models.models import AnalysisModel, ModelChunkingOptions
from ..data_files.models import DataFile
from ..files.models import RelatedFile, file_storage_link
from ..portfolios.models import Portfolio
from ..queues.utils import filter_queues_info
from ....common.data import STORED_FILENAME, ORIGINAL_FILENAME
from ....conf import iniconf

from .v1_api.tasks import record_generate_input_result, record_run_analysis_result


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

        send_task_status_message(build_task_status_message(status_message))

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
        ordering = ['id']
        constraints = (
            models.UniqueConstraint(fields=['task_id'], condition=~models.Q(task_id=''), name='unique_task_id'),
        )
        unique_together = (
            ('analysis', 'slug',)
        )

    def get_output_log_url(self, request=None, namespace=None):
        override_ns = f'{namespace}:' if namespace else 'v2-analyses:'
        return reverse(f'{override_ns}analysis-task-status-output-log', kwargs={'pk': self.pk}, request=request)

    def get_error_log_url(self, request=None, namespace=None):
        override_ns = f'{namespace}:' if namespace else 'v2-analyses:'
        return reverse(f'{override_ns}analysis-task-status-error-log', kwargs={'pk': self.pk}, request=request)



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
    run_mode_choices = Choices(
        ('V1', 'Single-Instance Execution'),
        ('V2', 'Distributed Execution'),
    )

    input_generation_traceback_file_id = None

    creator = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='analyses')
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name='analyses', help_text=_('The portfolio to link the analysis to'))
    model = models.ForeignKey(AnalysisModel, on_delete=models.CASCADE, related_name='analyses', help_text=_('The model to link the analysis to'))
    name = models.CharField(help_text='The name of the analysis', max_length=255)
    status = models.CharField(max_length=max(len(c) for c in status_choices._db_values),
                              choices=status_choices, default=status_choices.NEW, editable=False)
    run_mode = models.CharField(max_length=max(len(c) for c in run_mode_choices._db_values),
                                choices=run_mode_choices, default=None, editable=False, null=True)
    task_started = models.DateTimeField(editable=False, null=True, default=None)

    task_finished = models.DateTimeField(editable=False, null=True, default=None)
    run_task_id = models.CharField(max_length=255, editable=False, default='', blank=True)
    generate_inputs_task_id = models.CharField(max_length=255, editable=False, default='', blank=True)
    complex_model_data_files = models.ManyToManyField(DataFile, blank=True, related_name='complex_model_files_analyses')

    settings_file = models.ForeignKey(RelatedFile, on_delete=models.CASCADE, blank=True, null=True,
                                      default=None, related_name='settings_file_analyses')
    input_file = models.ForeignKey(RelatedFile, on_delete=models.CASCADE, blank=True, null=True, default=None, related_name='input_file_analyses')
    input_generation_traceback_file = models.ForeignKey(RelatedFile, on_delete=models.SET_NULL,
                                                        blank=True, null=True, default=None, related_name='input_generation_traceback_analyses')
    output_file = models.ForeignKey(RelatedFile, on_delete=models.CASCADE, blank=True, null=True, default=None, related_name='output_file_analyses')
    run_traceback_file = models.ForeignKey(RelatedFile, on_delete=models.SET_NULL, blank=True, null=True,
                                           default=None, related_name='run_traceback_file_analyses')
    run_log_file = models.ForeignKey(RelatedFile, on_delete=models.SET_NULL, blank=True,
                                     null=True, default=None, related_name='run_log_file_analyses')

    analysis_chunks = models.IntegerField(editable=False, default=None, blank=True, null=True)
    lookup_chunks = models.IntegerField(editable=False, default=None, blank=True, null=True)
    priority = models.IntegerField(null=False, default=4, validators=[MinValueValidator(1), MaxValueValidator(
        10)], help_text='Priority of this analysis for input generation and execution. Set from 1 to 10 where 10 is the highest priority.')

    lookup_errors_file = models.ForeignKey(RelatedFile, on_delete=models.CASCADE, blank=True, null=True,
                                           default=None, related_name='lookup_errors_file_analyses')
    lookup_success_file = models.ForeignKey(RelatedFile, on_delete=models.CASCADE, blank=True, null=True,
                                            default=None, related_name='lookup_success_file_analyses')
    lookup_validation_file = models.ForeignKey(RelatedFile, on_delete=models.CASCADE, blank=True, null=True,
                                               default=None, related_name='lookup_validation_file_analyses')
    summary_levels_file = models.ForeignKey(RelatedFile, on_delete=models.CASCADE, blank=True, null=True,
                                            default=None, related_name='summary_levels_file_analyses')

    chunking_options = models.OneToOneField(ModelChunkingOptions, on_delete=models.CASCADE, auto_created=True, default=None, null=True)

    class Meta:
        ordering = ['id']
        verbose_name_plural = 'analyses'

    def __str__(self):
        return self.name

    def _update_ns(self, request=None):
        """ WORKAROUND - this is needed for when a copy request is issued
                         from the portfolio view '/{ver}/portfolios/{id}/create_analysis/'

                         The inncorrect namespace '{ver}-portfolios' is inherited from the
                         original request. This needs to be replaced with '{ver}-analyses'
        """
        if not request:
            return None
        ns_ver, ns_view = request.version.split('-')
        if ns_view != 'analyses':
            request.version = f'{ns_ver}-analyses'
        return request

    def get_absolute_url(self, request=None, namespace=None):
        override_ns = f'{namespace}:' if namespace else ''
        return reverse(f'{override_ns}analysis-detail', kwargs={'pk': self.pk}, request=self._update_ns(request))

    def get_absolute_run_url(self, request=None, namespace=None):
        override_ns = f'{namespace}:' if namespace else ''
        return reverse(f'{override_ns}analysis-run', kwargs={'pk': self.pk}, request=self._update_ns(request))

    def get_absolute_cancel_url(self, request=None, namespace=None):
        override_ns = f'{namespace}:' if namespace else ''
        return reverse(f'{override_ns}analysis-cancel', kwargs={'pk': self.pk}, request=self._update_ns(request))

    def get_absolute_cancel_analysis_url(self, request=None, namespace=None):
        override_ns = f'{namespace}:' if namespace else ''
        return reverse(f'{override_ns}analysis-cancel-analysis-run', kwargs={'pk': self.pk}, request=self._update_ns(request))

    def get_absolute_generate_inputs_url(self, request=None, namespace=None):
        override_ns = f'{namespace}:' if namespace else ''
        return reverse(f'{override_ns}analysis-generate-inputs', kwargs={'pk': self.pk}, request=self._update_ns(request))

    def get_absolute_cancel_inputs_generation_url(self, request=None, namespace=None):
        override_ns = f'{namespace}:' if namespace else ''
        return reverse(f'{override_ns}analysis-cancel-generate-inputs', kwargs={'pk': self.pk}, request=self._update_ns(request))

    def get_absolute_copy_url(self, request=None, namespace=None):
        override_ns = f'{namespace}:' if namespace else ''
        return reverse(f'{override_ns}analysis-copy', kwargs={'pk': self.pk}, request=self._update_ns(request))

    def get_absolute_settings_file_url(self, request=None, namespace=None):
        override_ns = f'{namespace}:' if namespace else ''
        return reverse(f'{override_ns}analysis-settings-file', kwargs={'pk': self.pk}, request=self._update_ns(request))

    def get_absolute_settings_url(self, request=None, namespace=None):
        override_ns = f'{namespace}:' if namespace else ''
        return reverse(f'{override_ns}analysis-settings', kwargs={'pk': self.pk}, request=self._update_ns(request))

    def get_absolute_input_file_url(self, request=None, namespace=None):
        override_ns = f'{namespace}:' if namespace else ''
        return reverse(f'{override_ns}analysis-input-file', kwargs={'pk': self.pk}, request=self._update_ns(request))

    def get_absolute_lookup_errors_file_url(self, request=None, namespace=None):
        override_ns = f'{namespace}:' if namespace else ''
        return reverse(f'{override_ns}analysis-lookup-errors-file', kwargs={'pk': self.pk}, request=self._update_ns(request))

    def get_absolute_lookup_success_file_url(self, request=None, namespace=None):
        override_ns = f'{namespace}:' if namespace else ''
        return reverse(f'{override_ns}analysis-lookup-success-file', kwargs={'pk': self.pk}, request=self._update_ns(request))

    def get_absolute_lookup_validation_file_url(self, request=None, namespace=None):
        override_ns = f'{namespace}:' if namespace else ''
        return reverse(f'{override_ns}analysis-lookup-validation-file', kwargs={'pk': self.pk}, request=self._update_ns(request))

    def get_absolute_summary_levels_file_url(self, request=None, namespace=None):
        override_ns = f'{namespace}:' if namespace else ''
        return reverse(f'{override_ns}analysis-summary-levels-file', kwargs={'pk': self.pk}, request=self._update_ns(request))

    def get_absolute_input_generation_traceback_file_url(self, request=None, namespace=None):
        override_ns = f'{namespace}:' if namespace else ''
        return reverse(f'{override_ns}analysis-input-generation-traceback-file', kwargs={'pk': self.pk}, request=self._update_ns(request))

    def get_absolute_output_file_url(self, request=None, namespace=None):
        override_ns = f'{namespace}:' if namespace else ''
        return reverse(f'{override_ns}analysis-output-file', kwargs={'pk': self.pk}, request=self._update_ns(request))

    def get_absolute_run_traceback_file_url(self, request=None, namespace=None):
        override_ns = f'{namespace}:' if namespace else ''
        return reverse(f'{override_ns}analysis-run-traceback-file', kwargs={'pk': self.pk}, request=self._update_ns(request))

    def get_absolute_run_log_file_url(self, request=None, namespace=None):
        override_ns = f'{namespace}:' if namespace else ''
        return reverse(f'{override_ns}analysis-run-log-file', kwargs={'pk': self.pk}, request=self._update_ns(request))

    def get_absolute_storage_url(self, request=None, namespace=None):
        override_ns = f'{namespace}:' if namespace else ''
        return reverse(f'{override_ns}analysis-storage-links', kwargs={'pk': self.pk}, request=self._update_ns(request))

    def get_absolute_subtask_list_url(self, request=None, namespace=None):
        override_ns = f'{namespace}:' if namespace else ''
        return reverse(f'{override_ns}analysis-sub-task-list', kwargs={'pk': self.pk}, request=self._update_ns(request))

    def get_absolute_chunking_configuration_url(self, request=None, namespace=None):
        override_ns = f'{namespace}:' if namespace else ''
        return reverse(f'{override_ns}analysis-chunking-configuration', kwargs={'pk': self.pk}, request=self._update_ns(request))

    def get_groups(self):
        groups = []
        portfolio_groups = self.portfolio.groups.all()
        for group in portfolio_groups:
            groups.append(group.name)
        return groups

    def get_num_events(self):
        selected_strat = self.model.chunking_options.loss_strategy
        dynamic_strat = self.model.chunking_options.chunking_types.DYNAMIC_CHUNKS
        if selected_strat != dynamic_strat:
            return 1

        analysis_settings = self.settings_file.read_json()
        model_settings = self.model.resource_file.read_json()
        user_selected_events = analysis_settings.get('event_ids', [])
        selected_event_set = analysis_settings.get('model_settings', {}).get('event_set', "")
        if len(user_selected_events) > 1:
            return len(user_selected_events)

        event_set_options = model_settings.get('model_settings', {}).get('event_set').get('options', [])
        event_set_sizes = {e['id']: e['number_of_events'] for e in event_set_options if 'number_of_events' in e}
        if selected_event_set not in event_set_sizes:
            raise ValidationError(
                f"Failed to read event set size for chunking: selected event_id: {selected_event_set}, options: {event_set_options}")
        return event_set_sizes.get(selected_event_set)

    # --- V1 task signatures ------------------------------------------------ #

    @property
    def v1_run_analysis_signature(self):
        complex_data_files = self.create_complex_model_data_file_dicts()
        input_file = file_storage_link(self.input_file)
        settings_file = file_storage_link(self.settings_file)

        return celery_app_v1.signature(
            'run_analysis',
            args=(self.pk, input_file, settings_file, complex_data_files),
            queue=self.model.queue_name,
        )

    @property
    def v1_generate_input_signature(self):
        loc_file = file_storage_link(self.portfolio.location_file)
        acc_file = file_storage_link(self.portfolio.accounts_file)
        info_file = file_storage_link(self.portfolio.reinsurance_info_file)
        scope_file = file_storage_link(self.portfolio.reinsurance_scope_file)
        settings_file = file_storage_link(self.settings_file)
        complex_data_files = self.create_complex_model_data_file_dicts()

        return celery_app_v1.signature(
            'generate_input',
            args=(self.pk, loc_file, acc_file, info_file, scope_file, settings_file, complex_data_files),
            queue=self.model.queue_name,
        )

    # --- V2 task signatures ------------------------------------------------ #

    @property
    def v2_run_analysis_signature(self):
        return celery_app_v2.signature(
            'start_loss_generation_task',
            options={'queue': iniconf.settings.get('worker', 'LOSSES_GENERATION_CONTROLLER_QUEUE', fallback='celery-v2')}
        )

    @property
    def v2_start_input_and_loss_generation_signature(self):
        return celery_app_v2.signature(
            'start_input_and_loss_generation_task',
            options={'queue': iniconf.settings.get('worker', 'INPUT_GENERATION_CONTROLLER_QUEUE', fallback='celery-v2')}
        )

    @property
    def v2_cancel_subtasks_signature(self):
        return celery_app_v2.signature(
            'cancel_subtasks',
            options={
                'queue': iniconf.settings.get('worker', 'INPUT_GENERATION_CONTROLLER_QUEUE', fallback='celery-v2')
            }
        )

    @property
    def v2_generate_input_signature(self):
        return celery_app_v2.signature(
            'start_input_generation_task',
            options={
                'queue': iniconf.settings.get('worker', 'INPUT_GENERATION_CONTROLLER_QUEUE', fallback='celery-v2')
            }
        )

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
            errors['analysis_settings_file'] = ['Must not be null']

        if not self.input_file:
            errors['input_file'] = ['Must not be null']

        # Valadation for dyanmic loss chunks
        if self.model.chunking_options.loss_strategy == self.model.chunking_options.chunking_types.DYNAMIC_CHUNKS:
            if not self.model.resource_file:
                errors['model_settings_file'] = ['Must not be null for Dynamic chunking']
            elif self.settings_file:
                # cross check model and analysis settings if not given a set of events
                model_settings = self.model.resource_file.read_json()
                analysis_settings = self.settings_file.read_json()
                if not analysis_settings.get('event_ids'):
                    events_selected = analysis_settings.get('model_settings', {}).get('event_set', "")
                    events_options = model_settings.get("model_settings", {}).get('event_set', {}).get('options', [])
                    events_matched = [opt for opt in events_options if opt.get('id') == events_selected]

                    if not events_selected:
                        errors['analysis_settings_file'] = ['event_set, Must not be null for Dynamic chunking']
                    if not events_options:
                        errors['model_settings_file'] = ['event_set, No options given in Model settings']
                    if not events_matched:
                        errors['settings_files'] = [f"selected event_set '{events_selected}' from analysis_settings not found in model_settings"]
                    elif not events_matched[0].get('number_of_events'):
                        errors['model_settings_file'] = [f"Option 'number_of_events' is not set for event_set = '{events_selected}'"]

        if errors:
            self.status = self.status_choices.RUN_ERROR
            self.save()
            raise ValidationError(detail=errors)

    def run_callback(self, body):
        self.status = self.status_choices.RUN_STARTED
        self.save()

    def run(self, initiator, version):
        self.validate_run()
        events_total = self.get_num_events()
        self.status = self.status_choices.RUN_QUEUED
        self.save()

        if version.startswith('v1'):
            task = self.v1_run_analysis_signature
            task.link(record_run_analysis_result.s(self.pk, initiator.pk))
            task.link_error(
                celery_app_v1.signature('on_error', args=('record_run_analysis_failure', self.pk, initiator.pk), queue=self.model.queue_name)
            )
            self.status = self.status_choices.RUN_QUEUED
            self.run_mode = self.run_mode_choices.V1
            task_id = task.delay().id

        elif version.startswith('v2'):  # V2 task dispatch
            task = self.v2_run_analysis_signature
            task.on_error(celery_app_v2.signature('handle_task_failure', kwargs={
                'analysis_id': self.pk,
                'initiator_id': initiator.pk,
                'traceback_property': 'run_traceback_file',
                'failure_status': Analysis.status_choices.RUN_ERROR,
            }, queue='celery-v2'))
            self.run_mode = self.run_mode_choices.V2
            task_id = task.apply_async(args=[self.pk, initiator.pk, events_total], priority=self.priority).id

        else:
            raise ValidationError(detail={'version':
                                          [f"Request version must be either 'v1' or 'v2', received: '{version}'"]
                                          })

        self.run_task_id = task_id
        self.task_started = timezone.now()
        self.task_finished = None
        self.save()

    def raise_validate_errors(self, errors, error_state=None):
        if error_state:
            self.status = error_state
            self.save()
        if errors:
            raise ValidationError(detail=errors)

    def generate_and_run(self, initiator, version):
        valid_choices = [
            self.status_choices.NEW,
            self.status_choices.INPUTS_GENERATION_ERROR,
            self.status_choices.INPUTS_GENERATION_CANCELLED,
            self.status_choices.READY,
            self.status_choices.RUN_COMPLETED,
            self.status_choices.RUN_CANCELLED,
            self.status_choices.RUN_ERROR,
        ]

        # validation
        errors = {}
        if self.status not in valid_choices:
            errors['status'] = ['Analysis status must be one of [{}]'.format(', '.join(valid_choices))]
        if self.model.deleted:
            errors['model'] = ['Model pk "{}" has been deleted'.format(self.model.id)]
        if not self.settings_file:
            errors['settings_file'] = ['Must not be null']
        if not self.portfolio.location_file:
            errors['portfolio'] = ['"location_file" must not be null']

        # Raise for error
        self.raise_validate_errors(errors)

        self.status = self.status_choices.INPUTS_GENERATION_QUEUED
        self.lookup_errors_file = None
        self.lookup_success_file = None
        self.lookup_validation_file = None
        self.summary_levels_file = None
        self.input_generation_traceback_file_id = None

        task = self.v2_start_input_and_loss_generation_signature
        task.on_error(celery_app_v2.signature('handle_task_failure', kwargs={
            'analysis_id': self.pk,
            'initiator_id': initiator.pk,
            'traceback_property': 'input_generation_traceback_file',
            'failure_status': Analysis.status_choices.INPUTS_GENERATION_ERROR,
        }))
        self.run_mode = self.run_mode_choices.V2
        task_id = task.apply_async(args=[self.pk, initiator.pk], priority=self.priority).id

        self.generate_inputs_task_id = task_id
        self.task_started = timezone.now()
        self.task_finished = None
        self.save()

    def cancel(self):
        _now = timezone.now()

        # cleanup the the sub tasks
        qs = self.sub_task_statuses.filter(
            status__in=[
                AnalysisTaskStatus.status_choices.PENDING,
                AnalysisTaskStatus.status_choices.QUEUED,
                AnalysisTaskStatus.status_choices.STARTED]
        )

        for task_id in qs.values_list('task_id', flat=True):
            if task_id:
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

    def generate_inputs(self, initiator, version):
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
        else:
            try:
                loc_lines = self.portfolio.location_file_len()
            except Exception as e:
                raise ValidationError(f"Failed to read location file size for chunking: {e}")
            if not isinstance(loc_lines, int):
                errors['portfolio'] = [
                    f'Failed to read "location_file" size, content_type={self.portfolio.location_file.content_type} might not be supported']

            else:
                if loc_lines < 1:
                    errors['portfolio'] = ['"location_file" must at least one row']
        if errors:
            raise ValidationError(errors)

        self.status = self.status_choices.INPUTS_GENERATION_QUEUED
        self.lookup_errors_file = None
        self.lookup_success_file = None
        self.lookup_validation_file = None
        self.summary_levels_file = None
        self.input_generation_traceback_file_id = None
        self.save()

        if version.startswith('v1'):
            task = self.v1_generate_input_signature
            task.link(record_generate_input_result.s(self.pk, initiator.pk))
            task.link_error(
                celery_app_v1.signature('on_error', args=('record_generate_input_failure', self.pk, initiator.pk), queue=self.model.queue_name)
            )
            self.run_mode = self.run_mode_choices.V1
            self.status = self.status_choices.INPUTS_GENERATION_QUEUED
            task_id = task.delay().id

        elif version.startswith('v2'):
            task = self.v2_generate_input_signature
            task.on_error(celery_app_v2.signature('handle_task_failure', kwargs={
                'analysis_id': self.pk,
                'initiator_id': initiator.pk,
                'traceback_property': 'input_generation_traceback_file',
                'failure_status': Analysis.status_choices.INPUTS_GENERATION_ERROR,
            }))
            self.run_mode = self.run_mode_choices.V2
            task_id = task.apply_async(args=[self.pk, initiator.pk, loc_lines], priority=self.priority).id
        else:
            raise ValidationError(detail={'version':
                                          [f"Request version must be either 'v1' or 'v2', received: '{version}'"]
                                          })

        self.generate_inputs_task_id = task_id
        self.task_started = timezone.now()
        self.task_finished = None
        self.save()

    def cancel_any(self):
        INPUTS_GENERATION_STATES = [
            self.status_choices.INPUTS_GENERATION_QUEUED,
            self.status_choices.INPUTS_GENERATION_STARTED
        ]
        RUN_ANALYSIS_STATES = [
            self.status_choices.RUN_QUEUED,
            self.status_choices.RUN_STARTED
        ]
        valid_choices = INPUTS_GENERATION_STATES + RUN_ANALYSIS_STATES
        if self.status not in valid_choices:
            raise ValidationError({'status': ['Analysis is not running or queued']})

        if self.status in INPUTS_GENERATION_STATES:
            self.cancel_generate_inputs()

        if self.status in RUN_ANALYSIS_STATES:
            self.cancel_analysis()

    def cancel_analysis(self):
        valid_choices = [
            self.status_choices.RUN_QUEUED,
            self.status_choices.RUN_STARTED
        ]
        if self.status not in valid_choices:
            raise ValidationError({'status': ['Analysis execution is not running or queued']})

        # Terminate V2 Execution
        if self.run_mode is self.run_mode_choices.V2:
            # Kill the task controller job incase its still on queue
            AsyncResult(self.run_task_id).revoke(
                signal='SIGKILL',
                terminate=True,
            )
            # Send Kill chain call to worker-controller
            cancel_tasks = self.v2_cancel_subtasks_signature
            task_id = cancel_tasks.apply_async(args=[self.pk], priority=10).id

        # Terminate V1 Execution -- assume this option if not set
        else:
            AsyncResult(self.run_task_id).revoke(
                signal='SIGTERM',
                terminate=True,
            )

        self.status = self.status_choices.RUN_CANCELLED
        self.run_mode = None
        self.task_finished = timezone.now()
        self.save()

    def cancel_generate_inputs(self):
        valid_choices = [
            self.status_choices.INPUTS_GENERATION_QUEUED,
            self.status_choices.INPUTS_GENERATION_STARTED
        ]
        if self.status not in valid_choices:
            raise ValidationError({'status': ['Analysis input generation is not running or queued']})

        # Terminate V2 Execution
        if self.run_mode is self.run_mode_choices.V2:
            # Kill the task controller job incase its still on queue
            AsyncResult(self.generate_inputs_task_id).revoke(
                signal='SIGKILL',
                terminate=True,
            )
            # Send Kill chain call to worker-controller
            cancel_tasks = self.v2_cancel_subtasks_signature
            task_id = cancel_tasks.apply_async(args=[self.pk], priority=10).id

        # Terminate V1 Execution -- assume this option if not set
        else:
            AsyncResult(self.generate_inputs_task_id).revoke(
                signal='SIGTERM',
                terminate=True,
            )

        self.status = self.status_choices.INPUTS_GENERATION_CANCELLED
        self.run_mode = None
        self.task_finished = timezone.now()
        self.save()

    def create_complex_model_data_file_dicts(self):
        """Creates a list of tuples containing metadata for the complex model data files.

        Returns:
            list of dict: Dicts containing (stored filename, original filename) as the keys.

        """
        complex_data_files = [
            {
                STORED_FILENAME: file_storage_link(cmdf.file),
                ORIGINAL_FILENAME: cmdf.file.filename
            } for cmdf in self.complex_model_data_files.all()
        ]
        return complex_data_files

    def copy_file(self, obj):
        """ Duplicate a conneced DB object and
        store under a new ID
        """
        if obj is None:
            return None
        return RelatedFile.objects.create(
            file=File(obj.file),
            filename=obj.filename,
            content_type=obj.content_type,
            creator=obj.creator,
        )

    def copy(self):
        new_instance = self
        new_instance.pk = None
        new_instance.name = '{} - Copy'.format(new_instance.name)
        new_instance.run_task_id = ''
        new_instance.generate_inputs_task_id = ''
        new_instance.status = self.status_choices.NEW
        new_instance.settings_file = self.copy_file(new_instance.settings_file)

        new_instance.input_file = None
        new_instance.input_generation_traceback_file = None
        new_instance.output_file = None
        new_instance.run_traceback_file = None
        new_instance.run_log_file = None

        new_instance.lookup_errors_file = None
        new_instance.lookup_success_file = None
        new_instance.lookup_validation_file = None
        new_instance.summary_levels_file = None
        return new_instance


# Not needed, check for both in the controller
#@receiver(post_save, sender=Analysis)
#def create_default_scaling_options(sender, instance, **kwargs):
#    """ Copy the chunking options set in attached model on creation
#    """
#    if instance.chunking_options == None:
#        default_chunking = deepcopy(instance.model.chunking_options)
#        default_chunking.pk = None
#        default_chunking.save()
#        instance.chunking_options = default_chunking
#        instance.save()


@receiver(post_delete, sender=Analysis)
def delete_connected_files(sender, instance, **kwargs):
    """ Post delete handler to clear out any dangaling analyses files
    """
    for_removal = [
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
        'chunking_options',
    ]
    for ref in for_removal:
        obj_ref = getattr(instance, ref)
        if obj_ref:
            obj_ref.delete()

@receiver(post_delete, sender=AnalysisTaskStatus)
def delete_connected_task_logs(sender, instance, **kwargs):
    """ Post delete handler to clear out any dangaling log files
    """
    for_removal = [
        'output_log',
        'error_log',
    ]
    for ref in for_removal:
        obj_ref = getattr(instance, ref)
        if obj_ref:
            obj_ref.delete()

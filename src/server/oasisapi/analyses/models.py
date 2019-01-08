from __future__ import absolute_import, print_function

from celery import signature
from celery.result import AsyncResult
from django.conf import settings
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel
from model_utils.choices import Choices
from rest_framework.exceptions import ValidationError
from rest_framework.reverse import reverse

from ..files.models import RelatedFile
from ..analysis_models.models import AnalysisModel
from ..portfolios.models import Portfolio
from .tasks import generate_input_success, run_analysis_success


@python_2_unicode_compatible
class Analysis(TimeStampedModel):
    status_choices = Choices(
        ('NEW', 'New'),
        ('INPUTS_GENERATION_ERROR', 'Inputs generation error'),
        ('INPUTS_GENERATION_CANCELLED', 'Inputs generation cancelled'),
        ('INPUTS_GENERATION_STARTED', 'Inputs generation started'),
        ('READY', 'Ready'),
        ('RUN_STARTED', 'Run started'),
        ('RUN_COMPLETED', 'Run completed'),
        ('RUN_CANCELLED', 'Run cancelled'),
        ('RUN_ERROR', 'Run error'),
    )

    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='analyses')
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name='analyses', help_text=_('The portfolio to link the analysis to'))
    model = models.ForeignKey(AnalysisModel, on_delete=models.DO_NOTHING, related_name='analyses', help_text=_('The model to link the analysis to'))
    name = models.CharField(help_text='The name of the analysis', max_length=255)
    status = models.CharField(max_length=max(len(c) for c in status_choices._db_values), choices=status_choices, default=status_choices.NEW, editable=False)
    run_task_id = models.CharField(max_length=255, editable=False, default='', blank=True)
    generate_inputs_task_id = models.CharField(max_length=255, editable=False, default='', blank=True)

    settings_file = models.ForeignKey(RelatedFile, blank=True, null=True, default=None, related_name='settings_file_analyses')
    input_file = models.ForeignKey(RelatedFile, blank=True, null=True, default=None, related_name='input_file_analyses')
    input_errors_file = models.ForeignKey(RelatedFile, blank=True, null=True, default=None, related_name='input_errors_file_analyses')
    input_generation_traceback_file = models.ForeignKey(RelatedFile, blank=True, null=True, default=None, related_name='input_generation_traceback_analyses')
    output_file = models.ForeignKey(RelatedFile, blank=True, null=True, default=None, related_name='output_file_analyses')
    run_traceback_file = models.ForeignKey(RelatedFile, blank=True, null=True, default=None, related_name='run_traceback_file_analyses')

    class Meta:
        verbose_name_plural = 'analyses'

    def __str__(self):
        return self.name

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

    def get_absolute_input_file_url(self, request=None):
        return reverse('analysis-input-file', kwargs={'version': 'v1', 'pk': self.pk}, request=request)

    def get_absolute_input_errors_file_url(self, request=None):
        return reverse('analysis-input-errors-file', kwargs={'version': 'v1', 'pk': self.pk}, request=request)

    def get_absolute_input_generation_traceback_file_url(self, request=None):
        return reverse('analysis-input-generation-traceback-file', kwargs={'version': 'v1', 'pk': self.pk}, request=request)

    def get_absolute_output_file_url(self, request=None):
        return reverse('analysis-output-file', kwargs={'version': 'v1', 'pk': self.pk}, request=request)

    def get_absolute_run_traceback_file_url(self, request=None):
        return reverse('analysis-run-traceback-file', kwargs={'version': 'v1', 'pk': self.pk}, request=request)

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
        if not self.settings_file:
            errors['settings_file'] = ['Must not be null']

        if not self.input_file:
            errors['input_file'] = ['Must not be null']

        if errors:
            self.status = self.status_choices.RUN_ERROR
            self.save()

            raise ValidationError(detail=errors)

    def run(self, initiator):
        self.validate_run()

        self.status = self.status_choices.RUN_STARTED
        self.input_generation_traceback_file_id = None

        run_analysis_signature = self.run_analysis_signature
        run_analysis_signature.link(run_analysis_success.s(self.pk, initiator.pk))
        run_analysis_signature.link_error(
            signature('on_error', args=('record_run_analysis_failure', self.pk, initiator.pk), queue=self.model.queue_name)
        )
        self.run_task_id = run_analysis_signature.delay().id

        self.save()

    @property
    def run_analysis_signature(self):
        return signature(
            'run_analysis',
            args=(self.input_file.file.name, self.settings_file.file.name),
            queue=self.model.queue_name,
        )

    def cancel(self):
        if self.status != self.status_choices.RUN_STARTED:
            raise ValidationError({'status': ['Analysis is not running']})

        AsyncResult(self.run_task_id).revoke(
            signal='SIGKILL',
            terminate=True,
        )

        self.status = self.status_choices.RUN_CANCELLED
        self.save()

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

        if not self.portfolio.location_file:
            errors['portfolio'] = ['"location_file" must not be null']

        if errors:
            raise ValidationError(errors)

        self.status = self.status_choices.INPUTS_GENERATION_STARTED
        self.input_errors_file = None
        self.input_generation_traceback_file_id = None

        generate_input_signature = self.generate_input_signature
        generate_input_signature.link(generate_input_success.s(self.pk, initiator.pk))
        generate_input_signature.link_error(
            signature('on_error', args=('record_generate_input_failure', self.pk, initiator.pk), queue=self.model.queue_name)
        )
        self.generate_inputs_task_id = generate_input_signature.delay().id

        self.save()

    def cancel_generate_inputs(self):
        if self.status != self.status_choices.INPUTS_GENERATION_STARTED:
            raise ValidationError({'status': ['Analysis input generation is not running']})

        self.status = self.status_choices.INPUTS_GENERATION_CANCELLED
        AsyncResult(self.generate_inputs_task_id).revoke(
            signal='SIGKILL',
            terminate=True,
        )

        self.save()

    @property
    def generate_input_signature(self):
        return signature(
            'generate_input', args=(self.portfolio.location_file.file.name, ), queue=self.model.queue_name,
        )

    def copy(self):
        new_instance = self
        new_instance.pk = None
        new_instance.name = '{} - Copy'.format(new_instance.name)
        new_instance.creator = None
        new_instance.run_task_id = ''
        new_instance.generate_inputs_task_id = ''
        new_instance.status = self.status_choices.NEW
        new_instance.input_errors_file = None
        new_instance.output_file = None
        return new_instance

from __future__ import absolute_import, print_function

from celery import signature
from celery.result import AsyncResult
from django.conf import settings
from django.core.files.base import File
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from model_utils.models import TimeStampedModel
from model_utils.choices import Choices
from rest_framework.exceptions import ValidationError
from rest_framework.reverse import reverse

from ..files.models import RelatedFile, file_storage_link
from ..analysis_models.models import AnalysisModel
from ..data_files.models import DataFile
from ..portfolios.models import Portfolio
from .tasks import record_generate_input_result, record_run_analysis_result
from ....common.data import STORED_FILENAME, ORIGINAL_FILENAME


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
    
    def get_absolute_storage_url(self, request=None):
        return reverse('analysis-storage-links', kwargs={'version': 'v1', 'pk': self.pk}, request=request)


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

    def run(self, initiator):
        self.validate_run()

        self.status = self.status_choices.RUN_QUEUED

        run_analysis_signature = self.run_analysis_signature
        run_analysis_signature.link(record_run_analysis_result.s(self.pk, initiator.pk))
        run_analysis_signature.link_error(
            signature('on_error', args=('record_run_analysis_failure', self.pk, initiator.pk), queue=self.model.queue_name)
        )
        dispatched_task = run_analysis_signature.delay()
        self.run_task_id = dispatched_task.id
        self.task_started = None
        self.task_finished = None
        self.save()

    @property
    def run_analysis_signature(self):
        complex_data_files = self.create_complex_model_data_file_dicts()
        input_file = file_storage_link(self.input_file)
        settings_file = file_storage_link(self.settings_file)

        return signature(
            'run_analysis',
            args=(self.pk, input_file, settings_file, complex_data_files),
            queue=self.model.queue_name,
        )

    def cancel(self):
        valid_choices = [
            self.status_choices.RUN_QUEUED,
            self.status_choices.RUN_STARTED
        ]
        if self.status not in valid_choices:
            raise ValidationError({'status': ['Analysis is not running or queued']})

        AsyncResult(self.run_task_id).revoke(
            signal='SIGKILL',
            terminate=True,
        )

        self.status = self.status_choices.RUN_CANCELLED
        self.task_finished = timezone.now()
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

        if self.model.deleted:
            errors['model'] = ['Model pk "{}" has been deleted'.format(self.model.id)]

        if not self.portfolio.location_file:
            errors['portfolio'] = ['"location_file" must not be null']

        if errors:
            raise ValidationError(errors)

        self.status = self.status_choices.INPUTS_GENERATION_QUEUED
        generate_input_signature = self.generate_input_signature
        generate_input_signature.link(record_generate_input_result.s(self.pk, initiator.pk))
        generate_input_signature.link_error(
            signature('on_error', args=('record_generate_input_failure', self.pk, initiator.pk), queue=self.model.queue_name)
        )
        self.generate_inputs_task_id = generate_input_signature.delay().id
        self.task_started = None
        self.task_finished = None
        self.save()

    def cancel_generate_inputs(self):
        valid_choices = [
            self.status_choices.INPUTS_GENERATION_QUEUED,
            self.status_choices.INPUTS_GENERATION_STARTED
        ]
        if self.status not in valid_choices:
            raise ValidationError({'status': ['Analysis input generation is not running or queued']})

        self.status = self.status_choices.INPUTS_GENERATION_CANCELLED
        AsyncResult(self.generate_inputs_task_id).revoke(
            signal='SIGKILL',
            terminate=True,
        )
        self.task_finished = timezone.now()
        self.save()

    @property
    def generate_input_signature(self):
        loc_file = file_storage_link(self.portfolio.location_file)
        acc_file = file_storage_link(self.portfolio.accounts_file)
        info_file = file_storage_link(self.portfolio.reinsurance_info_file)
        scope_file = file_storage_link(self.portfolio.reinsurance_scope_file)
        settings_file = file_storage_link(self.settings_file)
        complex_data_files = self.create_complex_model_data_file_dicts()

        return signature(
            'generate_input',
            args=(self.pk, loc_file, acc_file, info_file, scope_file, settings_file, complex_data_files),
            queue=self.model.queue_name
        )

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

@receiver(post_delete, sender=Analysis)
def delete_connected_files(sender, instance, **kwargs):
    """ Post delete handler to clear out any dangaling analyses files
    """
    files_for_removal = [ 
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
    for ref in files_for_removal:
        file_ref = getattr(instance, ref)
        if file_ref:
            file_ref.delete()

from __future__ import absolute_import, print_function

import json

from celery.result import AsyncResult
from django.conf import settings
from django.core.files import File
from django.db import models
from django.urls import reverse
from django.utils.encoding import python_2_unicode_compatible
from django.utils.six import BytesIO
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel
from model_utils.choices import Choices
from pathlib2 import Path
from rest_framework.exceptions import ValidationError

from ..files.models import RelatedFile
from ..celery import celery_app
from ..analysis_models.models import AnalysisModel
from ..portfolios.models import Portfolio
from .tasks import poll_analysis_status


@python_2_unicode_compatible
class Analysis(TimeStampedModel):
    status_choices = Choices(
        ('NOT_RAN', 'Not ran'),
        ('PENDING', 'Pending'),
        ('STARTED', 'Started'),
        ('STOPPED_COMPLETED', 'Stopped - Completed'),
        ('STOPPED_CANCELLED', 'Stopped - Cancelled'),
        ('STOPPED_ERROR', 'Stopped - Error'),
    )

    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='analyses')
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name='analyses', help_text=_('The portfolio to link the analysis to'))
    model = models.ForeignKey(AnalysisModel, on_delete=models.DO_NOTHING, related_name='analyses', help_text=_('The model to link the analysis to'))
    name = models.CharField(help_text='The name of the analysis', max_length=255)
    status = models.CharField(max_length=max(len(c) for c in status_choices._db_values), choices=status_choices, default=status_choices.NOT_RAN, editable=False)
    task_id = models.CharField(max_length=255, editable=False, default='', blank=True)

    settings_file = models.ForeignKey(RelatedFile, null=True, default=None, related_name='settings_file_analyses')
    input_file = models.ForeignKey(RelatedFile, null=True, default=None, related_name='input_file_analyses')
    input_errors_file = models.ForeignKey(RelatedFile, null=True, default=None, related_name='input_errors_file_analyses')
    output_file = models.ForeignKey(RelatedFile, null=True, default=None, related_name='output_file_analyses')

    class Meta:
        verbose_name_plural = 'analyses'

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('analysis-detail', args=[self.pk])

    def get_absolute_run_url(self):
        return reverse('analysis-run', args=[self.pk])

    def get_absolute_cancel_url(self):
        return reverse('analysis-cancel', args=[self.pk])

    def get_absolute_copy_url(self):
        return reverse('analysis-copy', args=[self.pk])

    def get_absolute_settings_file_url(self):
        return reverse('analysis-settings-file', args=[self.pk])

    def get_absolute_input_file_url(self):
        return reverse('analysis-input-file', args=[self.pk])

    def get_absolute_input_errors_file_url(self):
        return reverse('analysis-input-errors-file', args=[self.pk])

    def get_absolute_output_file_url(self):
        return reverse('analysis-output-file', args=[self.pk])

    def validate_run(self):
        errors = []

        if self.status not in [self.status_choices.NOT_RAN, self.status_choices.STOPPED_COMPLETED, self.status_choices.STOPPED_ERROR]:
            raise ValidationError({'error': ['Analysis is already running']})

        if not self.model:
            errors.append('"model" is not set on the analysis object')

        if not self.settings_file:
            errors.append('"settings_file" is not set on the analysis object')

        if not self.input_file:
            errors.append('"input_file" is not set on the analysis object')

        if errors:
            errors_dict = {'errors': errors}

            self.status = self.status_choices.STOPPED_ERROR
            self.input_errors_file = RelatedFile.objects.create(
                file=File(BytesIO(json.dumps(errors_dict).encode()), 'file.json'),
                content_type='application/json',
            )

            self.save()

            raise ValidationError(detail=errors_dict)

    def run(self, request):
        self.validate_run()

        self.status = self.status_choices.PENDING
        self.task_id = celery_app.send_task(
            'run_analysis', (self.input_file.file.name, [json.loads(self.settings_file.read())]),
            queue='{}-{}'.format(self.model.supplier_id, self.model.version_id)
        )
        poll_analysis_status.delay(self.pk)

        self.save()

    def cancel(self):
        if self.status not in [self.status_choices.PENDING, self.status_choices.STARTED]:
            raise ValidationError({'error': ['Analysis is not running']})

        AsyncResult(self.task_id).revoke(signal='SIGKILL', terminate=True)

    def copy(self):
        new_instance = self
        new_instance.pk = None
        new_instance.name = '{} - Copy'.format(new_instance.name)
        new_instance.creator = None
        new_instance.task_id = ''
        new_instance.status = self.status_choices.NOT_RAN
        new_instance.input_errors_file = None
        new_instance.output_file = None
        return new_instance

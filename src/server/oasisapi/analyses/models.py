from __future__ import absolute_import, print_function

import json
from tempfile import NamedTemporaryFile

from django.conf import settings
from django.core.files import File
from django.core.validators import FileExtensionValidator
from django.db import models
from django.urls import reverse
from django.utils.encoding import python_2_unicode_compatible
from model_utils.models import TimeStampedModel
from model_utils.choices import Choices
from rest_framework.exceptions import ValidationError

from ..celery import celery_app
from ..analysis_models.models import AnalysisModel
from ..files.upload import random_file_name
from ..portfolios.models import Portfolio
from .tasks import poll_analysis_status


@python_2_unicode_compatible
class Analysis(TimeStampedModel):
    status_choices = Choices(
        ('NOT_RAN', 'Not ran'),
        ('STARTED', 'Started'),
        ('STOPPED_COMPLETED', 'Stopped - Completed'),
        ('STOPPED_ERROR', 'Stopped - Error'),
    )

    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='analyses')
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name='analyses')
    model = models.ForeignKey(AnalysisModel, on_delete=models.SET_DEFAULT, related_name='analyses', null=True, default=None)
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=max(len(c) for c in status_choices._db_values), choices=status_choices, default=status_choices.NOT_RAN)
    task_id = models.CharField(max_length=255, editable=False, default='', blank=True)

    settings_file = models.FileField(
        upload_to=random_file_name,
        validators=[FileExtensionValidator(allowed_extensions=['json'])],
        null=True,
        default=None,
    )
    input_file = models.FileField(
        upload_to=random_file_name,
        validators=[FileExtensionValidator(allowed_extensions=['tar'])],
        null=True,
        default=None,
    )
    input_errors_file = models.FileField(
        upload_to=random_file_name,
        null=True,
        default=None,
        editable=False,
    )
    output_file = models.FileField(
        upload_to=random_file_name,
        null=True,
        default=None,
        editable=False,
    )

    class Meta:
        verbose_name_plural = 'analyses'

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('analysis-detail', args=[self.pk])

    def get_absolute_run_url(self):
        return reverse('analysis-run', args=[self.pk])

    def validate(self):
        errors = []

        if not self.model:
            errors.append('"model" is not set on the analysis object')

        if not self.settings_file:
            errors.append('"settings_file" is not set on the analysis object')

        if not self.input_file:
            errors.append('"input_file" is not set on the analysis object')

        if errors:
            self.status = self.status_choices.STOPPED_ERROR
            errors_dict = {'errors': errors}

            with NamedTemporaryFile('w+') as f:
                f.write(json.dumps(errors_dict))
                self.input_errors_file = File(f, '{}.json'.format(f.name))

                self.save()

            raise ValidationError(detail=errors_dict)

    def run(self, request):
        self.validate()

        self.status = self.status_choices.STARTED
        self.task_id = celery_app.send_task(
            'run_analysis',
            (request.build_absolute_uri(self.input_file.url), [json.loads(self.settings_file.read())]),
            queue='{}-{}'.format(self.model.supplier_id, self.model.version_id)
        )
        poll_analysis_status.delay(self.pk)

        self.save()

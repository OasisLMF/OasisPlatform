from __future__ import absolute_import, print_function

from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models
from django.urls import reverse
from django.utils.encoding import python_2_unicode_compatible
from django_extensions.db.models import TimeStampedModel

from ..files.upload import random_file_name
from ..portfolio.models import Portfolio


@python_2_unicode_compatible
class Analysis(TimeStampedModel):
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='analyses')
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name='analyses')
    name = models.CharField(max_length=255)

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

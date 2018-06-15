from __future__ import absolute_import, print_function

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.encoding import python_2_unicode_compatible
from django.core.validators import FileExtensionValidator
from django_extensions.db.models import TimeStampedModel

from ..files.upload import random_file_name


@python_2_unicode_compatible
class Portfolio(TimeStampedModel):
    name = models.CharField(max_length=255)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='portfolios')

    accounts_file = models.FileField(
        upload_to=random_file_name,
        validators=[FileExtensionValidator(allowed_extensions=['csv', 'json'])],
        null=True,
        default=None,
    )
    location_file = models.FileField(
        upload_to=random_file_name,
        validators=[FileExtensionValidator(allowed_extensions=['csv', 'json'])],
        null=True,
        default=None,
    )
    reinsurance_source_file = models.FileField(
        upload_to=random_file_name,
        validators=[FileExtensionValidator(allowed_extensions=['csv', 'json'])],
        null=True,
        default=None,
    )
    reinsurance_info_file = models.FileField(
        upload_to=random_file_name,
        validators=[FileExtensionValidator(allowed_extensions=['csv', 'json'])],
        null=True,
        default=None,
    )

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('portfolio-detail', args=[self.pk])

    def get_absolute_create_analysis_url(self):
        return reverse('portfolio-create-analysis', args=[self.pk])

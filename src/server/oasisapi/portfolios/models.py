from __future__ import absolute_import, print_function

import io
import pathlib
import ods_tools

from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from model_utils.models import TimeStampedModel
from rest_framework.reverse import reverse

from ..files.models import RelatedFile


class Portfolio(TimeStampedModel):
    name = models.CharField(max_length=255, help_text=_('The name of the portfolio'))
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='portfolios')
    groups = models.ManyToManyField(Group, blank=True, null=False, default=None, help_text='Groups allowed to access this object')

    accounts_file = models.ForeignKey(RelatedFile, on_delete=models.CASCADE, blank=True, null=True, default=None, related_name='accounts_file_portfolios')
    location_file = models.ForeignKey(RelatedFile, on_delete=models.CASCADE, blank=True, null=True, default=None, related_name='location_file_portfolios')
    reinsurance_info_file = models.ForeignKey(RelatedFile, on_delete=models.CASCADE, blank=True, null=True, default=None, related_name='reinsurance_info_file_portfolios')
    reinsurance_scope_file = models.ForeignKey(RelatedFile, on_delete=models.CASCADE, blank=True, null=True, default=None, related_name='reinsurance_scope_file_portfolios')

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.name

    def get_absolute_url(self, request=None):
        return reverse('portfolio-detail', kwargs={'version': 'v1', 'pk': self.pk}, request=request)

    def get_absolute_create_analysis_url(self, request=None):
        return reverse('portfolio-create-analysis', kwargs={'version': 'v1', 'pk': self.pk}, request=request)

    def get_absolute_accounts_file_url(self, request=None):
        return reverse('portfolio-accounts-file', kwargs={'version': 'v1', 'pk': self.pk}, request=request)

    def get_absolute_location_file_url(self, request=None):
        return reverse('portfolio-location-file', kwargs={'version': 'v1', 'pk': self.pk}, request=request)

    def get_absolute_reinsurance_info_file_url(self, request=None):
        return reverse('portfolio-reinsurance-info-file', kwargs={'version': 'v1', 'pk': self.pk}, request=request)

    def get_absolute_reinsurance_scope_file_url(self, request=None):
        return reverse('portfolio-reinsurance-scope-file', kwargs={'version': 'v1', 'pk': self.pk}, request=request)

    def get_absolute_storage_url(self, request=None):
        return reverse('portfolio-storage-links', kwargs={'version': 'v1', 'pk': self.pk}, request=request)

    def location_file_len(self):
        csv_compression_types = {
            'text/csv': 'infer',
            'application/gzip': 'gzip',
            'application/x-bzip2': 'bz2',
            'application/zip': 'zip'
        }
        if not self.location_file:
            return None

        if self.location_file.content_type == 'application/octet-stream':
            df = ods_tools.read_parquet(io.BytesIO(self.location_file.file.read()))
            return len(df.index)
        if self.location_file.content_type in csv_compression_types:
            df = ods_tools.read_csv(io.BytesIO(self.location_file.file.read()), compression=csv_compression_types[self.location_file.content_type])
            return len(df.index)


class PortfolioStatus(TimeStampedModel):

    def __str__(self):
        pass

@receiver(post_delete, sender=Portfolio)
def delete_connected_files(sender, instance, **kwargs):
    """ Post delete handler to clear out any dangaling analyses files
    """
    files_for_removal = [
         'accounts_file',
         'location_file',
         'reinsurance_info_file',
         'reinsurance_scope_file',
    ]
    for ref in files_for_removal:
        file_ref = getattr(instance, ref)
        if file_ref:
            file_ref.delete()

from __future__ import absolute_import, print_function

from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from model_utils.models import TimeStampedModel
from rest_framework.reverse import reverse

from ..files.models import RelatedFile


@python_2_unicode_compatible
class Portfolio(TimeStampedModel):
    name = models.CharField(max_length=255, help_text=_('The name of the portfolio'))
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='portfolios')

    accounts_file = models.ForeignKey(RelatedFile, blank=True, null=True, default=None, related_name='accounts_file_portfolios')
    location_file = models.ForeignKey(RelatedFile, blank=True, null=True, default=None, related_name='location_file_portfolios')
    reinsurance_info_file = models.ForeignKey(RelatedFile, blank=True, null=True, default=None, related_name='reinsurance_info_file_portfolios')
    reinsurance_source_file = models.ForeignKey(RelatedFile, blank=True, null=True, default=None, related_name='reinsurance_source_file_portfolios')

    def __str__(self):
        return self.name

    def get_absolute_url(self, request=None):
        return reverse('portfolio-detail', kwargs={'pk': self.pk}, request=request)

    def get_absolute_create_analysis_url(self, request=None):
        return reverse('portfolio-create-analysis', kwargs={'pk': self.pk}, request=request)

    def get_absolute_accounts_file_url(self, request=None):
        return reverse('portfolio-accounts-file', kwargs={'pk': self.pk}, request=request)

    def get_absolute_location_file_url(self, request=None):
        return reverse('portfolio-location-file', kwargs={'pk': self.pk}, request=request)

    def get_absolute_reinsurance_info_file_url(self, request=None):
        return reverse('portfolio-reinsurance-info-file', kwargs={'pk': self.pk}, request=request)

    def get_absolute_reinsurance_source_file_url(self, request=None):
        return reverse('portfolio-reinsurance-source-file', kwargs={'pk': self.pk}, request=request)


@python_2_unicode_compatible
class PortfolioStatus(TimeStampedModel):


    def __str__(self):
        pass


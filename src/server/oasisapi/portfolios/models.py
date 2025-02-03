from __future__ import absolute_import, print_function

from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from model_utils.models import TimeStampedModel
from rest_framework.reverse import reverse
from rest_framework.exceptions import ValidationError

from ..files.models import RelatedFile, related_file_to_df

import re

from ods_tools.oed.exposure import OedExposure
from ods_tools.oed import OdsException


def oed_class_of_businesses__workaround(e):
    """ workaround function to format ClassOfBusiness exceptions from
        an ODS-tools validation call

        If not a ClassOfBusiness error return an empty dict
    """
    format_as_validation_error = False
    result = []

    if not isinstance(e, OdsException):
        return result

    exception_string = str(e)
    if 'ClassOfBusiness' in exception_string:
        lines = exception_string.splitlines()

        current_key = None
        for line in lines:
            line = line.strip()

            # Check if it's a new key (ClassOfBusiness.*)
            if line.endswith(':'):
                current_key = line[:-1]
            elif line.endswith('missing'):
                line = line[:-8].strip()  # Remove " missing" and strip extra spaces
                fields = re.split(r',\s*', line)  # Split by commas
                for field in fields:
                    field = field.strip()
                    result.append({
                        'name': current_key,
                        'msg': f'missing required column {field}'
                    })

    return result


class Portfolio(TimeStampedModel):
    name = models.CharField(max_length=255, help_text=_('The name of the portfolio'))
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='portfolios')
    groups = models.ManyToManyField(Group, blank=True, default=None, help_text='Groups allowed to access this object')

    accounts_file = models.ForeignKey(RelatedFile, on_delete=models.CASCADE, blank=True, null=True,
                                      default=None, related_name='accounts_file_portfolios')
    location_file = models.ForeignKey(RelatedFile, on_delete=models.CASCADE, blank=True, null=True,
                                      default=None, related_name='location_file_portfolios')
    reinsurance_info_file = models.ForeignKey(RelatedFile, on_delete=models.CASCADE, blank=True, null=True,
                                              default=None, related_name='reinsurance_info_file_portfolios')
    reinsurance_scope_file = models.ForeignKey(RelatedFile, on_delete=models.CASCADE, blank=True, null=True,
                                               default=None, related_name='reinsurance_scope_file_portfolios')

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.name

    def get_absolute_url(self, request=None, namespace=None):
        override_ns = f'{namespace}:' if namespace else ''
        return reverse(f'{override_ns}portfolio-detail', kwargs={'pk': self.pk}, request=request)

    def get_absolute_create_analysis_url(self, request=None, namespace=None):
        override_ns = f'{namespace}:' if namespace else ''
        return reverse(f'{override_ns}portfolio-create-analysis', kwargs={'pk': self.pk}, request=request)

    def get_absolute_accounts_file_url(self, request=None, namespace=None):
        override_ns = f'{namespace}:' if namespace else ''
        return reverse(f'{override_ns}portfolio-accounts-file', kwargs={'pk': self.pk}, request=request)

    def get_absolute_location_file_url(self, request=None, namespace=None):
        override_ns = f'{namespace}:' if namespace else ''
        return reverse(f'{override_ns}portfolio-location-file', kwargs={'pk': self.pk}, request=request)

    def get_absolute_reinsurance_info_file_url(self, request=None, namespace=None):
        override_ns = f'{namespace}:' if namespace else ''
        return reverse(f'{override_ns}portfolio-reinsurance-info-file', kwargs={'pk': self.pk}, request=request)

    def get_absolute_reinsurance_scope_file_url(self, request=None, namespace=None):
        override_ns = f'{namespace}:' if namespace else ''
        return reverse(f'{override_ns}portfolio-reinsurance-scope-file', kwargs={'pk': self.pk}, request=request)

    def get_absolute_storage_url(self, request=None, namespace=None):
        override_ns = f'{namespace}:' if namespace else ''
        return reverse(f'{override_ns}portfolio-storage-links', kwargs={'pk': self.pk}, request=request)

    def get_absolute_accounts_file_sql_url(self, request=None, namespace=None):
        override_ns = f'{namespace}:' if namespace else ''
        return reverse(
            f'{override_ns}portfolio-file-sql', kwargs={'pk': self.pk, 'file': 'accounts_file'},
            request=request
        )

    def get_absolute_location_file_sql_url(self, request=None, namespace=None):
        override_ns = f'{namespace}:' if namespace else ''
        return reverse(
            f'{override_ns}portfolio-file-sql', kwargs={'pk': self.pk, 'file': 'location_file'},
            request=request
        )

    def get_absolute_reinsurance_info_file_sql_url(self, request=None, namespace=None):
        override_ns = f'{namespace}:' if namespace else ''
        return reverse(
            f'{override_ns}portfolio-file-sql', kwargs={'pk': self.pk, 'file': 'reinsurance_info_file'},
            request=request
        )

    def get_absolute_reinsurance_scope_file_sql_url(self, request=None, namespace=None):
        override_ns = f'{namespace}:' if namespace else ''
        return reverse(
            f'{override_ns}portfolio-file-sql', kwargs={'pk': self.pk, 'file': 'reinsurance_scope_file'},
            request=request
        )

    def location_file_len(self):
        csv_compression_types = {
            'text/csv': 'infer',
            'application/vnd.ms-excel': 'infer',
            'application/gzip': 'gzip',
            'application/x-bzip2': 'bz2',
            'application/zip': 'zip',
        }
        if not self.location_file:
            return None

        df = related_file_to_df(self.location_file)
        return len(df.index)

    def set_portolio_valid(self):
        oed_files = [
            'accounts_file',
            'location_file',
            'reinsurance_info_file',
            'reinsurance_scope_file',
        ]
        for ref in oed_files:
            file_ref = getattr(self, ref)
            if file_ref:
                file_ref.oed_validated = True
                file_ref.save()

    def run_oed_validation(self):
        try:
            portfolio_exposure = OedExposure(
                location=getattr(self.location_file, 'file', None),
                account=getattr(self.accounts_file, 'file', None),
                ri_info=getattr(self.reinsurance_info_file, 'file', None),
                ri_scope=getattr(self.reinsurance_scope_file, 'file', None),
                validation_config=settings.PORTFOLIO_VALIDATION_CONFIG)
            validation_errors = portfolio_exposure.check()
        except Exception as e:
            COB_validation_errors = oed_class_of_businesses__workaround(e)
            if COB_validation_errors:
                validation_errors = COB_validation_errors
            else:
                raise ValidationError({
                    'error': 'Failed to validate portfolio',
                    'detail': str(e),
                    'exception': type(e).__name__
                })

        # Set validation fields to true or raise exception
        if validation_errors:
            raise ValidationError(detail=[(error['name'], error['msg']) for error in validation_errors])
        else:
            self.set_portolio_valid()


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

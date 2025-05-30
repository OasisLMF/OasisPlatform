from __future__ import absolute_import, print_function

from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from model_utils.models import TimeStampedModel
from model_utils.choices import Choices
from rest_framework.reverse import reverse
from rest_framework.exceptions import ValidationError

from ..files.models import RelatedFile, related_file_to_df
from src.server.oasisapi.celery_app_v2 import v2 as celery_app_v2
from .v2_api.tasks import record_exposure_output, record_validation_output, record_exposure_transformation

import re

# from ods_tools.oed.exposure import OedExposure
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
        if result:
            raise ValidationError(detail=sorted([(error['name'], error['msg']) for error in result]))


class Portfolio(TimeStampedModel):
    exposure_status_choices = Choices(
        ('NONE', 'No exposure run calls'),
        ('INSUFFICIENT_DATA', 'Missing location/accounts file'),
        ('STARTED', 'An exposure run has been started'),
        ('ERROR', 'Exposure run has failed'),
        ('RUN_COMPLETED', 'Exposure run has successfully finished'),
    )
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
    exposure_run_file = models.ForeignKey(RelatedFile, on_delete=models.CASCADE, blank=True, null=True,
                                          default=None, related_name='exposure_run_file_portfolios')
    exposure_status = models.CharField(
        max_length=max(len(c) for c in exposure_status_choices._db_values),
        choices=exposure_status_choices, default=exposure_status_choices.NONE, editable=False, db_index=True
    )

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

    def set_portfolio_valid(self):
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

    # Task signatures #

    def run_oed_validation_signature(self):
        location = get_path_or_url(self.location_file)
        account = get_path_or_url(self.accounts_file)
        ri_info = get_path_or_url(self.reinsurance_info_file)
        ri_scope = get_path_or_url(self.reinsurance_scope_file)
        validation_config = settings.PORTFOLIO_VALIDATION_CONFIG

        return celery_app_v2.signature(
            'run_oed_validation',
            args=(location, account, ri_info, ri_scope, validation_config)
        )

    def exposure_run_signature(self, params):
        if not self.location_file or not self.accounts_file:
            self.exposure_status = self.exposure_status_choices.INSUFFICIENT_DATA
            self.save()
            raise ValidationError("Exposure run requires a location and an accounts file!")

        location = get_path_or_url(self.location_file)
        account = get_path_or_url(self.accounts_file)
        ri_info = get_path_or_url(self.reinsurance_info_file)
        ri_scope = get_path_or_url(self.reinsurance_scope_file)

        return celery_app_v2.signature(
            'run_exposure_task',
            args=(location, account, ri_info, ri_scope, params),
            priority=10
        )

    def exposure_transformation_signature(self, request):
        location = get_path_or_url(self.location_file)
        account = get_path_or_url(self.accounts_file)
        ri_info = get_path_or_url(self.reinsurance_info_file)
        ri_scope = get_path_or_url(self.reinsurance_scope_file)
        details = request.data
        return celery_app_v2.signature(
            'run_exposure_transform',
            args=([location, account, ri_info, ri_scope], details),
            priority=10
        )

    # Task calls #

    def run_oed_validation(self):
        task = self.run_oed_validation_signature()
        task.link(record_validation_output.s(self.pk))
        task.apply_async(queue='oasis-internal-worker', priority=10)

    def exposure_run(self, params, user_pk):
        task = self.exposure_run_signature(params)
        task.link(record_exposure_output.s(self.pk, user_pk))
        task.apply_async(queue='oasis-internal-worker', priority=10)
        self.exposure_status = self.exposure_status_choices.STARTED
        self.save()

    def exposure_transformation(self, request):
        task = self.exposure_transformation_signature(request)
        task.link(record_exposure_transformation.s(self.pk, request.user.pk))
        task.apply_async(queue='oasis-internal-worker', priority=10)


def get_path_or_url(file):
    """
    S3 Files have no path attribute and Localstorage needs to use path
    """
    file = getattr(file, 'file', None)
    if file:
        return getattr(file, 'path', getattr(file, 'url', None))
    return None


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

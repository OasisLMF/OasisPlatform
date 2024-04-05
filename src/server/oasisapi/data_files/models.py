from django.conf import settings
from django.contrib.auth.models import Group
from django.db import models
from django.utils.translation import gettext_lazy as _
from model_utils.models import TimeStampedModel
from rest_framework.reverse import reverse

from ..files.models import RelatedFile


class DataFile(TimeStampedModel):
    file_description = models.CharField(
        max_length=255,
        help_text=_('Type of data contained within the file.')
    )
    file_category = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        default=None,
        help_text=_('Grouping label for data files (optional value)')
    )
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='data_file'
    )
    file = models.ForeignKey(
        RelatedFile,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        default=None,
        related_name="content_data_file"
    )
    groups = models.ManyToManyField(Group, blank=True, default=None, help_text='Groups allowed to access this object')

    class Meta:
        ordering = ['id']

    def __str__(self):
        return 'DataFile_{}'.format(self.file)

    def _update_ns(self, request=None):
        """ WORKAROUND - this is needed for when a copy request is issued
                         from the portfolio view '/{ver}/portfolios/{id}/create_analysis/'

                         The inncorrect namespace '{ver}-portfolios' is inherited from the
                         original request. This needs to be replaced with '{ver}-analyses'
        """
        if not request:
            return None
        ns_ver, ns_view = request.version.split('-')
        if ns_view != 'files':
            request.version = f'{ns_ver}-files'
        return request

    def get_filename(self):
        if self.file:
            return self.file.filename
        else:
            return None

    def get_filestore(self):
        if self.file:
            return self.file.file.name
        else:
            return None

    def get_content_type(self):
        if self.file:
            return self.file.content_type
        else:
            return None

    def get_absolute_data_file_url(self, request=None, namespace=None):
        override_ns = f'{namespace}:' if namespace else ''
        return reverse(f'{override_ns}data-file-content', kwargs={'pk': self.pk}, request=self._update_ns(request))

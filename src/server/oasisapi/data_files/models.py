from django.conf import settings
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

    def __str__(self):
        return 'DataFile_{}'.format(self.file)

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

    def get_absolute_data_file_url(self, request=None):
        return reverse('data-file-content', kwargs={'version': 'v1', 'pk': self.pk}, request=request)

import os
from uuid import uuid4

from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel


def random_file_name(instance, filename):
    ext = os.path.splitext(filename)[-1]
    return '{}{}'.format(uuid4().hex, ext)


class RelatedFile(TimeStampedModel):
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, null=True)
    file = models.FileField(help_text=_('The file to store'), upload_to=random_file_name)
    filename = models.CharField(max_length=255, editable=False, default=None, null=True, blank=True)
    content_type = models.CharField(max_length=255)

    def __str__(self):
        return 'File_{}'.format(self.file)

    def read(self, *args, **kwargs):
        return self.file.read(*args, **kwargs)

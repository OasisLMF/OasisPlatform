from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from model_utils.models import TimeStampedModel


@python_2_unicode_compatible
class AnalysisModel(TimeStampedModel):
    supplier_id = models.CharField(max_length=255, help_text=_('The supplier ID for the model.'))
    version_id = models.CharField(max_length=255, help_text=_('The version ID for the model.'))
    keys_server_uri = models.URLField(help_text=_('The root url for the model server.'))
    creator = models.ForeignKey(settings.AUTH_USER_MODEL)

    class Meta:
        unique_together = ('supplier_id', 'version_id')

    def __str__(self):
        return '{} - {}'.format(self.supplier_id, self.version_id)

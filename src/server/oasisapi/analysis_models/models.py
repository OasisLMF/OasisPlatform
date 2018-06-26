from django.utils.translation import ugettext_lazy as _
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from model_utils.models import TimeStampedModel


@python_2_unicode_compatible
class AnalysisModel(TimeStampedModel):
    supplier_id = models.CharField(max_length=255, help_text=_('The supplier ID for the model.'))
    version_id = models.CharField(max_length=255, help_text=_('The version ID for the model.'))

    class Meta:
        unique_together = ('supplier_id', 'version_id')

    def __str__(self):
        return '{} - {}'.format(self.supplier_id, self.version_id)

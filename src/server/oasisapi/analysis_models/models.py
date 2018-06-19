from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from model_utils.models import TimeStampedModel


@python_2_unicode_compatible
class AnalysisModel(TimeStampedModel):
    supplier_id = models.CharField(max_length=255)
    version_id = models.CharField(max_length=255)

    class Meta:
        unique_together = ('supplier_id', 'version_id')

    def __str__(self):
        return '{} - {}'.format(self.supplier_id, self.version_id)

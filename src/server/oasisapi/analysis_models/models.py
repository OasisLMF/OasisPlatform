from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from model_utils.models import TimeStampedModel
from rest_framework.reverse import reverse

from ..files.models import RelatedFile

@python_2_unicode_compatible
class AnalysisModel(TimeStampedModel):
    supplier_id = models.CharField(max_length=255, help_text=_('The supplier ID for the model.'))
    model_id = models.CharField(max_length=255, help_text=_('The model ID for the model.'))
    version_id = models.CharField(max_length=255, help_text=_('The version ID for the model.'))
    resource_file = models.ForeignKey(RelatedFile, null=True, default=None, related_name='analysis_model_resource_file')
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, default="")

    class Meta:
        unique_together = ('supplier_id', 'model_id', 'version_id')

    def __str__(self):
        return '{}-{}-{}'.format(self.supplier_id, self.model_id, self.version_id)

    @property
    def queue_name(self):
        return str(self)


    def get_absolute_resources_file_url(self, request=None):
        return reverse('analysis-model-resource-file', kwargs={'pk': self.pk}, request=request)


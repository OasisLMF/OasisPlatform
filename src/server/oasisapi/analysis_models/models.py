from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from model_utils.models import TimeStampedModel
from rest_framework.reverse import reverse

from ..files.models import RelatedFile
from ..data_files.models import DataFile


@python_2_unicode_compatible
class AnalysisModel(TimeStampedModel):
    supplier_id = models.CharField(max_length=255, help_text=_('The supplier ID for the model.'))
    model_id = models.CharField(max_length=255, help_text=_('The model ID for the model.'))
    version_id = models.CharField(max_length=255, help_text=_('The version ID for the model.'))
    resource_file = models.ForeignKey(RelatedFile, on_delete=models.CASCADE, null=True, default=None, related_name='analysis_model_resource_file')
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    data_files = models.ManyToManyField(DataFile, blank=True, related_name='analyses_model_data_files')
    ver_ktools = models.CharField(max_length=255, null=True, default=None, help_text=_('The worker ktools version.'))
    ver_oasislmf = models.CharField(max_length=255, null=True, default=None, help_text=_('The worker oasislmf version.'))
    ver_platform = models.CharField(max_length=255, null=True, default=None, help_text=_('The worker platform version.'))
    oasislmf_config = models.TextField(default='')

    class Meta:
        unique_together = ('supplier_id', 'model_id', 'version_id')

    def __str__(self):
        return '{}-{}-{}'.format(self.supplier_id, self.model_id, self.version_id)

    @property
    def queue_name(self):
        return str(self)

    def get_absolute_resources_file_url(self, request=None):
        return reverse('analysis-model-resource-file', kwargs={'version': 'v1', 'pk': self.pk}, request=request)
    def get_absolute_versions_url(self, request=None):
        return reverse('analysis-model-versions', kwargs={'version': 'v1', 'pk': self.pk}, request=request)
    def get_absolute_settings_url(self, request=None):
        return reverse('model-settings', kwargs={'version': 'v1', 'pk': self.pk}, request=request)


class QueueModelAssociation(models.Model):
    model = models.ForeignKey(AnalysisModel, null=False, on_delete=models.CASCADE, related_name='queue_associations')
    queue_name = models.CharField(max_length=255, blank=False, editable=False)

    class Meta:
        unique_together = (('model', 'queue_name'), )

    def __str__(self):
        return f'{self.model}: {self.queue_name}'

from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.db import models
from model_utils.models import TimeStampedModel
from rest_framework.reverse import reverse

from ..files.models import RelatedFile
from ..data_files.models import DataFile


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
    deleted = models.BooleanField(default=False, editable=False)

    class Meta:
        unique_together = ('supplier_id', 'model_id', 'version_id')

    def __str__(self):
        return '{}-{}-{}'.format(self.supplier_id, self.model_id, self.version_id)

    @property
    def queue_name(self):
        return str(self)

    def hard_delete(self):
        super(AnalysisModel, self).delete()
    
    def delete(self):
        self.deleted = True
        self.save()
    
    def activate(self):
        self.deleted = False
        self.save()

    def get_absolute_resources_file_url(self, request=None):
        return reverse('analysis-model-resource-file', kwargs={'version': 'v1', 'pk': self.pk}, request=request)
    def get_absolute_versions_url(self, request=None):
        return reverse('analysis-model-versions', kwargs={'version': 'v1', 'pk': self.pk}, request=request)
    def get_absolute_settings_url(self, request=None):
        return reverse('model-settings', kwargs={'version': 'v1', 'pk': self.pk}, request=request)

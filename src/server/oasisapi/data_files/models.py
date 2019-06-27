from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel
from rest_framework.reverse import reverse

from ..files.models import RelatedFile
from ..analysis_models.models import  AnalysisModel


class DataFile(TimeStampedModel):
    filename = models.CharField(max_length=255,
                                 help_text=_('The name of the input file that will be used at runtime.'))
    file_description = models.CharField(max_length=255,
                                        help_text=_('Type of data contained within the file.'))
    creator = models.ForeignKey(settings.AUTH_USER_MODEL,
                                on_delete=models.CASCADE,
                                related_name='data_file')
    file = models.ForeignKey(RelatedFile, blank=True, null=True, default=None,
                                  related_name="content_data_file")

    #linked_models = models.ForeignKey(AnalysisModel, blank=True, null=True, default=None, related_name="models_data_file")
    linked_models = models.ManyToManyField(AnalysisModel, related_name="model_list", blank=True)

    def __str__(self):
        return 'DataFile_{}'.format(self.file)

    def update_filename(self):
        if self.file:
            self.filename = self.file.filename
            self.save()
            return self.filename
        else:    
            return None     

    def get_absolute_data_file_url(self, request=None):
        return reverse('data-file-content', kwargs={'version': 'v1', 'pk': self.pk}, request=request)

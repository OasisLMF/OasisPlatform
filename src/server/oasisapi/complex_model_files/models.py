from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel
from rest_framework.reverse import reverse

from ..files.models import RelatedFile


class ComplexModelDataFile(TimeStampedModel):
    file_name = models.CharField(max_length=255,
                                 help_text=_('The name of the complex model input file that will be used at runtime.'))
    file_description = models.CharField(max_length=255,
                                        help_text=_('Type of data contained within the file.'))
    creator = models.ForeignKey(settings.AUTH_USER_MODEL,
                                on_delete=models.CASCADE,
                                related_name='complex_model_file')
    data_file = models.ForeignKey(RelatedFile, blank=True, null=True, default=None,
                                  related_name="data_file_complex_model_file")

    def __str__(self):
        return self.name

    def get_absolute_data_file_url(self, request=None):
        return reverse('complex-model-data-file-data-file', kwargs={'version': 'v1', 'pk': self.pk}, request=request)

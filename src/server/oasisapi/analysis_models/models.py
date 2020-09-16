from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from model_utils.models import TimeStampedModel
from rest_framework.reverse import reverse

from ..files.models import RelatedFile
from ..data_files.models import DataFile


class SoftDeleteManager(models.Manager):
    def __init__(self, *args, **kwargs):
        self.alive_only = kwargs.pop('alive_only', True)
        super(SoftDeleteManager, self).__init__(*args, **kwargs)

    def get_queryset(self):
        if self.alive_only:
            return SoftDeleteQuerySet(self.model).filter(deleted=False)
        return SoftDeleteQuerySet(self.model)

    def hard_delete(self):
        return self.get_queryset().hard_delete()


class SoftDeleteQuerySet(models.query.QuerySet):
    def delete(self):
        return super(SoftDeleteQuerySet, self).update(deleted=True)

    def hard_delete(self):
        return super(SoftDeleteQuerySet, self).delete()

    def alive(self):
        return self.filter(deleted=False)

    def dead(self):
        return self.exclude(deleted=False)


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

    # Logical Delete
    objects = SoftDeleteManager()
    all_objects = SoftDeleteManager(alive_only=False)

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
    
    def activate(self, request=None):
        self.deleted = False

        # Update model
        if request:
            self.creator = request.user
            try:
                # update Data_files
                file_pks = request.data['data_files']
                for current_file in self.data_files.all():
                    self.data_files.remove(current_file)
                for new_file in DataFile.objects.filter(pk__in=file_pks):
                    self.data_files.add(new_file.id)
            except KeyError:
                pass
        self.save()

    def get_absolute_resources_file_url(self, request=None):
        return reverse('analysis-model-resource-file', kwargs={'version': 'v1', 'pk': self.pk}, request=request)
    def get_absolute_versions_url(self, request=None):
        return reverse('analysis-model-versions', kwargs={'version': 'v1', 'pk': self.pk}, request=request)
    def get_absolute_settings_url(self, request=None):
        return reverse('model-settings', kwargs={'version': 'v1', 'pk': self.pk}, request=request)

@receiver(post_delete, sender=AnalysisModel)
def delete_connected_files(sender, instance, **kwargs):
    """ Post delete handler to clear out any dangaling analyses files
    """
    files_for_removal = [ 
         'resource_file',
    ]   
    for ref in files_for_removal:
        file_ref = getattr(instance, ref)
        if file_ref:
            file_ref.delete()

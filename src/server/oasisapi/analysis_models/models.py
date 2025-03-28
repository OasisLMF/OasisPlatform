from django.conf import settings
from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from model_utils.models import TimeStampedModel
from model_utils.choices import Choices
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


class ModelScalingOptions(models.Model):
    scaling_types = Choices(
        ('FIXED_WORKERS', 'Fixed number of workers'),
        ('QUEUE_LOAD', 'Scale based on model queue load'),
        ('DYNAMIC_TASKS', 'Scale based on tasks per worker'),
    )
    scaling_strategy = models.CharField(max_length=max(len(c) for c in scaling_types._db_values),
                                        choices=scaling_types, default=scaling_types.FIXED_WORKERS, editable=True)
    worker_count_fixed = models.PositiveSmallIntegerField(default=1, null=False)
    worker_count_max = models.PositiveSmallIntegerField(default=10, null=False)
    worker_count_min = models.PositiveSmallIntegerField(default=0, null=False)
    chunks_per_worker = models.PositiveIntegerField(default=10, null=False)


class ModelChunkingOptions(models.Model):
    chunking_types = Choices(
        ('FIXED_CHUNKS', 'Fixed run partion sizes'),
        ('DYNAMIC_CHUNKS', 'Distribute runs based on input size'),
    )
    lookup_strategy = models.CharField(max_length=max(len(c) for c in chunking_types._db_values),
                                       choices=chunking_types, default=chunking_types.FIXED_CHUNKS, editable=True)
    loss_strategy = models.CharField(max_length=max(len(c) for c in chunking_types._db_values),
                                     choices=chunking_types, default=chunking_types.FIXED_CHUNKS, editable=True)
    dynamic_locations_per_lookup = models.PositiveIntegerField(default=10000, null=False)
    dynamic_events_per_analysis = models.PositiveIntegerField(default=1, null=False)
    dynamic_chunks_max = models.PositiveIntegerField(default=200, null=False)
    fixed_analysis_chunks = models.PositiveSmallIntegerField(default=1, null=True)
    fixed_lookup_chunks = models.PositiveSmallIntegerField(default=1, null=True)


class SettingsTemplate(TimeStampedModel):
    name = models.CharField(
        max_length=255,
        help_text=_('Name for analysis settings template')
    )
    description = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        default=None,
        help_text=_('Description for type of analysis run settings.')
    )
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='settings_template'
    )
    file = models.ForeignKey(
        RelatedFile,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        default=None,
        related_name="analysis_settings_template"
    )

    def __str__(self):
        return 'SettingsTemplate_{}'.format(self.name)

    def get_filename(self):
        if self.settings_template:
            return self.file.filename
        else:
            return None

    def get_filestore(self):
        if self.settings_template:
            return self.settings_template.file.name
        else:
            return None

    def get_absolute_settings_template_url(self, model_pk, request=None, namespace=None):
        override_ns = f'{namespace}:' if namespace else ''
        return reverse(f'{override_ns}models-setting_templates-content', kwargs={'pk': self.pk, 'models_pk': model_pk}, request=self._update_ns(request))


class AnalysisModel(TimeStampedModel):
    run_mode_choices = Choices(
        ('V1', 'Available for Single-Instance Execution'),
        ('V2', 'Available for Distributed Execution'),
    )

    supplier_id = models.CharField(max_length=255, help_text=_('The supplier ID for the model.'))
    model_id = models.CharField(max_length=255, help_text=_('The model ID for the model.'))
    version_id = models.CharField(max_length=255, help_text=_('The version ID for the model.'))
    resource_file = models.ForeignKey(RelatedFile, on_delete=models.CASCADE, null=True, default=None, related_name='analysis_model_resource_file')
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    groups = models.ManyToManyField(Group, blank=True, default=None, help_text='Groups allowed to access this object')
    data_files = models.ManyToManyField(DataFile, blank=True, related_name='analyses_model_data_files')
    template_files = models.ManyToManyField(SettingsTemplate, blank=True, related_name='analyses_model_settings_template')
    ver_ktools = models.CharField(max_length=255, null=True, default=None, help_text=_('The worker ktools version.'))
    ver_oasislmf = models.CharField(max_length=255, null=True, default=None, help_text=_('The worker oasislmf version.'))
    ver_platform = models.CharField(max_length=255, null=True, default=None, help_text=_('The worker platform version.'))
    ver_ods = models.CharField(max_length=255, null=True, default=None, help_text=_('The worker ods-tools version.'))
    ver_oed = models.CharField(max_length=255, null=True, default=None, help_text=_('The worker oed-schema version.'))
    oasislmf_config = models.TextField(default='')
    deleted = models.BooleanField(default=False, editable=False)
    run_mode = models.CharField(max_length=max(len(c) for c in run_mode_choices._db_values),
                                choices=run_mode_choices, default=None, null=True, help_text=_('Execution modes Available, v1 = Single-Instance, v2 = Distributed Execution'))

    scaling_options = models.OneToOneField(ModelScalingOptions, on_delete=models.CASCADE, auto_created=True, default=None, null=True)
    chunking_options = models.OneToOneField(ModelChunkingOptions, on_delete=models.CASCADE, auto_created=True, default=None, null=True)

    # Logical Delete
    objects = SoftDeleteManager()
    all_objects = SoftDeleteManager(alive_only=False)

    class Meta:
        unique_together = ('supplier_id', 'model_id', 'version_id')
        ordering = ['id']

    def __str__(self):
        return '{}-{}-{}'.format(self.supplier_id, self.model_id, self.version_id)

    def _update_ns(self, request=None):
        """ WORKAROUND - this is needed for when a copy request is issued
                         from the portfolio view '/{ver}/portfolios/{id}/create_analysis/'

                         The inncorrect namespace '{ver}-portfolios' is inherited from the
                         original request. This needs to be replaced with '{ver}-analyses'
        """
        if not request:
            return None
        ns_ver, ns_view = request.version.split('-', 1)
        if ns_view != 'models':
            request.version = f'{ns_ver}-models'
        return request

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

    def get_absolute_resources_file_url(self, request=None, namespace=None):
        override_ns = f'{namespace}:' if namespace else ''
        return reverse(f'{override_ns}analysis-model-resource-file', kwargs={'pk': self.pk}, request=self._update_ns(request))

    def get_absolute_versions_url(self, request=None, namespace=None):
        override_ns = f'{namespace}:' if namespace else ''
        return reverse(f'{override_ns}analysis-model-versions', kwargs={'pk': self.pk}, request=self._update_ns(request))

    def get_absolute_settings_url(self, request=None, namespace=None):
        override_ns = f'{namespace}:' if namespace else ''
        return reverse(f'{override_ns}model-settings', kwargs={'pk': self.pk}, request=self._update_ns(request))

    def get_absolute_scaling_configuration_url(self, request=None, namespace=None):
        override_ns = f'{namespace}:' if namespace else ''
        return reverse(f'{override_ns}analysis-model-scaling-configuration', kwargs={'pk': self.pk}, request=self._update_ns(request))

    def get_absolute_chunking_configuration_url(self, request=None, namespace=None):
        override_ns = f'{namespace}:' if namespace else ''
        return reverse(f'{override_ns}analysis-model-chunking-configuration', kwargs={'pk': self.pk}, request=self._update_ns(request))

    def update_run_mode(self, namespace=None):
        if self.resource_file:
            model_settings = self.resource_file.read_json()
            run_mode = model_settings.get('model_run_mode', '').upper()
            if run_mode in (self.run_mode_choices.V1, self.run_mode_choices.V2):
                self.run_mode = run_mode
                self.save(update_fields=["run_mode"])


class QueueModelAssociation(models.Model):
    model = models.ForeignKey(AnalysisModel, null=False, on_delete=models.CASCADE, related_name='queue_associations')
    queue_name = models.CharField(max_length=255, blank=False, editable=False)

    class Meta:
        unique_together = (('model', 'queue_name'), )

    def __str__(self):
        return f'{self.model}: {self.queue_name}'


@receiver(post_save, sender=AnalysisModel)
def create_default_scaling_options(sender, instance, **kwargs):
    """ Create a default scaling option if none is attached to a model on save
    """
    if instance.chunking_options is None:
        instance.chunking_options = ModelChunkingOptions()
        instance.chunking_options.save()
        instance.save()
    if instance.scaling_options is None:
        instance.scaling_options = ModelScalingOptions()
        instance.scaling_options.save()
        instance.save()


@receiver(post_delete, sender=AnalysisModel)
def delete_connected_files(sender, instance, **kwargs):
    """ Post delete handler to clear out any dangaling analyses files
    """
    files_for_removal = [
        'resource_file',
    ]
    for ref in files_for_removal:
        try:
            file_ref = getattr(instance, ref)
            if file_ref:
                file_ref.delete()
        except ObjectDoesNotExist:
            pass

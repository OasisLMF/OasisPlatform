from backports.tempfile import TemporaryDirectory
from django.apps import apps
from django.test import override_settings
from hypothesis.extra.django import TestCase
from model_bakery import baker

from src.server.oasisapi.files.models import RelatedFile
from src.server.oasisapi.files.v1_api.tests.fakes import fake_related_file


def _models_with_related_files():
    """ Every model that references RelatedFile, mapped to those field names """
    found = {}
    for model in apps.get_models():
        fields = [
            f.name for f in model._meta.get_fields()
            if f.concrete and (f.many_to_one or f.one_to_one) and f.related_model is RelatedFile
        ]
        if fields:
            found[model] = fields
    return found


class DeleteConnectedFiles(TestCase):
    """ Deleting any object must also remove every RelatedFile it references,
        otherwise the file rows and their stored content are orphaned.
        Models / fields are discovered, so new ones are covered automatically.
    """

    def test_models_are_discovered(self):
        labels = {m._meta.label for m in _models_with_related_files()}
        self.assertTrue({
            'analyses.Analysis',
            'analyses.AnalysisTaskStatus',
            'analysis_models.AnalysisModel',
            'analysis_models.SettingsTemplate',
            'data_files.DataFile',
            'portfolios.Portfolio',
        } <= labels)

    def test_delete___every_referenced_related_file_is_removed(self):
        for model, fields in _models_with_related_files().items():
            with self.subTest(model=model._meta.label), \
                    TemporaryDirectory() as d, override_settings(MEDIA_ROOT=d):
                instance = baker.make(model, **{name: fake_related_file() for name in fields})
                file_ids = [getattr(instance, model._meta.get_field(name).attname) for name in fields]

                # AnalysisModel.delete() is a soft delete, which keeps its files by design
                getattr(instance, 'hard_delete', instance.delete)()

                manager = getattr(model, 'all_objects', model._default_manager)
                self.assertFalse(manager.filter(pk=instance.pk).exists())
                self.assertEqual(
                    list(RelatedFile.objects.filter(pk__in=file_ids).values_list('pk', flat=True)), [],
                )

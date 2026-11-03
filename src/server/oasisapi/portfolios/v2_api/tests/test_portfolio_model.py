from backports.tempfile import TemporaryDirectory
from django.test import override_settings
from hypothesis.extra.django import TestCase

from src.server.oasisapi.files.models import RelatedFile
from src.server.oasisapi.files.v1_api.tests.fakes import fake_related_file
from src.server.oasisapi.portfolios.models import Portfolio
from .fakes import fake_portfolio


def _portfolio_file_fields():
    return [
        f.name for f in Portfolio._meta.get_fields()
        if f.many_to_one and f.related_model is RelatedFile
    ]


class DeleteConnectedFiles(TestCase):

    def test_portfolio_delete___every_attached_file_is_removed(self):
        with TemporaryDirectory() as d, override_settings(MEDIA_ROOT=d):
            file_fields = _portfolio_file_fields()
            portfolio = fake_portfolio(**{name: fake_related_file() for name in file_fields})
            file_ids = [getattr(portfolio, f'{name}_id') for name in file_fields]

            portfolio.delete()

            self.assertTrue(file_ids)
            self.assertFalse(RelatedFile.objects.filter(pk__in=file_ids).exists())

from django_webtest import WebTestMixin
from hypothesis.extra.django import TestCase
from src.model_execution_worker.server_tasks import run_oed_validation
from src.server.oasisapi.portfolios.v2_api.tasks import record_validation_output
from django.conf import settings as django_settings
import os
from unittest.mock import MagicMock, patch
from rest_framework.exceptions import ValidationError
from src.server.oasisapi.portfolios.models import Portfolio
from src.server.oasisapi.files.models import RelatedFile
from src.server.oasisapi.auth.tests.fakes import fake_user

TEST_DIR = os.path.dirname(__file__)
ACCOUNTS_VALID = os.path.join(TEST_DIR, "inputs", "accounts.csv")
LOCATION_VALID = os.path.join(TEST_DIR, "inputs", "location.csv")
RI_INFO_VALID = os.path.join(TEST_DIR, "inputs", "ri_info.csv")
RI_SCOPE_VALID = os.path.join(TEST_DIR, "inputs", "ri_scope.csv")
LOCATION_INVALID = os.path.join(TEST_DIR, "inputs", "location_invalid.csv")
CONFIG = django_settings.PORTFOLIO_VALIDATION_CONFIG


class PortfolioValidation(WebTestMixin, TestCase):
    def test_all_exposure__are_valid(self):
        validation_errors = run_oed_validation(LOCATION_VALID, ACCOUNTS_VALID, RI_INFO_VALID, RI_SCOPE_VALID, CONFIG)
        assert validation_errors == []
        fake_portfolio = MagicMock()
        with patch('src.server.oasisapi.portfolios.models.Portfolio.objects.get', return_value=fake_portfolio) as mock_get:
            fake_user(pk=29)
            record_validation_output(validation_errors, 2, 29)
            mock_get.assert_called_once_with(pk=2)
            fake_portfolio.set_portfolio_valid.assert_called_once()

        mock_location = MagicMock(spec=RelatedFile, instance=True)
        mock_location._state = MagicMock(db='default')
        mock_accounts = MagicMock(spec=RelatedFile, instance=True)
        mock_accounts._state = MagicMock(db='default')
        mock_ri_info = MagicMock(spec=RelatedFile, instance=True)
        mock_ri_info._state = MagicMock(db='default')
        mock_ri_scope = MagicMock(spec=RelatedFile, instance=True)
        mock_ri_scope._state = MagicMock(db='default')

        with patch('src.server.oasisapi.portfolios.models.Portfolio.save') as mock_save:
            portfolio = Portfolio()
            portfolio.location_file = mock_location
            portfolio.accounts_file = mock_accounts
            portfolio.reinsurance_info_file = mock_ri_info
            portfolio.reinsurance_scope_file = mock_ri_scope

            portfolio.set_portfolio_valid()
            assert mock_location.oed_validated and mock_location.save.call_count == 1
            assert mock_accounts.oed_validated and mock_accounts.save.call_count == 1
            assert mock_ri_info.oed_validated and mock_ri_info.save.call_count == 1
            assert mock_ri_scope.oed_validated and mock_ri_scope.save.call_count == 1
            assert mock_save.call_count == 1

    def test_location_file__is_valid(self):
        validation_errors = run_oed_validation(LOCATION_VALID, None, None, None, CONFIG)
        assert validation_errors == []
        fake_portfolio = MagicMock()
        with patch('src.server.oasisapi.portfolios.models.Portfolio.objects.get', return_value=fake_portfolio) as mock_get:
            fake_user(pk=29)
            record_validation_output(validation_errors, 3, 29)
            mock_get.assert_called_once_with(pk=3)
            fake_portfolio.set_portfolio_valid.assert_called_once()

        mock_location = MagicMock(spec=RelatedFile, instance=True)
        mock_location._state = MagicMock(db='default')

        with patch('src.server.oasisapi.portfolios.models.Portfolio.save') as mock_save:
            portfolio = Portfolio()
            portfolio.location_file = mock_location

            portfolio.set_portfolio_valid()
            assert mock_location.oed_validated and mock_location.save.call_count == 1
            assert portfolio.accounts_file is None
            assert portfolio.reinsurance_info_file is None
            assert portfolio.reinsurance_scope_file is None
            assert mock_save.call_count == 1

    @patch('src.server.oasisapi.portfolios.models.oed_class_of_businesses__workaround')
    def test_location_file__is_invalid(self, mock_oed_cob_workaround):
        validation_errors = run_oed_validation(LOCATION_INVALID, None, None, None, CONFIG)
        assert isinstance(validation_errors, str)
        with self.assertRaises(ValidationError):
            fake_portfolio = MagicMock()
            fake_user(pk=29)
            with patch('src.server.oasisapi.portfolios.models.Portfolio.objects.get', return_value=fake_portfolio):
                record_validation_output(validation_errors, 5, 29)
                mock_oed_cob_workaround.assert_called_once_with(validation_errors)

    @patch('src.server.oasisapi.portfolios.models.oed_class_of_businesses__workaround')
    def test_account_file__is_invalid(self, mock_oed_cob_workaround):
        validation_errors = run_oed_validation(None, LOCATION_VALID, None, None, CONFIG)
        assert isinstance(validation_errors, str)
        with self.assertRaises(ValidationError):
            fake_portfolio = MagicMock()
            fake_user(pk=29)
            with patch('src.server.oasisapi.portfolios.models.Portfolio.objects.get', return_value=fake_portfolio):
                record_validation_output(validation_errors, 7, 29)
                mock_oed_cob_workaround.assert_called_once_with(validation_errors)

    @patch('src.server.oasisapi.portfolios.models.oed_class_of_businesses__workaround')
    def test_ri_info_file__is_invalid(self, mock_oed_cob_workaround):
        validation_errors = run_oed_validation(None, None, LOCATION_VALID, None, CONFIG)
        assert isinstance(validation_errors, str)
        with self.assertRaises(ValidationError):
            fake_portfolio = MagicMock()
            fake_user(pk=29)
            with patch('src.server.oasisapi.portfolios.models.Portfolio.objects.get', return_value=fake_portfolio):
                record_validation_output(validation_errors, 11, 29)
                mock_oed_cob_workaround.assert_called_once_with(validation_errors)

    @patch('src.server.oasisapi.portfolios.models.oed_class_of_businesses__workaround')
    def test_ri_scope_file__is_invalid(self, mock_oed_cob_workaround):
        validation_errors = run_oed_validation(None, None, None, LOCATION_VALID, CONFIG)
        assert isinstance(validation_errors, str)
        with self.assertRaises(ValidationError):
            fake_portfolio = MagicMock()
            fake_user(pk=29)
            with patch('src.server.oasisapi.portfolios.models.Portfolio.objects.get', return_value=fake_portfolio):
                record_validation_output(validation_errors, 13, 29)
                mock_oed_cob_workaround.assert_called_once_with(validation_errors)

from hypothesis.extra.django import TestCase
from src.model_execution_worker.server_tasks import run_oed_validation, run_exposure_task, run_exposure_transform
from src.server.oasisapi.portfolios.v2_api.tasks import record_validation_output, record_exposure_output, record_transform_output
from src.server.oasisapi.auth.tests.fakes import fake_user
from django.conf import settings as django_settings
import os
from unittest.mock import MagicMock, patch, call
from rest_framework.exceptions import ValidationError
from src.server.oasisapi.portfolios.models import Portfolio
from src.server.oasisapi.files.models import RelatedFile
import pytest
import filecmp

TEST_DIR = os.path.dirname(__file__)
TRANSFORM_DIR = os.path.join(TEST_DIR, "inputs", "test_transform")
ACCOUNTS_VALID = os.path.join(TEST_DIR, "inputs", "accounts.csv")
LOCATION_VALID = os.path.join(TEST_DIR, "inputs", "location.csv")
RI_INFO_VALID = os.path.join(TEST_DIR, "inputs", "ri_info.csv")
RI_SCOPE_VALID = os.path.join(TEST_DIR, "inputs", "ri_scope.csv")
LOCATION_INVALID = os.path.join(TEST_DIR, "inputs", "location_invalid.csv")
CONFIG = django_settings.PORTFOLIO_VALIDATION_CONFIG


class PortfolioValidation(TestCase):
    def test_chain_creation(self):
        mock_portfolio = MagicMock()
        mock_portfolio.pk = 19
        mock_portfolio.validation_status_choices.STARTED = "Started"
        signature_mock = MagicMock()
        mock_portfolio.run_oed_validation_signature.return_value = signature_mock

        Portfolio.run_oed_validation(mock_portfolio)
        mock_portfolio.save.assert_called_once()
        self.assertEqual(mock_portfolio.validation_status, "Started")
        signature_mock.link.assert_called_once_with(record_validation_output.s(19))
        signature_mock.apply_async.assert_called_once_with(queue='oasis-internal-worker', priority=10)

    def test_signature_creation(self):
        mock_portfolio = MagicMock()
        with (patch("src.server.oasisapi.portfolios.models.get_path_or_url", side_effect=[1, 2, 3, 4]),
              patch("src.server.oasisapi.portfolios.models.celery_app_v2.signature", return_value="hello") as mock_signature):
            signature = Portfolio.run_oed_validation_signature(mock_portfolio)
            self.assertEqual(signature, "hello")
            mock_signature.assert_called_once_with(
                'run_oed_validation',
                args=(1, 2, 3, 4, django_settings.PORTFOLIO_VALIDATION_CONFIG),
                priority=10,
                immutable=True,
                queue='oasis-internal-worker'
            )

    def test_all_exposure__are_valid(self):
        validation_errors = run_oed_validation(LOCATION_VALID, ACCOUNTS_VALID, RI_INFO_VALID, RI_SCOPE_VALID, CONFIG)
        assert validation_errors == []
        fake_portfolio = MagicMock()
        with patch('src.server.oasisapi.portfolios.models.Portfolio.objects.get', return_value=fake_portfolio) as mock_get:
            record_validation_output(validation_errors, 2)
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
            record_validation_output(validation_errors, 3)
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
            with patch('src.server.oasisapi.portfolios.models.Portfolio.objects.get', return_value=fake_portfolio):
                record_validation_output(validation_errors, 5)
                mock_oed_cob_workaround.assert_called_once_with(validation_errors)

    @patch('src.server.oasisapi.portfolios.models.oed_class_of_businesses__workaround')
    def test_account_file__is_invalid(self, mock_oed_cob_workaround):
        validation_errors = run_oed_validation(None, LOCATION_VALID, None, None, CONFIG)
        assert isinstance(validation_errors, str)
        with self.assertRaises(ValidationError):
            fake_portfolio = MagicMock()
            with patch('src.server.oasisapi.portfolios.models.Portfolio.objects.get', return_value=fake_portfolio):
                record_validation_output(validation_errors, 7)
                mock_oed_cob_workaround.assert_called_once_with(validation_errors)

    @patch('src.server.oasisapi.portfolios.models.oed_class_of_businesses__workaround')
    def test_ri_info_file__is_invalid(self, mock_oed_cob_workaround):
        validation_errors = run_oed_validation(None, None, LOCATION_VALID, None, CONFIG)
        assert isinstance(validation_errors, str)
        with self.assertRaises(ValidationError):
            fake_portfolio = MagicMock()
            with patch('src.server.oasisapi.portfolios.models.Portfolio.objects.get', return_value=fake_portfolio):
                record_validation_output(validation_errors, 11)
                mock_oed_cob_workaround.assert_called_once_with(validation_errors)

    @patch('src.server.oasisapi.portfolios.models.oed_class_of_businesses__workaround')
    def test_ri_scope_file__is_invalid(self, mock_oed_cob_workaround):
        validation_errors = run_oed_validation(None, None, None, LOCATION_VALID, CONFIG)
        assert isinstance(validation_errors, str)
        with self.assertRaises(ValidationError):
            fake_portfolio = MagicMock()
            with patch('src.server.oasisapi.portfolios.models.Portfolio.objects.get', return_value=fake_portfolio):
                record_validation_output(validation_errors, 13)
                mock_oed_cob_workaround.assert_called_once_with(validation_errors)


class ExposureRun(TestCase):
    def test_chain_creation(self):
        mock_portfolio = MagicMock()
        mock_portfolio.pk = 2
        mock_portfolio.exposure_status_choices.STARTED = "Started"
        signature_mock = MagicMock()
        mock_portfolio.exposure_run_signature.return_value = signature_mock

        Portfolio.exposure_run(mock_portfolio, None, 3)
        mock_portfolio.save.assert_called_once()
        self.assertEqual(mock_portfolio.exposure_status, "Started")
        signature_mock.link.assert_called_once_with(record_exposure_output.s(2, 3))
        signature_mock.apply_async.assert_called_once_with(queue='oasis-internal-worker', priority=10)

    def test_signature_creation(self):
        mock_portfolio = MagicMock()
        mock_portfolio.location_file = True
        with (patch("src.server.oasisapi.portfolios.models.get_path_or_url", side_effect=[1, 2, 3, 4]),
              patch("src.server.oasisapi.portfolios.models.celery_app_v2.signature", return_value="hello") as mock_signature):
            signature = Portfolio.exposure_run_signature(mock_portfolio, "params")
            self.assertEqual(signature, "hello")
            mock_signature.assert_called_once_with(
                'run_exposure_task',
                args=(1, 2, 3, 4, "params"),
                priority=10,
                immutable=True,
                queue='oasis-internal-worker'
            )

    def test_fail_on_no_files(self):
        mock_portfolio = MagicMock()
        mock_portfolio.exposure_status_choices.INSUFFICIENT_DATA = "Insufficient Data"
        mock_portfolio.location_file = None
        mock_portfolio.accounts_file = None
        with pytest.raises(ValidationError):
            Portfolio.exposure_run_signature(mock_portfolio, 1)
        self.assertEqual(mock_portfolio.exposure_status, "Insufficient Data")
        mock_portfolio.save.assert_called_once_with()

    def test_run_exposure_task_success(self):
        def side_effect(text):
            if text == "outfile.csv":
                return "hello"
            elif text == "error.txt":
                return "world"
            raise ValueError()

        with patch('src.model_execution_worker.server_tasks.get_filestore') as mock_filestore:
            dir = os.getcwd()

            mock_store = MagicMock()
            mock_store.put.side_effect = side_effect
            mock_filestore.return_value = mock_store

            effect, result = run_exposure_task(LOCATION_VALID, ACCOUNTS_VALID, RI_INFO_VALID, RI_SCOPE_VALID, {})
            self.assertEqual(result, True)
            self.assertEqual(effect, "hello")
            mock_store.put.assert_called_once_with("outfile.csv")
            mock_store.reset_mock()

            effect, result = run_exposure_task(LOCATION_VALID, ACCOUNTS_VALID, None, None, {})
            self.assertEqual(result, True)
            self.assertEqual(effect, "hello")
            mock_store.put.assert_called_once_with("outfile.csv")
            mock_store.reset_mock()

            effect, result = run_exposure_task(LOCATION_INVALID, ACCOUNTS_VALID, None, None, {})
            self.assertEqual(result, False)
            self.assertEqual(effect, "world")
            mock_store.put.assert_called_once_with("error.txt")

            self.assertEqual(dir, os.getcwd)

    def test_run_exposure_task_output(self):
        def side_effect(arg):
            assert filecmp.cmp("outfile.csv", os.path.join(TEST_DIR, "inputs", "expected_output.csv"))

        with patch('src.model_execution_worker.server_tasks.get_filestore') as mock_filestore:
            mock_store = MagicMock()
            mock_store.put.side_effect = side_effect
            mock_filestore.return_value = mock_store

            run_exposure_task(LOCATION_VALID, ACCOUNTS_VALID, None, None, {})

    def test_record_exposure_output(self):
        mock_portfolio_get = MagicMock()
        initiator = fake_user(pk=29)
        mock_portfolio = MagicMock()
        mock_portfolio_get.return_value = mock_portfolio
        mock_portfolio.exposure_status_choices.ERROR = "ERROR"
        mock_portfolio.exposure_status_choices.RUN_COMPLETED = "RUN_COMPLETED"
        with (patch('src.server.oasisapi.portfolios.models.Portfolio') as mock_portfolio_class,
              patch('src.server.oasisapi.portfolios.v2_api.tasks.RelatedFile') as mock_related_file):
            mock_portfolio_class.objects.get.return_value = mock_portfolio
            record_exposure_output((None, True), 15, 29)
            mock_portfolio.save.assert_called_once_with()
            self.assertEqual(mock_portfolio.exposure_status, "RUN_COMPLETED")
            mock_related_file.objects.create.assert_called_once_with(file=None, content_type='text/csv', creator=initiator,
                                                                     filename='portfolio_15_exposure_run.csv', store_as_filename=True)
            mock_portfolio.reset_mock()

            record_exposure_output((None, False), 28, 29)
            mock_portfolio.save.assert_called_once_with()
            self.assertEqual(mock_portfolio.exposure_status, "ERROR")


class Transform(TestCase):
    def test_chain_creation(self):
        mock_portfolio = MagicMock()
        mock_portfolio.pk = 5
        mock_portfolio.exposure_transform_status_choices.STARTED = "StartedTransform"
        mock_portfolio.validation_status_choices.STARTED = "StartedValidation"

        mock_request = MagicMock()
        mock_request.user.pk = 7
        mock_request.data = {'file_type': 'csv'}

        transform_mock = MagicMock(name="transform_signature")
        validate_mock = MagicMock(name="validate_signature")
        mock_portfolio.exposure_transform_signature.return_value = transform_mock
        mock_portfolio.run_oed_validation_signature.return_value = validate_mock

        chain_mock_return = MagicMock(name="task_chain")
        with patch("src.server.oasisapi.portfolios.models.chain", return_value=chain_mock_return) as chain_mock:
            Portfolio.exposure_transform(mock_portfolio, mock_request)

            self.assertEqual(mock_portfolio.exposure_transform_status, "StartedTransform")
            self.assertEqual(mock_portfolio.validation_status, "StartedValidation")
            mock_portfolio.save.assert_called_once()
            mock_portfolio.exposure_transform_signature.assert_called_once_with()
            mock_portfolio.run_oed_validation_signature.assert_called_once_with()

            transform_output = record_transform_output.s(5, 7, 'csv')
            validate_output = record_validation_output.s(5)
            chain_mock.assert_called_once_with(transform_mock, transform_output, validate_mock, validate_output)

            chain_mock_return.apply_async.assert_called_once_with(queue='oasis-internal-worker', priority=10)

    def test_signature_creation(self):
        mock_portfolio = MagicMock()
        with (patch("src.server.oasisapi.portfolios.models.get_path_or_url", side_effect=[1, 2]),
              patch("src.server.oasisapi.portfolios.models.celery_app_v2.signature", return_value="hello") as mock_signature):
            signature = Portfolio.exposure_transform_signature(mock_portfolio)
            self.assertEqual("hello", signature)
            mock_signature.assert_called_once_with(
                'run_exposure_transform',
                args=(1, 2),
                priority=10,
                immutable=True,
                queue='oasis-internal-worker'
            )

    def test_run_exposure_transform_correct(self):
        input_file = os.path.join(TRANSFORM_DIR, "input.csv")
        mapping_file = os.path.join(TRANSFORM_DIR, "mapping.yml")
        expected_output = os.path.join(TRANSFORM_DIR, "expected_output.csv")
        with patch('src.model_execution_worker.server_tasks.get_filestore') as mock_filestore:
            def side_effect(arg):
                assert filecmp.cmp(os.path.join(TRANSFORM_DIR, "output.csv"), expected_output)
                return "Hello World"

            mock_store = MagicMock()
            mock_store.put.side_effect = side_effect
            mock_filestore.return_value = mock_store
            file = run_exposure_transform(input_file, mapping_file)
            self.assertEqual(file, "Hello World")

    def test_record_transform_output(self):
        portfolio_pk = 10110
        portfolio = MagicMock(pk=10110)
        portfolio.exposure_transform_status_choices.RUN_COMPLETED = "COMPLETED"
        initiator = MagicMock()

        with (patch("src.server.oasisapi.portfolios.models.Portfolio") as mock_Portfolio,
              patch("src.server.oasisapi.portfolios.v2_api.tasks.get_user_model") as mock_get_user,
              patch("src.server.oasisapi.portfolios.v2_api.tasks.RelatedFile") as mock_RelatedFile,
              patch("src.server.oasisapi.portfolios.v2_api.tasks._delete_related_file") as mock_deleted):
            mock_Portfolio.objects.get.return_value = portfolio
            mock_get_user.return_value = initiator
            mock_RelatedFile.objects.create.return_value = 3
            record_transform_output("Filey McFileface", portfolio_pk, 42, "accounts")
            mock_Portfolio.objects.get.assert_called_once_with(pk=portfolio_pk)
            mock_RelatedFile.objects.create.assert_called_once_with(file="Filey McFileface", content_type='text/csv', creator=initiator.objects.get(),
                                                                    filename="portfolio_10110_accounts_file.csv", store_as_filename=True)
            self.assertEqual(portfolio.accounts_file, 3)

            mock_deleted.assert_has_calls([
                call(portfolio, 'transform_file', initiator.objects.get()),
                call(portfolio, 'mapping_file', initiator.objects.get())]
            )
            self.assertEqual(mock_deleted.call_count, 2)
            self.assertEqual(portfolio.exposure_transform_status, "COMPLETED")
            portfolio.save.assert_called_once_with()

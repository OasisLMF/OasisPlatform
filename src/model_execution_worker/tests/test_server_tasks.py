from hypothesis.extra.django import TestCase
from src.model_execution_worker.server_tasks import run_oed_validation, run_exposure_run, run_exposure_transform
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
CURRENCY_SETTINGS = os.path.join(TEST_DIR, "inputs", "currency_config.json")
EXPECTED_ALL_EXPOSURE = os.path.join(TEST_DIR, "inputs", "expected_output_all.csv")
EXPECTED_ALL_USD = os.path.join(TEST_DIR, "inputs", "expected_output_all_usd.csv")
EXPECTED_ACC_LOC_EXPOSURE = os.path.join(TEST_DIR, "inputs", "expected_output_acc_loc.csv")
EXPECTED_ACC_LOC_USD = os.path.join(TEST_DIR, "inputs", "expected_output_acc_loc_usd.csv")


class PortfolioValidation(TestCase):
    def test_chain_creation(self):
        mock_portfolio = MagicMock()
        mock_portfolio.pk = 19
        mock_portfolio.validation_status_choices.STARTED = "Started"
        signature_mock = MagicMock()
        mock_portfolio.run_oed_validation_signature.return_value = signature_mock

        Portfolio.run_oed_validation(mock_portfolio, 22)
        mock_portfolio.save.assert_called_once()
        self.assertEqual(mock_portfolio.validation_status, "Started")
        signature_mock.link.assert_called_once_with(record_validation_output.s(19, 22))
        signature_mock.apply_async.assert_called_once_with(queue='oasis-internal-worker', priority=10)

    def test_signature_creation(self):
        mock_portfolio = MagicMock()
        mock_portfolio.reporting_currency = "Riot Points"
        with (patch("src.server.oasisapi.portfolios.models.get_path_or_url", side_effect=[1, 2, 3, 4, 5]),
              patch("src.server.oasisapi.portfolios.models.celery_app_v2.signature", return_value="hello") as mock_signature):
            signature = Portfolio.run_oed_validation_signature(mock_portfolio)
            self.assertEqual(signature, "hello")
            mock_signature.assert_called_once_with(
                'run_oed_validation',
                args=(1, 2, 3, 4, django_settings.PORTFOLIO_VALIDATION_CONFIG, 5, "Riot Points"),
                priority=10,
                immutable=True,
                queue='oasis-internal-worker'
            )

    def test_all_exposure__are_valid(self):
        validation_errors = run_oed_validation(LOCATION_VALID, ACCOUNTS_VALID, RI_INFO_VALID, RI_SCOPE_VALID, CONFIG, None, None)
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
        validation_errors = run_oed_validation(LOCATION_VALID, None, None, None, CONFIG, None, None)
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
        validation_errors = run_oed_validation(LOCATION_INVALID, None, None, None, CONFIG, None, None)
        assert isinstance(validation_errors, str)
        with self.assertRaises(ValidationError):
            fake_portfolio = MagicMock()
            fake_user(pk=29)
            with (patch('src.server.oasisapi.portfolios.models.Portfolio.objects.get', return_value=fake_portfolio),
                  patch('src.server.oasisapi.portfolios.v2_api.tasks.ContentFile') as mock_file,
                  patch('src.server.oasisapi.portfolios.v2_api.tasks.RelatedFile') as mock_related_file):
                mock_file.return_value = MagicMock()
                record_validation_output(validation_errors, 5, 29)
                mock_file.assert_called_once_with(content=str(validation_errors), name="portfolio_5_errors.txt")
                mock_related_file.assert_called_once_with(file=mock_file, content_type='text/csv', creator=fake_user,
                                                          filename=mock_file.name, store_as_filename=True)
                mock_oed_cob_workaround.assert_called_once_with(validation_errors)
                assert fake_portfolio.validation_status == fake_portfolio.validation_status_choices.ERROR
                fake_portfolio.save.assert_called_once()

    @patch('src.server.oasisapi.portfolios.models.oed_class_of_businesses__workaround')
    def test_account_file__is_invalid(self, mock_oed_cob_workaround):
        validation_errors = run_oed_validation(None, LOCATION_VALID, None, None, CONFIG, None, None)
        assert isinstance(validation_errors, str)
        with self.assertRaises(ValidationError):
            fake_portfolio = MagicMock()
            fake_user(pk=29)
            with (patch('src.server.oasisapi.portfolios.models.Portfolio.objects.get', return_value=fake_portfolio),
                  patch('src.server.oasisapi.portfolios.v2_api.tasks.ContentFile') as mock_file,
                  patch('src.server.oasisapi.portfolios.v2_api.tasks.RelatedFile') as mock_related_file):
                mock_file.return_value = MagicMock()
                record_validation_output(validation_errors, 7, 29)
                mock_file.assert_called_once_with(content=str(validation_errors), name="portfolio_7_errors.txt")
                mock_related_file.assert_called_once_with(file=mock_file, content_type='text/csv', creator=fake_user,
                                                          filename=mock_file.name, store_as_filename=True)
                mock_oed_cob_workaround.assert_called_once_with(validation_errors)
                assert fake_portfolio.validation_status == fake_portfolio.validation_status_choices.ERROR
                fake_portfolio.save.assert_called_once()

    @patch('src.server.oasisapi.portfolios.models.oed_class_of_businesses__workaround')
    def test_ri_info_file__is_invalid(self, mock_oed_cob_workaround):
        validation_errors = run_oed_validation(None, None, LOCATION_VALID, None, CONFIG, None, None)
        assert isinstance(validation_errors, str)
        with self.assertRaises(ValidationError):
            fake_portfolio = MagicMock()
            fake_user(pk=29)
            with (patch('src.server.oasisapi.portfolios.models.Portfolio.objects.get', return_value=fake_portfolio),
                  patch('src.server.oasisapi.portfolios.v2_api.tasks.ContentFile') as mock_file,
                  patch('src.server.oasisapi.portfolios.v2_api.tasks.RelatedFile') as mock_related_file):
                mock_file.return_value = MagicMock()
                record_validation_output(validation_errors, 11, 29)
                mock_file.assert_called_once_with(content=str(validation_errors), name="portfolio_5_errors.txt")
                mock_related_file.assert_called_once_with(file=mock_file, content_type='text/csv', creator=fake_user,
                                                          filename=mock_file.name, store_as_filename=True)
                mock_oed_cob_workaround.assert_called_once_with(validation_errors)
                assert fake_portfolio.validation_status == fake_portfolio.validation_status_choices.ERROR
                fake_portfolio.save.assert_called_once()

    @patch('src.server.oasisapi.portfolios.models.oed_class_of_businesses__workaround')
    def test_ri_scope_file__is_invalid(self, mock_oed_cob_workaround):
        validation_errors = run_oed_validation(None, None, None, LOCATION_VALID, CONFIG, None, None)
        assert isinstance(validation_errors, str)
        with self.assertRaises(ValidationError):
            fake_portfolio = MagicMock()
            fake_user(pk=29)
            with (patch('src.server.oasisapi.portfolios.models.Portfolio.objects.get', return_value=fake_portfolio),
                  patch('src.server.oasisapi.portfolios.v2_api.tasks.ContentFile') as mock_file,
                  patch('src.server.oasisapi.portfolios.v2_api.tasks.RelatedFile') as mock_related_file):
                mock_file.return_value = MagicMock()
                record_validation_output(validation_errors, 13, 29)
                mock_file.assert_called_once_with(content=str(validation_errors), name="portfolio_5_errors.txt")
                mock_related_file.assert_called_once_with(file=mock_file, content_type='text/csv', creator=fake_user,
                                                          filename=mock_file.name, store_as_filename=True)
                mock_oed_cob_workaround.assert_called_once_with(validation_errors)
                assert fake_portfolio.validation_status == fake_portfolio.validation_status_choices.ERROR
                fake_portfolio.save.assert_called_once()

    def test_passes_with_reporting_currency(self):
        validation_errors = run_oed_validation(LOCATION_VALID, None, None, None, CONFIG, None, "USD")
        assert validation_errors == []

    def test_passes_with_currency_conversion(self):
        validation_errors = run_oed_validation(LOCATION_VALID, None, None, None, CONFIG, CURRENCY_SETTINGS, None)
        assert validation_errors == []

    def test_passes_with_valid_json_and_reporting(self):
        validation_errors = run_oed_validation(LOCATION_VALID, None, None, None, CONFIG, CURRENCY_SETTINGS, "USD")
        assert validation_errors == []

    def test_fails_with_invalid_json(self):
        validation_errors = run_oed_validation(LOCATION_VALID, None, None, None, CONFIG, LOCATION_VALID, "USD")
        assert validation_errors != []

    def test_fails_with_invalid_reporting(self):
        validation_errors = run_oed_validation(LOCATION_VALID, None, None, None, CONFIG, CURRENCY_SETTINGS, "Emeralds")
        assert validation_errors != []


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
        mock_portfolio.reporting_currency = "BTC"
        with (patch("src.server.oasisapi.portfolios.models.get_path_or_url", side_effect=[1, 2, 3, 4, 5]),
              patch("src.server.oasisapi.portfolios.models.celery_app_v2.signature", return_value="hello") as mock_signature):
            signature = Portfolio.exposure_run_signature(mock_portfolio, "params")
            self.assertEqual(signature, "hello")
            mock_signature.assert_called_once_with(
                'run_exposure_run',
                args=(1, 2, 3, 4, 5, "BTC", "params"),
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

    def test_run_exposure_run_success(self):
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

            effect, result = run_exposure_run(LOCATION_VALID, ACCOUNTS_VALID, RI_INFO_VALID, RI_SCOPE_VALID, None, None, {})
            self.assertEqual(result, True)
            self.assertEqual(effect, "hello")
            mock_store.put.assert_called_once_with("outfile.csv")
            mock_store.reset_mock()

            effect, result = run_exposure_run(LOCATION_VALID, ACCOUNTS_VALID, None, None, None, None, {})
            self.assertEqual(result, True)
            self.assertEqual(effect, "hello")
            mock_store.put.assert_called_once_with("outfile.csv")
            mock_store.reset_mock()

            effect, result = run_exposure_run(LOCATION_INVALID, ACCOUNTS_VALID, None, None, None, None, {})
            self.assertEqual(result, False)
            self.assertEqual(effect, "world")
            mock_store.put.assert_called_once_with("error.txt")

            self.assertEqual(dir, os.getcwd())

    def test_run_exposure_run_output_no_conversion(self):
        def side_effect(arg):
            assert filecmp.cmp("outfile.csv", EXPECTED_ACC_LOC_EXPOSURE)

        with patch('src.model_execution_worker.server_tasks.get_filestore') as mock_filestore:
            mock_store = MagicMock()
            mock_store.put.side_effect = side_effect
            mock_filestore.return_value = mock_store

            run_exposure_run(LOCATION_VALID, ACCOUNTS_VALID, None, None, None, None, {})

    def test_run_exposure_run_output_with_conversion(self):
        def side_effect(arg):
            assert filecmp.cmp("outfile.csv", EXPECTED_ACC_LOC_USD)

        with patch('src.model_execution_worker.server_tasks.get_filestore') as mock_filestore:
            mock_store = MagicMock()
            mock_store.put.side_effect = side_effect
            mock_filestore.return_value = mock_store

            run_exposure_run(LOCATION_VALID, ACCOUNTS_VALID, None, None, CURRENCY_SETTINGS, "USD", {})

    def test_run_exposure_run_output_ri_rl_no_conversion(self):
        def side_effect(arg):
            with open("outfile.csv", "r") as f:
                print(f.readlines())
            assert filecmp.cmp("outfile.csv", EXPECTED_ALL_EXPOSURE)

        with patch('src.model_execution_worker.server_tasks.get_filestore') as mock_filestore:
            mock_store = MagicMock()
            mock_store.put.side_effect = side_effect
            mock_filestore.return_value = mock_store

            run_exposure_run(LOCATION_VALID, ACCOUNTS_VALID, RI_INFO_VALID, RI_SCOPE_VALID, None, None, {})

    def test_run_exposure_run_output_ri_rl_with_conversion(self):
        def side_effect(arg):
            assert filecmp.cmp("outfile.csv", EXPECTED_ALL_USD)

        with patch('src.model_execution_worker.server_tasks.get_filestore') as mock_filestore:
            mock_store = MagicMock()
            mock_store.put.side_effect = side_effect
            mock_filestore.return_value = mock_store

            run_exposure_run(LOCATION_VALID, ACCOUNTS_VALID, RI_INFO_VALID, RI_SCOPE_VALID, CURRENCY_SETTINGS, "USD", {})

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


@pytest.mark.parametrize(
    "currency_conversion_json, reporting_currency",
    [
        (None, "NONE"),
        (None, "world"),
        (CURRENCY_SETTINGS, "NONE"),
        (CURRENCY_SETTINGS, "world"),
    ]
)
def test_exposure_run_params(currency_conversion_json, reporting_currency):
    allowed_params = {
        'ktools_alloc_rule_il': 1,
        'model_perils_covered': 2,
        'loss_factor': 3,
        'supported_oed_coverage_types': 4,
        'fmpy_sort_output': 5,
        'fmpy_low_memory': 6,
        'extra_summary_cols': 7,
        'ktools_alloc_rule_ri': 8,
        'check_oed': 9,
        'do_disaggregation': 10,
        'verbose': 11
    }
    disallowed_params = {
        'fake_param': 'not allowed',
        'six': 'seven',
        'reporting_currency': 'endpoint_only'
    }
    with (patch("src.model_execution_worker.server_tasks.OasisManager") as fake_manager,
            patch('src.model_execution_worker.server_tasks.get_filestore') as _):
        fake_manager.return_value._params_run_exposure.return_value = {
            'ktools_alloc_rule_il': "a",
            'model_perils_covered': "b",
            'loss_factor': "c",
            'supported_oed_coverage_types': "d",
            'fmpy_sort_output': "e",
            'fmpy_low_memory': "f",
            'extra_summary_cols': "g",
            'ktools_alloc_rule_ri': "h",
            'check_oed': "i",
            'do_disaggregation': "j",
            'verbose': "k",
            'log_level': "l",
            'currency_conversion_json': None,
            'reporting_currency': None
        }
        run_exposure_run(LOCATION_VALID, ACCOUNTS_VALID, None, None, currency_conversion_json, reporting_currency,
                         {**allowed_params, **disallowed_params})
        args, kwargs = fake_manager.return_value.run_exposure.call_args
        assert args == ()
        for k, v in allowed_params.items():
            assert kwargs[k] == v
        for k, v in disallowed_params.items():
            if k in kwargs:
                assert kwargs[k] != v
        assert 'log_level' in kwargs
        assert kwargs['output_file'] == 'outfile.csv'
        assert not kwargs['print_summary'] and kwargs['print_summary'] is not None
        if reporting_currency == "NONE" or currency_conversion_json is None:
            assert kwargs['reporting_currency'] is None
            assert kwargs['currency_conversion_json'] is None
        else:
            assert kwargs['reporting_currency'] == reporting_currency
            assert 'currency_conversion_json' in kwargs


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
            validate_output = record_validation_output.s(5, 7)
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
            file, flag = run_exposure_transform(input_file, mapping_file)
            self.assertEqual(file, "Hello World")
            self.assertEqual(flag, True)

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
            record_transform_output(("Filey McFileface", True), portfolio_pk, 42, "accounts")
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

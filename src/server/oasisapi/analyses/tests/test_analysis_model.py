import string

from backports.tempfile import TemporaryDirectory
from celery import signature
from django.test import override_settings
from django_webtest import WebTestMixin
from hypothesis import given, settings
from hypothesis.extra.django import TestCase
from hypothesis.strategies import text, sampled_from
from mock import patch, PropertyMock, Mock
from rest_framework.exceptions import ValidationError

from ...portfolios.tests.fakes import fake_portfolio
from ...files.tests.fakes import fake_related_file
from ...auth.tests.fakes import fake_user
from ..models import Analysis
from ..tasks import record_run_analysis_result, record_generate_input_result
from .fakes import fake_analysis, FakeAsyncResultFactory

# Override default deadline for all tests to 8s
settings.register_profile("ci", deadline=800.0)
settings.load_profile("ci")


class AnalysisCancel(WebTestMixin, TestCase):
    @given(task_id=text(min_size=1, max_size=10, alphabet=string.ascii_letters))
    def test_state_is_running___revoke_is_called(self, task_id):
        res_factory = FakeAsyncResultFactory(target_task_id=task_id)
        analysis = fake_analysis(status=Analysis.status_choices.RUN_STARTED, run_task_id=task_id)

        with patch('src.server.oasisapi.analyses.models.AsyncResult', res_factory):
            analysis.cancel()

            self.assertEqual(Analysis.status_choices.RUN_CANCELLED, analysis.status)
            self.assertTrue(res_factory.revoke_called)
            self.assertEqual({'signal': 'SIGKILL', 'terminate': True}, res_factory.revoke_kwargs)

    @given(
        status=sampled_from([c for c in Analysis.status_choices._db_values if c not in [
            Analysis.status_choices.RUN_STARTED,
            Analysis.status_choices.RUN_QUEUED,
        ]]),
        task_id=text(min_size=1, max_size=10, alphabet=string.ascii_letters),
    )
    def test_state_is_not_running___validation_error_is_raised_revoke_is_not_called(self, status, task_id):
        res_factory = FakeAsyncResultFactory(target_task_id=task_id)

        with patch('src.server.oasisapi.analyses.models.AsyncResult', res_factory):
            analysis = fake_analysis(status=status, run_task_id=task_id)

            with self.assertRaises(ValidationError) as ex:
                analysis.cancel()

            self.assertEqual({'status': ['Analysis is not running or queued']}, ex.exception.detail)
            self.assertEqual(status, analysis.status)
            self.assertFalse(res_factory.revoke_called)


class AnalysisRun(WebTestMixin, TestCase):
    @given(
        status=sampled_from([
            Analysis.status_choices.READY,
            Analysis.status_choices.RUN_COMPLETED,
            Analysis.status_choices.RUN_CANCELLED,
            Analysis.status_choices.RUN_ERROR
        ]),
        task_id=text(min_size=1, max_size=10, alphabet=string.ascii_letters),
    )
    def test_state_is_ready___run_is_started(self, status, task_id):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                res_factory = FakeAsyncResultFactory(target_task_id=task_id)
                analysis = fake_analysis(status=status, run_task_id=task_id, input_file=fake_related_file(), settings_file=fake_related_file())
                initiator = fake_user()

                sig_res = Mock()
                sig_res.delay.return_value = res_factory(task_id)

                with patch('src.server.oasisapi.analyses.models.Analysis.run_analysis_signature', PropertyMock(return_value=sig_res)):
                    analysis.run(initiator)

                    sig_res.link.assert_called_once_with(record_run_analysis_result.s(analysis.pk, initiator.pk))
                    sig_res.link_error.assert_called_once_with(
                        signature('on_error', args=('record_run_analysis_failure', analysis.pk, initiator.pk), queue=analysis.model.queue_name)
                    )
                    sig_res.delay.assert_called_once_with()

    @given(
        status=sampled_from([
            Analysis.status_choices.NEW,
            Analysis.status_choices.INPUTS_GENERATION_ERROR,
            Analysis.status_choices.INPUTS_GENERATION_CANCELLED,
            Analysis.status_choices.INPUTS_GENERATION_STARTED,
            Analysis.status_choices.RUN_STARTED,
        ]),
        task_id=text(min_size=1, max_size=10, alphabet=string.ascii_letters),
    )
    def test_state_is_running_or_generating_inputs___validation_error_is_raised_revoke_is_not_called(self, status, task_id):
        res_factory = FakeAsyncResultFactory(target_task_id=task_id)
        initiator = fake_user()

        sig_res = Mock()
        with patch('src.server.oasisapi.analyses.models.Analysis.run_analysis_signature', PropertyMock(return_value=sig_res)):
            analysis = fake_analysis(status=status, run_task_id=task_id)

            with self.assertRaises(ValidationError) as ex:
                analysis.run(initiator)

            self.assertEqual({'status': ['Analysis must be in one of the following states [READY, RUN_COMPLETED, RUN_ERROR, RUN_CANCELLED]']}, ex.exception.detail)
            self.assertEqual(status, analysis.status)
            self.assertFalse(res_factory.revoke_called)

    def test_run_analysis_signature_is_correct(self):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                analysis = fake_analysis(input_file=fake_related_file(), settings_file=fake_related_file())

                sig = analysis.run_analysis_signature

                self.assertEqual(sig.task, 'run_analysis')
                self.assertEqual(sig.args, (analysis.id, analysis.input_file.file.name, analysis.settings_file.file.name, []))
                self.assertEqual(sig.options['queue'], analysis.model.queue_name)


class AnalysisCancelInputGeneration(WebTestMixin, TestCase):
    @given(task_id=text(min_size=1, max_size=10, alphabet=string.ascii_letters))
    def test_state_is_generating_inputs___revoke_is_called(self, task_id):
        res_factory = FakeAsyncResultFactory(target_task_id=task_id)
        analysis = fake_analysis(status=Analysis.status_choices.INPUTS_GENERATION_STARTED, generate_inputs_task_id=task_id)

        with patch('src.server.oasisapi.analyses.models.AsyncResult', res_factory):
            analysis.cancel_generate_inputs()

            self.assertEqual(Analysis.status_choices.INPUTS_GENERATION_CANCELLED, analysis.status)
            self.assertTrue(res_factory.revoke_called)
            self.assertEqual({'signal': 'SIGKILL', 'terminate': True}, res_factory.revoke_kwargs)

    @given(
        status=sampled_from([c for c in Analysis.status_choices._db_values if c not in [
            Analysis.status_choices.INPUTS_GENERATION_STARTED,
            Analysis.status_choices.INPUTS_GENERATION_QUEUED
        ]]),
        task_id=text(min_size=1, max_size=10, alphabet=string.ascii_letters),
    )
    def test_state_is_not_generating_inputs___validation_error_is_raised_revoke_is_not_called(self, status, task_id):
        res_factory = FakeAsyncResultFactory(target_task_id=task_id)

        with patch('src.server.oasisapi.analyses.models.AsyncResult', res_factory):
            analysis = fake_analysis(status=status, generate_inputs_task_id=task_id)

            with self.assertRaises(ValidationError) as ex:
                analysis.cancel_generate_inputs()

            self.assertEqual({'status': ['Analysis input generation is not running or queued']}, ex.exception.detail)
            self.assertEqual(status, analysis.status)
            self.assertFalse(res_factory.revoke_called)


class AnalysisGenerateInputs(WebTestMixin, TestCase):
    @given(
        status=sampled_from([c for c in Analysis.status_choices._db_values if c not in [
            Analysis.status_choices.INPUTS_GENERATION_QUEUED, 
            Analysis.status_choices.INPUTS_GENERATION_STARTED, 
            Analysis.status_choices.RUN_QUEUED,
            Analysis.status_choices.RUN_STARTED
        ]]),
        task_id=text(min_size=1, max_size=10, alphabet=string.ascii_letters),
    )
    def test_state_is_not_running___run_is_started(self, status, task_id):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                res_factory = FakeAsyncResultFactory(target_task_id=task_id)
                analysis = fake_analysis(status=status, run_task_id=task_id, portfolio=fake_portfolio(location_file=fake_related_file()))
                initiator = fake_user()

                sig_res = Mock()
                sig_res.delay.return_value = res_factory(task_id)

                with patch('src.server.oasisapi.analyses.models.Analysis.generate_input_signature', PropertyMock(return_value=sig_res)):
                    analysis.generate_inputs(initiator)

                    sig_res.link.assert_called_once_with(record_generate_input_result.s(analysis.pk, initiator.pk))
                    sig_res.link_error.assert_called_once_with(
                        signature('on_error', args=('record_generate_input_failure', analysis.pk, initiator.pk), queue=analysis.model.queue_name)
                    )
                    sig_res.delay.assert_called_once_with()

    @given(
        status=sampled_from([
            Analysis.status_choices.INPUTS_GENERATION_STARTED,
            Analysis.status_choices.RUN_STARTED,
        ]),
        task_id=text(min_size=1, max_size=10, alphabet=string.ascii_letters),
    )
    def test_state_is_running_or_generating_inputs___validation_error_is_raised_revoke_is_not_called(self, status, task_id):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                res_factory = FakeAsyncResultFactory(target_task_id=task_id)
                initiator = fake_user()

                sig_res = Mock()
                with patch('src.server.oasisapi.analyses.models.Analysis.generate_input_signature', PropertyMock(return_value=sig_res)):
                    analysis = fake_analysis(status=status, run_task_id=task_id, portfolio=fake_portfolio(location_file=fake_related_file()))

                    with self.assertRaises(ValidationError) as ex:
                        analysis.generate_inputs(initiator)

                    self.assertEqual({'status': [
                        'Analysis status must be one of [NEW, INPUTS_GENERATION_ERROR, INPUTS_GENERATION_CANCELLED, READY, RUN_COMPLETED, RUN_CANCELLED, RUN_ERROR]'
                    ]}, ex.exception.detail)
                    self.assertEqual(status, analysis.status)
                    self.assertFalse(res_factory.revoke_called)

    @given(task_id=text(min_size=1, max_size=10, alphabet=string.ascii_letters))
    def test_portfolio_has_no_location_file___validation_error_is_raised_revoke_is_not_called(self, task_id):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                res_factory = FakeAsyncResultFactory(target_task_id=task_id)
                initiator = fake_user()

                sig_res = Mock()
                with patch('src.server.oasisapi.analyses.models.Analysis.generate_input_signature', PropertyMock(return_value=sig_res)):
                    analysis = fake_analysis(status=Analysis.status_choices.NEW, run_task_id=task_id)

                    with self.assertRaises(ValidationError) as ex:
                        analysis.generate_inputs(initiator)

                    self.assertEqual({'portfolio': ['"location_file" must not be null']}, ex.exception.detail)

                    self.assertEqual(Analysis.status_choices.NEW, analysis.status)
                    self.assertFalse(res_factory.revoke_called)

    def test_generate_input_signature_is_correct(self):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                analysis = fake_analysis(portfolio=fake_portfolio(location_file=fake_related_file()))

                sig = analysis.generate_input_signature

                self.assertEqual(sig.task, 'generate_input')
                self.assertEqual(sig.args, (analysis.id, analysis.portfolio.location_file.file.name, None, None, None, None, []))
                self.assertEqual(sig.options['queue'], analysis.model.queue_name)

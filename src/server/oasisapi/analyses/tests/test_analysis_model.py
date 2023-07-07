import string

from .fakes import fake_analysis, FakeAsyncResultFactory
# from .fakes import fake_analysis_task_status
from backports.tempfile import TemporaryDirectory
from django.test import override_settings
# from django.utils.timezone import now, utc
from django_webtest import WebTestMixin
# from freezegun import freeze_time
from hypothesis import given, settings
from hypothesis.extra.django import TestCase
from hypothesis.strategies import text, sampled_from
# from hypothesis.strategies import datetimes, just
from mock import patch, PropertyMock, Mock
from rest_framework.exceptions import ValidationError
from unittest.mock import ANY, MagicMock

from src.conf import iniconf
from ...portfolios.tests.fakes import fake_portfolio
from ...files.tests.fakes import fake_related_file
from ...auth.tests.fakes import fake_user
# from ..models import AnalysisTaskStatus
from ..models import Analysis

# Override default deadline for all tests to 8s
settings.register_profile("ci", deadline=800.0)
settings.load_profile("ci")


class CancelAnalysisTask(WebTestMixin, TestCase):
    pass

    # TODO: fix test - disabled due to failure
    # @given(orig_status=sampled_from([
    #     Analysis.status_choices.INPUTS_GENERATION_QUEUED,
    #     Analysis.status_choices.INPUTS_GENERATION_STARTED,
    # ]))
    # def test_analysis_is_running_input_generation___analysis_status_is_updated_and_running_children_are_cancelled(self, orig_status):
    #     _now = now()
    #     async_result_mock = Mock()
    #
    #     with freeze_time(_now), \
    #          patch('src.server.oasisapi.analyses.models.AsyncResult', return_value=async_result_mock) as async_res_mock:
    #         analysis = fake_analysis(status=orig_status)
    #
    #         complete = fake_analysis_task_status(analysis=analysis, status=AnalysisTaskStatus.status_choices.COMPLETED)
    #         error = fake_analysis_task_status(analysis=analysis, status=AnalysisTaskStatus.status_choices.ERROR)
    #         queued = fake_analysis_task_status(analysis=analysis, status=AnalysisTaskStatus.status_choices.QUEUED)
    #         started = fake_analysis_task_status(analysis=analysis, status=AnalysisTaskStatus.status_choices.STARTED)
    #
    #         analysis.cancel()
    #
    #         analysis.refresh_from_db()
    #         complete.refresh_from_db()
    #         error.refresh_from_db()
    #         queued.refresh_from_db()
    #         started.refresh_from_db()
    #
    #         self.assertEqual(analysis.status, Analysis.status_choices.INPUTS_GENERATION_CANCELLED)
    #         self.assertEqual(analysis.task_finished, _now)
    #
    #         self.assertEqual(complete.status, AnalysisTaskStatus.status_choices.COMPLETED)
    #         self.assertEqual(error.status, AnalysisTaskStatus.status_choices.ERROR)
    #         self.assertEqual(queued.status, AnalysisTaskStatus.status_choices.CANCELLED)
    #         self.assertEqual(started.status, AnalysisTaskStatus.status_choices.CANCELLED)
    #
    #         self.assertEqual(async_res_mock.call_count, 2)
    #         self.assertEqual(async_result_mock.revoke.call_count, 2)
    #         async_res_mock.assert_any_call(queued.task_id)
    #         async_res_mock.assert_any_call(started.task_id)

    # TODO: fix test - disabled due to failure
    # @given(orig_status=sampled_from([
    #     Analysis.status_choices.RUN_QUEUED,
    #     Analysis.status_choices.RUN_STARTED,
    # ]))
    # def test_analysis_is_running_loss_generation___analysis_status_is_updated_and_running_children_are_cancelled(self, orig_status):
    #     _now = now()
    #     async_result_mock = Mock()
    #
    #     with freeze_time(_now), \
    #          patch('src.server.oasisapi.analyses.models.AsyncResult', return_value=async_result_mock) as async_res_mock:
    #         analysis = fake_analysis(status=orig_status)
    #
    #         complete = fake_analysis_task_status(analysis=analysis, status=AnalysisTaskStatus.status_choices.COMPLETED)
    #         error = fake_analysis_task_status(analysis=analysis, status=AnalysisTaskStatus.status_choices.ERROR)
    #         queued = fake_analysis_task_status(analysis=analysis, status=AnalysisTaskStatus.status_choices.QUEUED)
    #         started = fake_analysis_task_status(analysis=analysis, status=AnalysisTaskStatus.status_choices.STARTED)
    #
    #         analysis.cancel()
    #
    #         analysis.refresh_from_db()
    #         complete.refresh_from_db()
    #         error.refresh_from_db()
    #         queued.refresh_from_db()
    #         started.refresh_from_db()
    #
    #         self.assertEqual(analysis.status, Analysis.status_choices.RUN_CANCELLED)
    #         self.assertEqual(analysis.task_finished, _now)
    #
    #         self.assertEqual(complete.status, AnalysisTaskStatus.status_choices.COMPLETED)
    #         self.assertEqual(error.status, AnalysisTaskStatus.status_choices.ERROR)
    #         self.assertEqual(queued.status, AnalysisTaskStatus.status_choices.CANCELLED)
    #         self.assertEqual(started.status, AnalysisTaskStatus.status_choices.CANCELLED)
    #
    #         self.assertEqual(async_res_mock.call_count, 2)
    #         self.assertEqual(async_result_mock.revoke.call_count, 2)
    #         async_res_mock.assert_any_call(queued.task_id)
    #         async_res_mock.assert_any_call(started.task_id)

    # TODO: fix test - disabled due to failure
    # @given(
    #     end_time=datetimes(timezones=just(utc)),
    #     orig_status=sampled_from([
    #         Analysis.status_choices.INPUTS_GENERATION_ERROR,
    #         Analysis.status_choices.INPUTS_GENERATION_CANCELLED,
    #         Analysis.status_choices.RUN_ERROR,
    #         Analysis.status_choices.RUN_CANCELLED,
    #     ])
    # )
    # def test_analysis_already_in_and_ended_state___analysis_status_is_unchanged(self, orig_status, end_time):
    #     _now = now()
    #     async_result_mock = Mock()
    #
    #     with freeze_time(_now), \
    #          patch('src.server.oasisapi.analyses.models.AsyncResult', return_value=async_result_mock) as async_res_mock:
    #         analysis = fake_analysis(status=orig_status, task_finished=end_time)
    #
    #         complete = fake_analysis_task_status(analysis=analysis, status=AnalysisTaskStatus.status_choices.COMPLETED)
    #         error = fake_analysis_task_status(analysis=analysis, status=AnalysisTaskStatus.status_choices.ERROR)
    #         queued = fake_analysis_task_status(analysis=analysis, status=AnalysisTaskStatus.status_choices.QUEUED)
    #         started = fake_analysis_task_status(analysis=analysis, status=AnalysisTaskStatus.status_choices.STARTED)
    #
    #         analysis.cancel()
    #
    #         analysis.refresh_from_db()
    #         complete.refresh_from_db()
    #         error.refresh_from_db()
    #         queued.refresh_from_db()
    #         started.refresh_from_db()
    #
    #         self.assertEqual(analysis.status, orig_status)
    #         self.assertEqual(analysis.task_finished, end_time)
    #
    #         self.assertEqual(complete.status, AnalysisTaskStatus.status_choices.COMPLETED)
    #         self.assertEqual(error.status, AnalysisTaskStatus.status_choices.ERROR)
    #         self.assertEqual(queued.status, AnalysisTaskStatus.status_choices.CANCELLED)
    #         self.assertEqual(started.status, AnalysisTaskStatus.status_choices.CANCELLED)
    #
    #         self.assertEqual(async_res_mock.call_count, 2)
    #         self.assertEqual(async_result_mock.revoke.call_count, 2)
    #         async_res_mock.assert_any_call(queued.task_id)
    #         async_res_mock.assert_any_call(started.task_id)


class AnalysisGenerateAndRun(WebTestMixin, TestCase):
    @given(
        status=sampled_from([
            Analysis.status_choices.READY,
            Analysis.status_choices.RUN_COMPLETED,
            Analysis.status_choices.RUN_CANCELLED,
            Analysis.status_choices.RUN_ERROR
        ]),
        task_gen_id=text(min_size=1, max_size=10, alphabet=string.ascii_letters),
        task_run_id=text(min_size=1, max_size=10, alphabet=string.ascii_letters),
    )
    def test_state_is_ready___run_is_started(self, status, task_gen_id, task_run_id):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                initiator = fake_user()
                analysis = fake_analysis(
                    status=status,
                    run_task_id=task_run_id,
                    portfolio=fake_portfolio(location_file=fake_related_file()),
                    settings_file=fake_related_file())

                task_gen = Mock()
                task_run = Mock()
                task_chain = Mock()

                res_factory_gen = FakeAsyncResultFactory(target_task_id=task_gen_id)
                res_factory_run = FakeAsyncResultFactory(target_task_id=task_run_id)

                task_gen.apply_async.return_value = res_factory_gen(task_gen_id)
                task_run.apply_async.return_value = res_factory_run(task_run_id)
                task_chain.apply_async.return_value = res_factory_run(task_run_id)

                with (
                    patch('src.server.oasisapi.analyses.models.Analysis.generate_input_signature', PropertyMock(return_value=task_gen)),
                    patch('src.server.oasisapi.analyses.models.Analysis.run_analysis_chain_signature', PropertyMock(return_value=task_run)),
                    patch('src.server.oasisapi.analyses.models.chain', PropertyMock(return_value=task_chain)) as task_chain,
                ):
                    analysis.generate_and_run(initiator, validate_celery=False)

                    task_gen.link.assert_called_with(record_generate_input_result.s(analysis.pk, initiator.pk))
                    task_gen.link_error.assert_called_with(
                        signature('on_error', args=('record_generate_input_failure', analysis.pk, initiator.pk), queue=analysis.model.queue_name))

                    task_run.link.assert_called_once_with(record_run_analysis_result.s(analysis.pk, initiator.pk))
                    task_run.link_error.assert_called_with(
                        signature('on_error', args=('record_run_analysis_failure', analysis.pk, initiator.pk), queue=analysis.model.queue_name))

                    task_chain.assert_called_once_with(task_gen, task_run)

    @given(
        status=sampled_from([
            Analysis.status_choices.INPUTS_GENERATION_QUEUED,
            Analysis.status_choices.INPUTS_GENERATION_STARTED,
            Analysis.status_choices.RUN_QUEUED,
            Analysis.status_choices.RUN_STARTED,
        ]),
        task_id=text(min_size=1, max_size=10, alphabet=string.ascii_letters),
    )
    def test_state_is_running_or_generating_inputs___validation_error_is_raised_revoke_is_not_called(self, status, task_id):
        res_factory = FakeAsyncResultFactory(target_task_id=task_id)
        initiator = fake_user()

        task_chain = Mock()
        task_chain.delay.return_value = res_factory(task_id)

        with (
                patch('src.server.oasisapi.analyses.models.chain', PropertyMock(return_value=task_chain)) as task_chain):
            analysis = fake_analysis(status=status, run_task_id=task_id)

            with self.assertRaises(ValidationError) as ex:
                analysis.generate_and_run(initiator, validate_celery=False)

            self.maxDiff = None
            self.assertEqual({
                'portfolio': ['"location_file" must not be null'],
                'settings_file': ['Must not be null'],
                'status': ['Analysis status must be one of [NEW, INPUTS_GENERATION_ERROR, INPUTS_GENERATION_CANCELLED, READY, RUN_COMPLETED, RUN_CANCELLED, RUN_ERROR]'],
            }, ex.exception.detail)

            self.assertEqual(status, analysis.status)
            self.assertFalse(res_factory.revoke_called)

    @given(
        status=sampled_from([
            Analysis.status_choices.READY,
            Analysis.status_choices.RUN_COMPLETED,
            Analysis.status_choices.RUN_CANCELLED,
            Analysis.status_choices.RUN_ERROR
        ]),
        task_id=text(min_size=1, max_size=10, alphabet=string.ascii_letters),
    )
    def test_worker_not_supported__validation_error_is_raised_revoke_is_not_called(self, status, task_id):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                initiator = fake_user()
                res_factory = FakeAsyncResultFactory(target_task_id=task_id)
                analysis = fake_analysis(
                    status=status,
                    run_task_id=task_id,
                    portfolio=fake_portfolio(location_file=fake_related_file()),
                    settings_file=fake_related_file())

                task_chain = Mock()
                task_chain.delay.return_value = res_factory(task_id)

                task_celery_support = Mock()
                task_celery_support.wait = MagicMock(return_value=(False, "celery error message"))

                with (
                    patch('src.server.oasisapi.analyses.models.chain', PropertyMock(return_value=task_chain)) as task_chain,
                    patch('src.server.oasisapi.analyses.models.check_model_task_support.delay', PropertyMock(return_value=task_celery_support))
                ):

                    with self.assertRaises(ValidationError) as ex:
                        analysis.generate_and_run(initiator, validate_celery=True)

                    self.assertEqual([k for k in ex.exception.detail], ['worker'])
                    self.assertEqual(
                        str(ex.exception.detail.get('worker', '')),
                        "Celery task 'generate_and_run' not supported in worker version None"
                    )
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
                # res_factory = FakeAsyncResultFactory(target_task_id=task_id)
                analysis = fake_analysis(status=status, run_task_id=task_id, input_file=fake_related_file(), settings_file=fake_related_file())
                initiator = fake_user()

                task_obj = type('', (), {})()
                task_obj.id = task_id
                mock_task = MagicMock(return_value=task_obj)

                with patch('src.server.oasisapi.analyses.models.celery_app.send_task', new=mock_task):
                    analysis.run(initiator)
                    mock_task.assert_called_once_with('start_loss_generation_task', (analysis.pk, initiator.pk, 1),
                                                      {}, queue='celery', link_error=ANY, priority=4)

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

            self.assertEqual(
                {'status': ['Analysis must be in one of the following states [READY, RUN_COMPLETED, RUN_ERROR, RUN_CANCELLED]']}, ex.exception.detail)
            self.assertEqual(status, analysis.status)
            self.assertFalse(res_factory.revoke_called)

    def test_run_analysis_signature_is_correct(self):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                analysis = fake_analysis(input_file=fake_related_file(), settings_file=fake_related_file())

                sig = analysis.run_analysis_signature

                self.assertEqual(sig.task, 'start_loss_generation_task')
                self.assertEqual(
                    sig.options['queue'],
                    iniconf.settings.get('worker', 'LOSSES_GENERATION_CONTROLLER_QUEUE', fallback='celery')
                )


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
                analysis = fake_analysis(status=status, run_task_id=task_id, portfolio=fake_portfolio(location_file=fake_related_file()))
                initiator = fake_user()

                task_obj = type('', (), {})()
                task_obj.id = task_id
                mock_task = MagicMock(return_value=task_obj)
                with patch('src.server.oasisapi.analyses.models.celery_app.send_task', new=mock_task):
                    analysis.generate_inputs(initiator)
                    mock_task.assert_called_once_with('start_input_generation_task', (analysis.pk, initiator.pk,
                                                      4), {}, queue='celery', link_error=ANY, priority=4)

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

                self.assertEqual(sig.task, 'start_input_generation_task')
                self.assertEqual(
                    sig.options['queue'],
                    iniconf.settings.get('worker', 'INPUT_GENERATION_CONTROLLER_QUEUE', fallback='celery')
                )

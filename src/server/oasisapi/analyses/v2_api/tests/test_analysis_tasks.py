import datetime
import os
import string
from unittest.mock import Mock, patch
from uuid import uuid4

from backports.tempfile import TemporaryDirectory
from django.test import override_settings
from django.utils.timezone import now
from freezegun import freeze_time
from hypothesis import given
from hypothesis import settings
from hypothesis.extra.django import TestCase
from hypothesis.strategies import text, sampled_from
from pathlib2 import Path

from .fakes import fake_analysis, fake_analysis_task_status
from ...models import Analysis, AnalysisTaskStatus
from ....auth.tests.fakes import fake_user
from ....files.models import RelatedFile
from ....files.v2_api.tests.fakes import fake_related_file
from ...v2_api.tasks import (
    chord_error_callback, handle_task_failure, record_losses_files, record_sub_task_failure, record_sub_task_success,
    record_sub_task_start, start_input_and_loss_generation_task, start_loss_generation_task, start_input_generation_task,
    subtask_error_log, store_lookup_errors_file,
)
from ...v1_api.tasks import (
    record_run_analysis_result, generate_input_success, record_generate_input_failure, record_run_analysis_failure
)

settings.register_profile("ci", deadline=800.0)
settings.load_profile("ci")


class RunAnalysisSuccess(TestCase):
    @given(
        output_location=text(min_size=1, max_size=10, alphabet=string.ascii_letters),
        log_location=text(min_size=1, max_size=10, alphabet=string.ascii_letters),
        traceback_location=text(min_size=1, max_size=10, alphabet=string.ascii_letters),
        return_code=sampled_from([0, 1])
    )
    def test_output_file_and_status_are_updated(self, output_location, log_location, traceback_location, return_code):
        expected_status = Analysis.status_choices.RUN_COMPLETED if return_code == 0 else Analysis.status_choices.RUN_ERROR

        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                initiator = fake_user()
                analysis = fake_analysis()
                Path(d, output_location).touch()
                Path(d, log_location).touch()
                Path(d, traceback_location).touch()

                record_run_analysis_result(
                    (
                        os.path.join(d, output_location),
                        os.path.join(d, traceback_location),
                        os.path.join(d, log_location),
                        return_code,
                    ),
                    analysis.pk,
                    initiator.pk,
                )

                analysis.refresh_from_db()

                if return_code == 0:
                    self.assertEqual(analysis.output_file.filename, f'analysis_{analysis.pk}_output.tar.gz')
                    self.assertEqual(analysis.output_file.content_type, 'application/gzip')
                    self.assertEqual(analysis.output_file.creator, initiator)
                else:
                    self.assertEqual(analysis.output_file, None)

                self.assertEqual(analysis.run_log_file.filename, f'analysis_{analysis.pk}_logs.tar.gz')
                self.assertEqual(analysis.run_log_file.content_type, 'application/gzip')
                self.assertEqual(analysis.run_log_file.creator, initiator)

                self.assertEqual(analysis.run_traceback_file.filename, f'analysis_{analysis.pk}_run_traceback.txt')
                self.assertEqual(analysis.run_traceback_file.content_type, 'text/plain')
                self.assertEqual(analysis.run_traceback_file.creator, initiator)

                self.assertEqual(analysis.status, expected_status)


class RunAnalysisFailure(TestCase):
    @given(traceback=text(min_size=1, max_size=10, alphabet=string.ascii_letters))
    def test_output_tracebackfile__and_status_are_updated(self, traceback):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                initiator = fake_user()
                analysis = fake_analysis()

                record_run_analysis_failure(analysis.pk, initiator.pk, traceback)

                analysis.refresh_from_db()

                self.assertEqual(analysis.run_traceback_file.file.read(), traceback.encode())
                self.assertEqual(analysis.run_traceback_file.content_type, 'text/plain')
                self.assertEqual(analysis.run_traceback_file.creator, initiator)
                self.assertEqual(analysis.status, analysis.status_choices.RUN_ERROR)
                self.assertTrue(isinstance(analysis.task_finished, datetime.datetime))


class GenerateInputsSuccess(TestCase):
    @given(
        input_location=text(min_size=1, max_size=10, alphabet=string.ascii_letters),
        lookup_error_fp=text(min_size=1, max_size=10, alphabet=string.ascii_letters),
        lookup_success_fp=text(min_size=1, max_size=10, alphabet=string.ascii_letters),
        lookup_validation_fp=text(min_size=1, max_size=10, alphabet=string.ascii_letters),
        summary_levels_fp=text(min_size=1, max_size=10, alphabet=string.ascii_letters),
    )
    def test_input_file_lookup_files_and_status_are_updated(self, input_location, lookup_error_fp,
                                                            lookup_success_fp, lookup_validation_fp, summary_levels_fp):
        with (TemporaryDirectory() as d,
              override_settings(MEDIA_ROOT=d)):
            Path(d, input_location).touch()
            Path(d, lookup_error_fp).touch()
            Path(d, lookup_success_fp).touch()
            Path(d, lookup_validation_fp).touch()
            Path(d, summary_levels_fp).touch()

            initiator = fake_user()
            analysis = fake_analysis()
            res = (input_location, lookup_error_fp, lookup_success_fp, lookup_validation_fp, summary_levels_fp)
            generate_input_success(res, analysis.pk, initiator.pk)
            analysis.refresh_from_db()

            self.assertEqual(analysis.input_file.filename, input_location)
            self.assertEqual(analysis.input_file.content_type, 'application/gzip')
            self.assertEqual(analysis.input_file.creator, initiator)

            self.assertEqual(analysis.lookup_errors_file.filename, 'keys-errors.csv')
            self.assertEqual(analysis.lookup_errors_file.content_type, 'text/csv')
            self.assertEqual(analysis.lookup_errors_file.creator, initiator)

            self.assertEqual(analysis.lookup_success_file.filename, 'gul_summary_map.csv')
            self.assertEqual(analysis.lookup_success_file.content_type, 'text/csv')
            self.assertEqual(analysis.lookup_success_file.creator, initiator)

            self.assertEqual(analysis.lookup_validation_file.filename, 'exposure_summary_report.json')
            self.assertEqual(analysis.lookup_validation_file.content_type, 'application/json')
            self.assertEqual(analysis.lookup_validation_file.creator, initiator)

            self.assertEqual(analysis.summary_levels_file.filename, 'exposure_summary_levels.json')
            self.assertEqual(analysis.summary_levels_file.content_type, 'application/json')
            self.assertEqual(analysis.summary_levels_file.creator, initiator)

            self.assertEqual(analysis.status, analysis.status_choices.READY)
            self.assertTrue(isinstance(analysis.task_finished, datetime.datetime))


class GenerateInputsFailure(TestCase):
    @given(traceback=text(min_size=1, max_size=10, alphabet=string.ascii_letters))
    def test_input_generation_traceback_file_and_status_are_updated(self, traceback):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                initiator = fake_user()
                analysis = fake_analysis()

                record_generate_input_failure(analysis.pk, initiator.pk, traceback)

                analysis.refresh_from_db()

                self.assertEqual(analysis.input_generation_traceback_file.file.read(), traceback.encode())
                self.assertEqual(analysis.input_generation_traceback_file.content_type, 'text/plain')
                self.assertEqual(analysis.input_generation_traceback_file.creator, initiator)
                self.assertEqual(analysis.status, analysis.status_choices.INPUTS_GENERATION_ERROR)
                self.assertTrue(isinstance(analysis.task_finished, datetime.datetime))


class StartInputGenerationTask(TestCase):
    def test_generate_inputs_is_called_on_task_controller(self):
        analysis = fake_analysis()
        initiator = fake_user()

        task_controller = Mock()
        with patch('src.server.oasisapi.analyses.v2_api.tasks.get_analysis_task_controller', return_value=task_controller):
            start_input_generation_task(analysis.pk, initiator.pk, 37)

        task_controller.generate_inputs.assert_called_once_with(analysis, initiator, 37)


class StartInputAndLossGenerationTask(TestCase):
    def test_generate_input_and_loss_called_on_task_controller(self):
        analysis = fake_analysis()
        initiator = fake_user()

        task_controller = Mock()
        with patch('src.server.oasisapi.analyses.v2_api.tasks.get_analysis_task_controller', return_value=task_controller):
            start_input_and_loss_generation_task(analysis.pk, initiator.pk, 10, 39)

        task_controller.generate_input_and_losses.assert_called_once_with(analysis, initiator, 10, 39)


class StartLossGenerationTask(TestCase):
    def test_generate_losses_is_called_on_task_controller(self):
        analysis = fake_analysis()
        initiator = fake_user()

        task_controller = Mock()
        with patch('src.server.oasisapi.analyses.v2_api.tasks.get_analysis_task_controller', return_value=task_controller):
            start_loss_generation_task(analysis.pk, initiator.pk, 41)

        task_controller.generate_losses.assert_called_once_with(analysis, initiator, 41)


class RecordLossesFiles(TestCase):
    """ generate_and_run adds input files (occurrence.bin) during the loss run, after
        record_input_files has already stored the inputs tarball.
    """

    def _record_losses_files(self, result):
        initiator = fake_user()
        analysis = fake_analysis(input_file=fake_related_file())
        original_input_file = analysis.input_file
        stored = fake_related_file()
        with patch('src.server.oasisapi.analyses.v2_api.tasks.store_file', return_value=stored) as store_file_mock, \
                patch('src.server.oasisapi.analyses.v2_api.tasks.record_sub_task_start'):
            record_losses_files(result, analysis_id=analysis.pk, initiator_id=initiator.pk, slug='record-losses-files')
        analysis.refresh_from_db()
        return analysis, original_input_file, stored, store_file_mock, initiator

    def test_updated_input_location___input_file_is_replaced(self):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                analysis, _, stored, store_file_mock, initiator = self._record_losses_files(
                    {'output_location': 'output.tar.gz', 'updated_input_location': 'fresh-inputs.tar.gz'})

                store_file_mock.assert_any_call('fresh-inputs.tar.gz', 'application/gzip', initiator,
                                                filename=f'analysis_{analysis.pk}_inputs.tar.gz')
                self.assertEqual(analysis.input_file, stored)

    def test_updated_input_location___replaced_input_file_is_deleted(self):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                analysis, original_input_file, _, _, _ = self._record_losses_files(
                    {'output_location': 'output.tar.gz', 'updated_input_location': 'fresh-inputs.tar.gz'})

                self.assertTrue(Analysis.objects.filter(pk=analysis.pk).exists())
                self.assertFalse(RelatedFile.objects.filter(pk=original_input_file.pk).exists())

    def test_replaced_input_file_has_a_different_name___its_stored_file_is_deleted(self):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                initiator = fake_user()
                analysis = fake_analysis(input_file=fake_related_file())
                old_path = analysis.input_file.file.path
                with self.captureOnCommitCallbacks(execute=True), \
                        patch('src.server.oasisapi.analyses.v2_api.tasks.store_file', side_effect=lambda *a, **kw: fake_related_file()), \
                        patch('src.server.oasisapi.analyses.v2_api.tasks.record_sub_task_start'):
                    record_losses_files({'output_location': 'output.tar.gz', 'updated_input_location': 'fresh-inputs.tar.gz'},
                                        analysis_id=analysis.pk, initiator_id=initiator.pk, slug='record-losses-files')

                self.assertFalse(os.path.exists(old_path))

    def test_replaced_input_file_has_the_same_storage_name___new_file_is_kept(self):
        """ record_input_files and record_losses_files both store 'analysis_<id>_inputs.tar.gz', so on
            S3/Azure the new copy overwrites the old object. Deleting the old row must not delete that object.
        """
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                initiator = fake_user()
                name = 'analysis_inputs.tar.gz'
                Path(d, name).write_bytes(b'new inputs')
                old_input_file = RelatedFile.objects.create(file=name, filename=name, content_type='application/gzip', creator=initiator)
                analysis = fake_analysis(input_file=old_input_file)

                def overwrite_in_place(*args, **kwargs):
                    return RelatedFile.objects.create(file=name, filename=name, content_type='application/gzip', creator=initiator)

                with self.captureOnCommitCallbacks(execute=True), \
                        patch('src.server.oasisapi.analyses.v2_api.tasks.store_file', side_effect=overwrite_in_place), \
                        patch('src.server.oasisapi.analyses.v2_api.tasks.record_sub_task_start'):
                    record_losses_files({'output_location': 'output.tar.gz', 'updated_input_location': 'fresh-inputs.tar.gz'},
                                        analysis_id=analysis.pk, initiator_id=initiator.pk, slug='record-losses-files')

                analysis.refresh_from_db()
                self.assertFalse(RelatedFile.objects.filter(pk=old_input_file.pk).exists())
                self.assertEqual(analysis.input_file.file.name, name)
                self.assertEqual(Path(d, name).read_bytes(), b'new inputs')

    def test_replaced_input_file_shared_with_another_analysis___not_deleted(self):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                shared_input_file = fake_related_file()
                other = fake_analysis(input_file=shared_input_file)
                initiator = fake_user()
                analysis = fake_analysis(input_file=shared_input_file)
                with patch('src.server.oasisapi.analyses.v2_api.tasks.store_file', side_effect=lambda *a, **kw: fake_related_file()), \
                        patch('src.server.oasisapi.analyses.v2_api.tasks.record_sub_task_start'):
                    record_losses_files({'output_location': 'output.tar.gz', 'updated_input_location': 'fresh-inputs.tar.gz'},
                                        analysis_id=analysis.pk, initiator_id=initiator.pk, slug='record-losses-files')

                other.refresh_from_db()
                self.assertEqual(other.input_file, shared_input_file)
                self.assertTrue(RelatedFile.objects.filter(pk=shared_input_file.pk).exists())

    def test_no_updated_input_location___input_file_is_unchanged(self):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                analysis, original_input_file, _, _, _ = self._record_losses_files({'output_location': 'output.tar.gz'})

                self.assertEqual(analysis.input_file, original_input_file)


class RecordSubTaskStart(TestCase):
    def test_subtask_status_does_already_exists___status_is_updated_to_started_state(self):
        _now = now()
        queued_status = AnalysisTaskStatus.objects.create(
            analysis=fake_analysis(),
            slug='task_slug',
            task_id=uuid4().hex,
            status=AnalysisTaskStatus.status_choices.QUEUED,
        )
        with freeze_time(_now):
            record_sub_task_start(queued_status.analysis.pk, 'task_slug', queued_status.task_id)

        queued_status.refresh_from_db()
        self.assertEqual(queued_status.status, AnalysisTaskStatus.status_choices.STARTED)
        self.assertEqual(queued_status.start_time, _now)


class RecordSubTaskSuccess(TestCase):
    @given(
        output_content=text(min_size=1, max_size=10, alphabet=string.ascii_letters),
        error_content=text(min_size=1, max_size=10, alphabet=string.ascii_letters),
    )
    def test_subtask_status_already_exist___status_is_updated_in_completed_state_with_log_files_set(
            self,
            output_content,
            error_content):
        task_id = uuid4().hex
        task_request_mock = Mock()
        task_request_mock.parent_id = task_id

        _now = now()
        status = fake_analysis_task_status(task_id=task_id, slug="slug")

        with TemporaryDirectory() as d, patch('celery.app.task.Context', return_value=task_request_mock):
            with override_settings(MEDIA_ROOT=d):
                log_path = os.path.join(d, uuid4().hex)
                with open(log_path, 'w') as f:
                    f.write(output_content)

                error_path = os.path.join(d, uuid4().hex)
                with open(error_path, 'w') as f:
                    f.write(error_content)

                res = {'log_location': log_path, 'error_location': error_path}

                with freeze_time(_now):
                    record_sub_task_success(res, status.analysis.pk, fake_user().id, "slug")

                status.refresh_from_db()

                self.assertEqual(status.status, AnalysisTaskStatus.status_choices.COMPLETED)
                self.assertEqual(status.end_time, _now)
                self.assertEqual(status.output_log.read().decode(), output_content)
                self.assertEqual(status.error_log.read().decode(), error_content)


class SubtaskErrorLog(TestCase):
    @given(output_content=text(min_size=1, max_size=10, alphabet=string.ascii_letters))
    def test_output_log_is_stored_and_readable(self, output_content):
        status = fake_analysis_task_status(slug="slug")
        initiator = fake_user()

        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                log_path = os.path.join(d, uuid4().hex)
                with open(log_path, 'w') as f:
                    f.write(output_content)

                subtask_error_log(status.analysis.pk, initiator.pk, "slug", uuid4().hex, log_path)
                status.refresh_from_db()

                self.assertEqual(status.output_log.read().decode(), output_content)

    def test_log_reference_is_copied_via_store_file(self):
        """ Regression: the raw worker key was saved as the file name, which on S3/Azure
            got the server's storage prefix prepended and 404'd on read.
        """
        status = fake_analysis_task_status(slug="slug")
        initiator = fake_user()
        task_id = uuid4().hex
        worker_key = 'oasis/worker/{}.log'.format(uuid4().hex)

        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                stored = fake_related_file()
                with patch('src.server.oasisapi.analyses.v2_api.tasks.store_file', return_value=stored) as store_file_mock:
                    subtask_error_log(status.analysis.pk, initiator.pk, "slug", task_id, worker_key)

                store_file_mock.assert_called_once_with(worker_key, 'text/plain', initiator, filename=f'{task_id}-output.log')
                status.refresh_from_db()
                self.assertEqual(status.output_log, stored)


class RecordSubTaskFailure(TestCase):
    @given(error_content=text(min_size=1, max_size=10, alphabet=string.ascii_letters))
    def test_subtask_status_already_exist___status_is_updated_in_completed_state_with_log_files_set(self, error_content):
        task_id = uuid4().hex
        task_request_mock = Mock()
        task_request_mock.parent_id = task_id

        _now = now()
        analysis = fake_analysis()
        status = fake_analysis_task_status(analysis=analysis, slug="hello")

        with (TemporaryDirectory() as d,
              patch('celery.app.task.Context', return_value=task_request_mock),
              override_settings(MEDIA_ROOT=d),
              freeze_time(_now)):
            record_sub_task_failure(None, None, error_content, analysis_id=status.analysis.pk, initiator_id=status.task_id, task_slug="hello")

            status.refresh_from_db()

            self.assertEqual(status.status, AnalysisTaskStatus.status_choices.ERROR)
            self.assertEqual(status.end_time, _now)
            self.assertEqual(status.error_log.read().decode(), error_content)


class HandleTaskFailure(TestCase):
    """ 'handle_task_failure' is the chain-level errback that builds the analysis-wide
        traceback/log file when a V2 run fails. It merges in each failed sub-task's
        'output_log' (the full KERNEL_STDERR/STDOUT output captured by the worker) and
        'error_log' (its traceback), so a user doesn't have to dig through individual
        sub-tasks to see why a run failed.
    """

    def test_run_failure___subtask_output_and_error_logs_are_merged_into_run_traceback_and_log_file(self):
        with TemporaryDirectory() as d, override_settings(MEDIA_ROOT=d):
            initiator = fake_user()
            analysis = fake_analysis()
            fake_analysis_task_status(
                analysis=analysis,
                slug='generate-losses-chunk-1',
                status=AnalysisTaskStatus.status_choices.ERROR,
                output_log=fake_related_file(file='KERNEL_STDERR:\nboom\nSTDOUT:\nfailure output'),
                error_log=fake_related_file(file='Traceback (most recent call last):\nOasisException: boom'),
            )

            handle_task_failure(
                None, None, 'top level celery traceback',
                analysis_id=analysis.pk,
                initiator_id=initiator.pk,
                run_data_uuid='run-uuid',
                traceback_property='run_traceback_file',
                failure_status=Analysis.status_choices.RUN_ERROR,
            )

            analysis.refresh_from_db()
            self.assertEqual(analysis.status, Analysis.status_choices.RUN_ERROR)
            self.assertIsNotNone(analysis.run_traceback_file)
            self.assertIsNotNone(analysis.run_log_file)
            # both fields point at the same combined content, so it's visible from
            # either place on the analysis, without opening a sub-task record
            self.assertEqual(analysis.run_traceback_file_id, analysis.run_log_file_id)

            content = analysis.run_traceback_file.read().decode('utf-8')
            self.assertIn('generate-losses-chunk-1', content)
            self.assertIn('KERNEL_STDERR', content)
            self.assertIn('STDOUT', content)
            self.assertIn('failure output', content)
            self.assertIn('OasisException: boom', content)
            self.assertIn('top level celery traceback', content)

    def test_input_generation_failure___leaves_run_log_file_untouched(self):
        with TemporaryDirectory() as d, override_settings(MEDIA_ROOT=d):
            initiator = fake_user()
            analysis = fake_analysis()
            fake_analysis_task_status(
                analysis=analysis,
                slug='write-input-files',
                status=AnalysisTaskStatus.status_choices.ERROR,
                output_log=fake_related_file(file='STDOUT:\nlookup failure'),
                error_log=fake_related_file(file='OasisExceptionNoKeys: boom'),
            )

            handle_task_failure(
                None, None, 'top level celery traceback',
                analysis_id=analysis.pk,
                initiator_id=initiator.pk,
                run_data_uuid='run-uuid',
                traceback_property='input_generation_traceback_file',
                failure_status=Analysis.status_choices.INPUTS_GENERATION_ERROR,
            )

            analysis.refresh_from_db()
            self.assertEqual(analysis.status, Analysis.status_choices.INPUTS_GENERATION_ERROR)
            self.assertIsNotNone(analysis.input_generation_traceback_file)
            self.assertIsNone(analysis.run_log_file)

    def test_subtask_output_log_not_yet_available___retries_instead_of_writing_a_bare_traceback(self):
        with TemporaryDirectory() as d, override_settings(MEDIA_ROOT=d):
            initiator = fake_user()
            analysis = fake_analysis()
            # sub-task has failed, but the worker's separately-dispatched
            # 'subtask_error_log' task hasn't attached the output log yet
            fake_analysis_task_status(
                analysis=analysis,
                slug='generate-losses-chunk-1',
                status=AnalysisTaskStatus.status_choices.ERROR,
                error_log=fake_related_file(file='Traceback (most recent call last):\nOasisException: boom'),
            )

            with patch.object(handle_task_failure, 'retry', side_effect=RuntimeError('retried')) as retry_mock:
                with self.assertRaises(RuntimeError):
                    handle_task_failure(
                        None, None, 'top level celery traceback',
                        analysis_id=analysis.pk,
                        initiator_id=initiator.pk,
                        run_data_uuid='run-uuid',
                        traceback_property='run_traceback_file',
                        failure_status=Analysis.status_choices.RUN_ERROR,
                    )

            retry_mock.assert_called_once()
            analysis.refresh_from_db()
            self.assertNotEqual(analysis.status, Analysis.status_choices.RUN_ERROR)
            self.assertIsNone(analysis.run_traceback_file)

    def test_no_failed_subtask_recorded_yet___retries_instead_of_writing_a_bare_traceback(self):
        with TemporaryDirectory() as d, override_settings(MEDIA_ROOT=d):
            initiator = fake_user()
            analysis = fake_analysis()

            with patch.object(handle_task_failure, 'retry', side_effect=RuntimeError('retried')) as retry_mock:
                with self.assertRaises(RuntimeError):
                    handle_task_failure(
                        None, None, 'top level celery traceback',
                        analysis_id=analysis.pk,
                        initiator_id=initiator.pk,
                        run_data_uuid='run-uuid',
                        traceback_property='run_traceback_file',
                        failure_status=Analysis.status_choices.RUN_ERROR,
                    )

            retry_mock.assert_called_once()

    def test_retries_exhausted___writes_the_bare_traceback_rather_than_failing_silently(self):
        with TemporaryDirectory() as d, override_settings(MEDIA_ROOT=d):
            initiator = fake_user()
            analysis = fake_analysis()
            fake_analysis_task_status(
                analysis=analysis,
                slug='generate-losses-chunk-1',
                status=AnalysisTaskStatus.status_choices.ERROR,
                error_log=fake_related_file(file='Traceback (most recent call last):\nOasisException: boom'),
            )
            task_request_mock = Mock()
            task_request_mock.retries = handle_task_failure.max_retries

            with patch('celery.app.task.Context', return_value=task_request_mock):
                handle_task_failure(
                    None, None, 'top level celery traceback',
                    analysis_id=analysis.pk,
                    initiator_id=initiator.pk,
                    run_data_uuid='run-uuid',
                    traceback_property='run_traceback_file',
                    failure_status=Analysis.status_choices.RUN_ERROR,
                )

            analysis.refresh_from_db()
            self.assertEqual(analysis.status, Analysis.status_choices.RUN_ERROR)
            self.assertIsNotNone(analysis.run_traceback_file)
            content = analysis.run_traceback_file.read().decode('utf-8')
            self.assertIn('top level celery traceback', content)
            self.assertIn('OasisException: boom', content)


class ChordErrorCallback(TestCase):
    def test_analysis_fails___all_queued_and_started_tasks_are_revoked(self):
        _now = now()
        queued_time = _now - datetime.timedelta(hours=1)
        analysis = fake_analysis()
        with freeze_time(queued_time):
            queued = fake_analysis_task_status(
                analysis=analysis,
                status=AnalysisTaskStatus.status_choices.QUEUED,
                slug="1"
            )
            running = fake_analysis_task_status(
                analysis=analysis,
                status=AnalysisTaskStatus.status_choices.STARTED,
                start_time=_now - datetime.timedelta(minutes=40),
                slug="2"
            )
            completed = fake_analysis_task_status(
                analysis=analysis,
                status=AnalysisTaskStatus.status_choices.COMPLETED,
                start_time=_now - datetime.timedelta(minutes=30),
                end_time=_now - datetime.timedelta(minutes=3),
                slug="3"
            )
            errored = fake_analysis_task_status(
                analysis=analysis,
                status=AnalysisTaskStatus.status_choices.ERROR,
                start_time=_now - datetime.timedelta(minutes=20),
                end_time=_now - datetime.timedelta(minutes=2),
                slug="4"
            )
            cancelled = fake_analysis_task_status(
                analysis=analysis,
                status=AnalysisTaskStatus.status_choices.CANCELLED,
                start_time=_now - datetime.timedelta(minutes=10),
                end_time=_now - datetime.timedelta(minutes=1),
                slug="5"
            )

        with freeze_time(_now), patch('src.server.oasisapi.analyses.v2_api.tasks.celery_app_v2.control.revoke') as revoke_mock:
            chord_error_callback(analysis.id)

            revoke_mock.assert_called_once_with({queued.task_id, running.task_id}, terminate=True)

            queued.refresh_from_db()
            running.refresh_from_db()
            completed.refresh_from_db()
            errored.refresh_from_db()
            cancelled.refresh_from_db()

            self.assertEqual(queued.end_time, _now)
            self.assertEqual(queued.status, AnalysisTaskStatus.status_choices.CANCELLED)

            self.assertEqual(running.start_time, _now - datetime.timedelta(minutes=40))
            self.assertEqual(running.end_time, _now)
            self.assertEqual(running.status, AnalysisTaskStatus.status_choices.CANCELLED)

            self.assertEqual(completed.start_time, _now - datetime.timedelta(minutes=30))
            self.assertEqual(completed.end_time, _now - datetime.timedelta(minutes=3))
            self.assertEqual(completed.status, AnalysisTaskStatus.status_choices.COMPLETED)

            self.assertEqual(errored.start_time, _now - datetime.timedelta(minutes=20))
            self.assertEqual(errored.end_time, _now - datetime.timedelta(minutes=2))
            self.assertEqual(errored.status, AnalysisTaskStatus.status_choices.ERROR)

            self.assertEqual(cancelled.start_time, _now - datetime.timedelta(minutes=10))
            self.assertEqual(cancelled.end_time, _now - datetime.timedelta(minutes=1))
            self.assertEqual(cancelled.status, AnalysisTaskStatus.status_choices.CANCELLED)


class StoreLookupErrorsFile(TestCase):
    def test_parquet_reference___stored_as_parquet(self):
        with patch('src.server.oasisapi.analyses.v2_api.tasks.store_file') as store_file_mock:
            store_lookup_errors_file('abc123.parquet', 'user', 1)

        store_file_mock.assert_called_once_with(
            'abc123.parquet', 'application/octet-stream', 'user', filename='analysis_1_keys-errors.parquet')

    def test_csv_reference___stored_as_csv(self):
        with patch('src.server.oasisapi.analyses.v2_api.tasks.store_file') as store_file_mock:
            store_lookup_errors_file('abc123.csv', 'user', 1)

        store_file_mock.assert_called_once_with(
            'abc123.csv', 'text/csv', 'user', filename='analysis_1_keys-errors.csv')

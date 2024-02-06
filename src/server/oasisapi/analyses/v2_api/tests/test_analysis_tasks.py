# import datetime
# import os
# import string
# from unittest.mock import Mock, patch
# from uuid import uuid4

# from backports.tempfile import TemporaryDirectory
# from django.test import override_settings
# from django.utils.timezone import now
# from freezegun import freeze_time
# from hypothesis import given
# from hypothesis import settings
# from hypothesis.extra.django import TestCase
# from hypothesis.strategies import text
# from pathlib2 import Path

# from .fakes import fake_analysis, fake_analysis_task_status
# from ..models import Analysis, AnalysisTaskStatus
# from ...auth.tests.fakes import fake_user

# Override default deadline for all tests to 8s
# settings.register_profile("ci", deadline=800.0)
# settings.load_profile("ci")

#################################################
# Commented out code - upgrade in 2.0 branch?
#
# class RunAnalysisSuccess(TestCase):
#     @given(
#         output_location=text(min_size=1, max_size=10, alphabet=string.ascii_letters),
#         log_location=text(min_size=1, max_size=10, alphabet=string.ascii_letters),
#         traceback_location=text(min_size=1, max_size=10, alphabet=string.ascii_letters),
#         return_code=sampled_from([0, 1])
#     )
#     def test_output_file_and_status_are_updated(self, output_location, log_location, traceback_location, return_code):
#         expected_status = Analysis.status_choices.RUN_COMPLETED if return_code == 0 else Analysis.status_choices.RUN_ERROR
#
#         with TemporaryDirectory() as d:
#             with override_settings(MEDIA_ROOT=d):
#                 initiator = fake_user()
#                 analysis = fake_analysis()
#                 Path(d, output_location).touch()
#                 Path(d, log_location).touch()
#                 Path(d, traceback_location).touch()
#
#                 record_run_analysis_result(
#                     (
#                         os.path.join(d, output_location),
#                         os.path.join(d, traceback_location),
#                         os.path.join(d, log_location),
#                         return_code,
#                     ),
#                     analysis.pk,
#                     initiator.pk,
#                 )
#
#                 analysis.refresh_from_db()
#
#                 if return_code == 0:
#                     self.assertEqual(analysis.output_file.filename, output_location)
#                     self.assertEqual(analysis.output_file.content_type, 'application/gzip')
#                     self.assertEqual(analysis.output_file.creator, initiator)
#                 else:
#                       self.assertEqual(analysis.output_file, None)
#
#                 self.assertEqual(analysis.run_log_file.filename, log_location)
#                 self.assertEqual(analysis.run_log_file.content_type, 'application/gzip')
#                 self.assertEqual(analysis.run_log_file.creator, initiator)
#
#                 self.assertEqual(analysis.run_traceback_file.filename, traceback_location)
#                 self.assertEqual(analysis.run_traceback_file.content_type, 'text/plain')
#                 self.assertEqual(analysis.run_traceback_file.creator, initiator)
#
#                 self.assertEqual(analysis.status, expected_status)
#
#
# class RunAnalysisFailure(TestCase):
#     @given(traceback=text(min_size=1, max_size=10, alphabet=string.ascii_letters))
#     def test_output_tracebackfile__and_status_are_updated(self, traceback):
#         with TemporaryDirectory() as d:
#             with override_settings(MEDIA_ROOT=d):
#                 initiator = fake_user()
#                 analysis = fake_analysis()
#
#                 record_run_analysis_failure(None, None, traceback, analysis.pk, initiator.pk)
#
#                 analysis.refresh_from_db()
#
#                 self.assertEqual(analysis.run_traceback_file.file.read(), traceback.encode())
#                 self.assertEqual(analysis.run_traceback_file.content_type, 'text/plain')
#                 self.assertEqual(analysis.run_traceback_file.creator, initiator)
#                 self.assertEqual(analysis.status, analysis.status_choices.RUN_ERROR)
#                 self.assertTrue(isinstance(analysis.task_finished, datetime.datetime))
#
#
# class GenerateInputsSuccess(TestCase):
#     @given(
#         input_location=text(min_size=1, max_size=10, alphabet=string.ascii_letters),
#         lookup_error_fp=text(min_size=1, max_size=10, alphabet=string.ascii_letters),
#         lookup_success_fp=text(min_size=1, max_size=10, alphabet=string.ascii_letters),
#         lookup_validation_fp=text(min_size=1, max_size=10, alphabet=string.ascii_letters),
#         summary_levels_fp=text(min_size=1, max_size=10, alphabet=string.ascii_letters),
#         traceback_fp=text(min_size=1, max_size=10, alphabet=string.ascii_letters),
#     )
#     def test_input_file_lookup_files_and_status_are_updated(self, input_location, lookup_error_fp, lookup_success_fp, lookup_validation_fp, summary_levels_fp, traceback_fp):
#         with TemporaryDirectory() as d:
#             with override_settings(MEDIA_ROOT=d):
#                 Path(d, input_location).touch()
#                 Path(d, lookup_error_fp).touch()
#                 Path(d, lookup_success_fp).touch()
#                 Path(d, lookup_validation_fp).touch()
#                 Path(d, summary_levels_fp).touch()
#                 Path(d, traceback_fp).touch()
#
#                 initiator = fake_user()
#                 analysis = fake_analysis()
#
#                 generate_input_success({
#                     'output_location': input_location,
#                     'log_location': None,
#                     'error_location': None,
#                     'return_code': 0,
#                     'lookup_error_location': lookup_error_fp,
#                     'lookup_success_location': lookup_success_fp,
#                     'lookup_validation_location': lookup_validation_fp,
#                     'summary_levels_location': summary_levels_fp
#                 }, analysis.pk, initiator.pk)
#                 analysis.refresh_from_db()
#
#                 self.assertEqual(analysis.input_file.filename, input_location)
#                 self.assertEqual(analysis.input_file.content_type, 'application/gzip')
#                 self.assertEqual(analysis.input_file.creator, initiator)
#
#                 self.assertEqual(analysis.lookup_errors_file.filename, lookup_error_fp)
#                 self.assertEqual(analysis.lookup_errors_file.content_type, 'text/csv')
#                 self.assertEqual(analysis.lookup_errors_file.creator, initiator)
#
#                 self.assertEqual(analysis.lookup_success_file.filename, lookup_success_fp)
#                 self.assertEqual(analysis.lookup_success_file.content_type, 'text/csv')
#                 self.assertEqual(analysis.lookup_success_file.creator, initiator)
#
#                 self.assertEqual(analysis.lookup_validation_file.filename, lookup_validation_fp)
#                 self.assertEqual(analysis.lookup_validation_file.content_type, 'application/json')
#                 self.assertEqual(analysis.lookup_validation_file.creator, initiator)
#
#                 self.assertEqual(analysis.summary_levels_file.filename, summary_levels_fp)
#                 self.assertEqual(analysis.summary_levels_file.content_type, 'application/json')
#                 self.assertEqual(analysis.summary_levels_file.creator, initiator)
#
#                 self.assertEqual(analysis.status, analysis.status_choices.READY)
#                 self.assertTrue(isinstance(analysis.task_finished, datetime.datetime))
#
#
# class GenerateInputsFailure(TestCase):
#     @given(traceback=text(min_size=1, max_size=10, alphabet=string.ascii_letters))
#     def test_input_generation_traceback_file_and_status_are_updated(self, traceback):
#         with TemporaryDirectory() as d:
#             with override_settings(MEDIA_ROOT=d):
#                 initiator = fake_user()
#                 analysis = fake_analysis()
#
#                 record_generate_input_failure(None, None, traceback, analysis.pk, initiator.pk)
#
#                 analysis.refresh_from_db()
#
#                 self.assertEqual(analysis.input_generation_traceback_file.file.read(), traceback.encode())
#                 self.assertEqual(analysis.input_generation_traceback_file.content_type, 'text/plain')
#                 self.assertEqual(analysis.input_generation_traceback_file.creator, initiator)
#                 self.assertEqual(analysis.status, analysis.status_choices.INPUTS_GENERATION_ERROR)
#                 self.assertTrue(isinstance(analysis.task_finished, datetime.datetime))
#
#
# class StartInputGenerationTask(TestCase):
#     def test_generate_inputs_is_called_on_task_controller(self):
#         analysis = fake_analysis()
#         initiator = fake_user()
#
#
#         task_controller = Mock()
#         with patch('src.server.oasisapi.analyses.tasks.get_analysis_task_controller', return_value=task_controller):
#             start_input_generation_task(analysis.pk, initiator.pk)
#
#         analysis.refresh_from_db()
#
#         self.assertEqual(analysis.status, Analysis.status_choices.INPUTS_GENERATION_STARTED)
#         task_controller.generate_inputs.assert_called_once_with(analysis, initiator)
#
#
# class StartLossGenerationTask(TestCase):
#     def test_generate_losses_is_called_on_task_controller(self):
#         analysis = fake_analysis()
#         initiator = fake_user()
#
#         task_controller = Mock()
#         with patch('src.server.oasisapi.analyses.tasks.get_analysis_task_controller', return_value=task_controller):
#             start_loss_generation_task(analysis.pk, initiator.pk)
#
#         analysis.refresh_from_db()
#
#         self.assertEqual(analysis.status, Analysis.status_choices.RUN_STARTED)
#         task_controller.generate_losses.assert_called_once_with(analysis, initiator)
#
#
# class RecordSubTaskStart(TestCase):
#     def test_subtask_status_does_not_yet_exist___status_is_created_in_started_state(self):
#         _now = now()
#         analysis = fake_analysis()
#         task_id = uuid4().hex
#
#         with freeze_time(_now):
#             record_sub_task_start(analysis.pk, task_id, 'some_queue')
#
#         status = AnalysisTaskStatus.objects.get(analysis=analysis, task_id=task_id)
#
#         self.assertEqual(status.status, AnalysisTaskStatus.status_choices.STARTED)
#         self.assertEqual(status.start_time, _now)
#         self.assertEqual(status.queue_time, _now)
#
#     def test_subtask_status_does_already_exists___status_is_updated_to_started_state(self):
#         _now = now()
#         with freeze_time(_now - datetime.timedelta(hours=1)):
#             status = fake_analysis_task_status()
#
#         with freeze_time(_now):
#             record_sub_task_start(status.analysis.pk, status.task_id, 'some_queue')
#
#         status.refresh_from_db()
#
#         self.assertEqual(status.status, AnalysisTaskStatus.status_choices.STARTED)
#         self.assertEqual(status.start_time, _now)
#         self.assertEqual(status.queue_time, _now - datetime.timedelta(hours=1))
#
#
# class RecordSubTaskSuccess(TestCase):
#     @given(
#         output_content=text(min_size=1, max_size=10, alphabet=string.ascii_letters),
#         error_content=text(min_size=1, max_size=10, alphabet=string.ascii_letters),
#     )
#     def test_subtask_status_already_exist___status_is_updated_in_completed_state_with_log_files_set(
#             self,
#             output_content,
#             error_content):
#         task_id = uuid4().hex
#         task_request_mock = Mock()
#         task_request_mock.parent_id = task_id
#
#         _now = now()
#         with freeze_time(_now - datetime.timedelta(hours=1)):
#             status = fake_analysis_task_status(task_id=task_id)
#
#         with TemporaryDirectory() as d, patch('celery.app.task.Context', return_value=task_request_mock):
#             with override_settings(MEDIA_ROOT=d):
#                 log_path = os.path.join(d, uuid4().hex)
#                 with open(log_path, 'w') as f:
#                     f.write(output_content)
#
#                 error_path = os.path.join(d, uuid4().hex)
#                 with open(error_path, 'w') as f:
#                     f.write(error_content)
#
#                 with freeze_time(_now):
#                     record_sub_task_success(
#                         {
#                             'log_location': log_path,
#                             'error_location': error_path,
#                         },
#                         status.analysis.pk,
#                         fake_user().id,
#                     )
#
#                 status.refresh_from_db()
#
#                 self.assertEqual(status.status, AnalysisTaskStatus.status_choices.COMPLETED)
#                 self.assertEqual(status.queue_time, _now - datetime.timedelta(hours=1))
#                 self.assertEqual(status.end_time, _now)
#                 self.assertEqual(status.output_log.read().decode(), output_content)
#                 self.assertEqual(status.error_log.read().decode(), error_content)
#
#
# class RecordSubTaskFailure(TestCase):
#     @given(
#         error_content=text(min_size=1, max_size=10, alphabet=string.ascii_letters),
#     )
#     def test_subtask_status_already_exist___status_is_updated_in_completed_state_with_log_files_set(
#             self,
#             error_content):
#         task_id = uuid4().hex
#         task_request_mock = Mock()
#         task_request_mock.parent_id = task_id
#
#         _now = now()
#         with freeze_time(_now - datetime.timedelta(hours=1)):
#             status = fake_analysis_task_status(task_id=task_id)
#
#         with TemporaryDirectory() as d, patch('celery.app.task.Context', return_value=task_request_mock):
#             with override_settings(MEDIA_ROOT=d):
#                 with freeze_time(_now):
#                     record_sub_task_failure(
#                         Mock(),
#                         Mock(),
#                         error_content,
#                         status.analysis.pk,
#                         fake_user().id,
#                     )
#
#                 status.refresh_from_db()
#
#                 self.assertEqual(status.status, AnalysisTaskStatus.status_choices.ERROR)
#                 self.assertEqual(status.queue_time, _now - datetime.timedelta(hours=1))
#                 self.assertEqual(status.end_time, _now)
#                 self.assertEqual(status.error_log.read().decode(), error_content)
#
#
# class ChordErrorCallback(TestCase):
#     def test_analysis_fails___all_queued_and_started_tasks_are_revoked(self):
#         _now = now()
#         queued_time = _now - datetime.timedelta(hours=1)
#         analysis = fake_analysis()
#
#         with freeze_time(queued_time):
#             queued = fake_analysis_task_status(
#                 analysis=analysis,
#                 status=AnalysisTaskStatus.status_choices.QUEUED
#             )
#             running = fake_analysis_task_status(
#                 analysis=analysis,
#                 status=AnalysisTaskStatus.status_choices.STARTED,
#                 start_time=_now - datetime.timedelta(minutes=40),
#             )
#             completed = fake_analysis_task_status(
#                 analysis=analysis,
#                 status=AnalysisTaskStatus.status_choices.COMPLETED,
#                 start_time=_now - datetime.timedelta(minutes=30),
#                 end_time=_now - datetime.timedelta(minutes=3),
#             )
#             errored = fake_analysis_task_status(
#                 analysis=analysis,
#                 status=AnalysisTaskStatus.status_choices.ERROR,
#                 start_time=_now - datetime.timedelta(minutes=20),
#                 end_time=_now - datetime.timedelta(minutes=2),
#             )
#             cancelled = fake_analysis_task_status(
#                 analysis=analysis,
#                 status=AnalysisTaskStatus.status_choices.CANCELLED,
#                 start_time=_now - datetime.timedelta(minutes=10),
#                 end_time=_now - datetime.timedelta(minutes=1),
#             )
#
#         with freeze_time(_now), patch('src.server.oasisapi.analyses.tasks.celery_app.control.revoke') as revoke_mock:
#             chord_error_callback(analysis.id)
#
#             revoke_mock.assert_called_once_with({queued.task_id, running.task_id}, terminate=True)
#
#             queued.refresh_from_db()
#             running.refresh_from_db()
#             completed.refresh_from_db()
#             errored.refresh_from_db()
#             cancelled.refresh_from_db()
#
#             self.assertEqual(queued.queue_time, _now - datetime.timedelta(hours=1))
#             self.assertEqual(queued.end_time, _now)
#             self.assertEqual(queued.status, AnalysisTaskStatus.status_choices.CANCELLED)
#
#             self.assertEqual(running.queue_time, _now - datetime.timedelta(hours=1))
#             self.assertEqual(running.start_time, _now - datetime.timedelta(minutes=40))
#             self.assertEqual(running.end_time, _now)
#             self.assertEqual(running.status, AnalysisTaskStatus.status_choices.CANCELLED)
#
#             self.assertEqual(completed.queue_time, _now - datetime.timedelta(hours=1))
#             self.assertEqual(completed.start_time, _now - datetime.timedelta(minutes=30))
#             self.assertEqual(completed.end_time, _now - datetime.timedelta(minutes=3))
#             self.assertEqual(completed.status, AnalysisTaskStatus.status_choices.COMPLETED)
#
#             self.assertEqual(errored.queue_time, _now - datetime.timedelta(hours=1))
#             self.assertEqual(errored.start_time, _now - datetime.timedelta(minutes=20))
#             self.assertEqual(errored.end_time, _now - datetime.timedelta(minutes=2))
#             self.assertEqual(errored.status, AnalysisTaskStatus.status_choices.ERROR)
#
#             self.assertEqual(cancelled.queue_time, _now - datetime.timedelta(hours=1))
#             self.assertEqual(cancelled.start_time, _now - datetime.timedelta(minutes=10))
#             self.assertEqual(cancelled.end_time, _now - datetime.timedelta(minutes=1))
#             self.assertEqual(cancelled.status, AnalysisTaskStatus.status_choices.CANCELLED)

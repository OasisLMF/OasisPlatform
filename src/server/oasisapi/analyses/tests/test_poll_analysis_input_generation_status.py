# import string
# from uuid import uuid4
#
# from backports.tempfile import TemporaryDirectory
# from celery.states import SUCCESS, FAILURE, REVOKED, REJECTED, RETRY, RECEIVED, PENDING, STARTED
# from django.test import override_settings
# from hypothesis import given
# from hypothesis.extra.django import TestCase
# from hypothesis.strategies import text, sampled_from
# from mock import patch, Mock
# from pathlib2 import Path
#
# from src.server.oasisapi.auth.tests.fakes import fake_user
# from ..tasks import poll_analysis_input_generation_status
# from .fakes import fake_analysis, fake_async_result_factory
#
#
# class PollAnalysisInputGenerationStatus(TestCase):
#     @given(task_id=text(min_size=1, max_size=10, alphabet=string.ascii_letters))
#     def test_celery_status_is_success___status_is_ready_and_task_is_not_rescheduled_input_end_errors_files_are_set(self, task_id):
#         with TemporaryDirectory() as d:
#             with override_settings(MEDIA_ROOT=d):
#                 input_file = Path(d, uuid4().hex)
#                 input_file.touch()
#
#                 error_file = Path(d, uuid4().hex)
#                 error_file.touch()
#
#                 with patch('src.server.oasisapi.analyses.tasks.AsyncResult', fake_async_result_factory(SUCCESS, task_id, (input_file.relative_to(d), error_file.relative_to(d)))):
#                     initiator = fake_user()
#                     analysis = fake_analysis(generate_inputs_task_id=task_id, input_file='contents')
#
#                     poll_analysis_input_generation_status.retry = Mock()
#                     poll_analysis_input_generation_status(analysis.pk, initiator.pk)
#
#                     analysis.refresh_from_db()
#
#                     poll_analysis_input_generation_status.retry.assert_not_called()
#                     self.assertEqual(analysis.status_choices.READY, analysis.status)
#                     self.assertEqual(analysis.input_file.file.file.name, str(input_file))
#                     self.assertEqual(analysis.input_file.content_type, 'application/gzip')
#                     self.assertEqual(analysis.input_file.creator, initiator)
#                     self.assertEqual(analysis.input_errors_file.file.file.name, str(error_file))
#                     self.assertEqual(analysis.input_errors_file.content_type, 'text/csv')
#                     self.assertEqual(analysis.input_errors_file.creator, initiator)
#
#     @given(task_id=text(min_size=1, max_size=10, alphabet=string.ascii_letters), traceback=text(min_size=1, max_size=10, alphabet=string.ascii_letters))
#     def test_celery_status_is_error___status_is_complete_and_task_is_not_rescheduled_traceback_is_stored(self, task_id, traceback):
#         with TemporaryDirectory() as d:
#             with override_settings(MEDIA_ROOT=d):
#                 with patch('src.server.oasisapi.analyses.tasks.AsyncResult', fake_async_result_factory(FAILURE, task_id, result_traceback=traceback)):
#                     initiator = fake_user()
#                     analysis = fake_analysis(generate_inputs_task_id=task_id, input_file='contents')
#
#                     poll_analysis_input_generation_status.retry = Mock()
#                     poll_analysis_input_generation_status(analysis.pk, initiator.pk)
#
#                     analysis.refresh_from_db()
#
#                     poll_analysis_input_generation_status.retry.assert_not_called()
#                     self.assertEqual(analysis.status_choices.INPUTS_GENERATION_ERROR, analysis.status)
#                     self.assertEqual(analysis.input_generation_traceback_file.read(), traceback.encode())
#
#     @given(task_id=text(min_size=1, max_size=10, alphabet=string.ascii_letters), status=sampled_from([PENDING, RECEIVED, RETRY]))
#     def test_celery_status_is_pending___status_is_generating_inputs_and_task_is_rescheduled(self, task_id, status):
#         with TemporaryDirectory() as d:
#             with override_settings(MEDIA_ROOT=d):
#                 with patch('src.server.oasisapi.analyses.tasks.AsyncResult', fake_async_result_factory(status, task_id)):
#                     initiator = fake_user()
#                     analysis = fake_analysis(generate_inputs_task_id=task_id, input_file='contents')
#
#                     poll_analysis_input_generation_status.retry = Mock()
#                     poll_analysis_input_generation_status(analysis.pk, initiator.pk)
#
#                     analysis.refresh_from_db()
#
#                     poll_analysis_input_generation_status.retry.assert_called_once()
#                     self.assertEqual(analysis.status_choices.GENERATING_INPUTS, analysis.status)
#
#     @given(task_id=text(min_size=1, max_size=10, alphabet=string.ascii_letters))
#     def test_celery_status_is_started___status_is_generating_inputs_and_task_is_rescheduled(self, task_id):
#         with TemporaryDirectory() as d:
#             with override_settings(MEDIA_ROOT=d):
#                 with patch('src.server.oasisapi.analyses.tasks.AsyncResult', fake_async_result_factory(STARTED, task_id)):
#                     initiator = fake_user()
#                     analysis = fake_analysis(generate_inputs_task_id=task_id, input_file='contents')
#
#                     poll_analysis_input_generation_status.retry = Mock()
#                     poll_analysis_input_generation_status(analysis.pk, initiator.pk)
#
#                     analysis.refresh_from_db()
#
#                     poll_analysis_input_generation_status.retry.assert_called_once()
#                     self.assertEqual(analysis.status_choices.GENERATING_INPUTS, analysis.status)
#
#     @given(task_id=text(min_size=1, max_size=10, alphabet=string.ascii_letters))
#     def test_celery_status_is_started___status_is_inputs_generation_canceled_and_task_is_not_rescheduled(self, task_id):
#         with TemporaryDirectory() as d:
#             with override_settings(MEDIA_ROOT=d):
#                 with patch('src.server.oasisapi.analyses.tasks.AsyncResult', fake_async_result_factory(REVOKED, task_id)):
#                     initiator = fake_user()
#                     analysis = fake_analysis(generate_inputs_task_id=task_id, input_file='contents')
#
#                     poll_analysis_input_generation_status.retry = Mock()
#                     poll_analysis_input_generation_status(analysis.pk, initiator.pk)
#
#                     analysis.refresh_from_db()
#
#                     poll_analysis_input_generation_status.retry.assert_not_called()
#                     self.assertEqual(analysis.status_choices.INPUTS_GENERATION_CANCELED, analysis.status)

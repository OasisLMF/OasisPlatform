import string

from celery.states import SUCCESS, FAILURE, REVOKED, REJECTED, RETRY, RECEIVED, PENDING, STARTED
from hypothesis import given
from hypothesis.extra.django import TestCase
from hypothesis.strategies import text, sampled_from
from mock import patch, Mock

from ..tasks import poll_analysis_status
from .fakes import fake_analysis


def fake_async_result_factory(target_status, target_task_id):
    class FakeAsyncResult(object):
        status = target_status

        def __init__(self, task_id):
            if task_id != target_task_id:
                raise ValueError()

    return FakeAsyncResult


class PollAnalysisStatus(TestCase):
    @given(task_id=text(min_size=1, max_size=10, alphabet=string.ascii_letters))
    def test_celery_status_is_success___status_is_complete_and_task_is_not_rescheduled(self, task_id):
        with patch('oasisapi.analyses.tasks.AsyncResult', fake_async_result_factory(SUCCESS, task_id)):
            fake_task = Mock()
            analysis = fake_analysis(task_id=task_id)

            poll_analysis_status(fake_task, analysis.pk)

            analysis.refresh_from_db()

            fake_task.retry.assert_not_called()
            self.assertEqual(analysis.status_choices.STOPPED_COMPLETED, analysis.status)

    @given(task_id=text(min_size=1, max_size=10, alphabet=string.ascii_letters), status=sampled_from([FAILURE, REJECTED]))
    def test_celery_status_is_error___status_is_complete_and_task_is_not_rescheduled(self, task_id, status):
        with patch('oasisapi.analyses.tasks.AsyncResult', fake_async_result_factory(status, task_id)):
            fake_task = Mock()
            analysis = fake_analysis(task_id=task_id)

            poll_analysis_status(fake_task, analysis.pk)

            analysis.refresh_from_db()

            fake_task.retry.assert_not_called()
            self.assertEqual(analysis.status_choices.STOPPED_ERROR, analysis.status)

    @given(task_id=text(min_size=1, max_size=10, alphabet=string.ascii_letters), status=sampled_from([PENDING, RECEIVED, RETRY]))
    def test_celery_status_is_pending___status_is_complete_and_task_is_not_rescheduled(self, task_id, status):
        with patch('oasisapi.analyses.tasks.AsyncResult', fake_async_result_factory(status, task_id)):
            fake_task = Mock()
            analysis = fake_analysis(task_id=task_id)

            poll_analysis_status(fake_task, analysis.pk)

            analysis.refresh_from_db()

            fake_task.retry.assert_called_once()
            self.assertEqual(analysis.status_choices.PENDING, analysis.status)

    @given(task_id=text(min_size=1, max_size=10, alphabet=string.ascii_letters))
    def test_celery_status_is_started___status_is_complete_and_task_is_not_rescheduled(self, task_id):
        with patch('oasisapi.analyses.tasks.AsyncResult', fake_async_result_factory(STARTED, task_id)):
            fake_task = Mock()
            analysis = fake_analysis(task_id=task_id)

            poll_analysis_status(fake_task, analysis.pk)

            analysis.refresh_from_db()

            fake_task.retry.assert_called_once()
            self.assertEqual(analysis.status_choices.STARTED, analysis.status)

    @given(task_id=text(min_size=1, max_size=10, alphabet=string.ascii_letters))
    def test_celery_status_is_started___status_is_complete_and_task_is_not_rescheduled(self, task_id):
        with patch('oasisapi.analyses.tasks.AsyncResult', fake_async_result_factory(REVOKED, task_id)):
            fake_task = Mock()
            analysis = fake_analysis(task_id=task_id)

            poll_analysis_status(fake_task, analysis.pk)

            analysis.refresh_from_db()

            fake_task.retry.assert_not_called()
            self.assertEqual(analysis.status_choices.STOPPED_CANCELLED, analysis.status)

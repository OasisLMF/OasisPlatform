from unittest import TestCase, mock

from celery import Celery, states
from celery.exceptions import Terminated
from celery.signals import task_failure, task_revoked
from celery.worker import state as worker_state

from src.model_execution_worker.celery_error_handler import OasisWorkerTask


class CancelledTaskTests(TestCase):
    """ A task revoked on an in-process (threads/gevent/eventlet) worker should end as
    REVOKED with no errbacks or `task_failure`, the same as a prefork termination.
    """

    def setUp(self):
        self.app = Celery('test', broker='memory://', backend='cache+memory://')
        self.app.conf.task_store_eager_result = True
        self.behaviour = None

        @self.app.task(bind=True, base=OasisWorkerTask, name='cancellable')
        def cancellable(task, analysis_id=None):
            worker_state.revoked.add(task.request.id)
            return self.behaviour()

        self.task = cancellable
        self.errback = mock.Mock()
        self.failures, self.revoked = [], []

        @self.app.task(name='errback')
        def errback(*args, **kwargs):
            self.errback(*args, **kwargs)

        self.errback_task = errback

        def on_failure(sender=None, **kw):
            self.failures.append(sender)

        def on_revoked(sender=None, request=None, terminated=None, **kw):
            self.revoked.append((sender, request.id, terminated))

        task_failure.connect(on_failure, weak=False)
        task_revoked.connect(on_revoked, weak=False)
        self.addCleanup(task_failure.disconnect, on_failure)
        self.addCleanup(task_revoked.disconnect, on_revoked)
        self.addCleanup(worker_state.revoked.clear)

    def _run(self, behaviour):
        self.behaviour = behaviour
        # the worker's own `task_revoked` handler asks the API to cancel the analysis
        with mock.patch('src.model_execution_worker.distributed_tasks.signature') as sig:
            result = self.task.apply(kwargs={'analysis_id': 1}, link_error=self.errback_task.s())
        sig.assert_called_once_with('cancel_subtasks', args=[1], queue=mock.ANY)
        return result

    def _assert_revoked(self, result):
        self.assertEqual(result.state, states.IGNORED)
        self.assertEqual(self.app.AsyncResult(result.id).state, states.REVOKED)
        self.assertEqual(self.revoked, [(self.task, result.id, True)])
        self.assertEqual(self.failures, [])
        self.errback.assert_not_called()

    def test_finishes_after_cancel___revoked_not_success(self):
        self._assert_revoked(self._run(lambda: 'done'))

    def test_raises_terminated___revoked_not_failure(self):
        def behaviour():
            raise Terminated('cancelled')
        self._assert_revoked(self._run(behaviour))

    def test_fails_after_cancel___revoked_not_failure(self):
        def behaviour():
            raise ValueError('broken by the kill')
        self._assert_revoked(self._run(behaviour))

    def test_not_cancelled_failure___still_fails(self):
        @self.app.task(bind=True, base=OasisWorkerTask, name='failing')
        def failing(task):
            raise ValueError('real error')

        result = failing.apply(link_error=self.errback_task.s())
        self.assertEqual(result.state, states.FAILURE)
        self.assertEqual(len(self.failures), 1)
        self.assertEqual(self.revoked, [])
        self.errback.assert_called_once()

    def test_called_directly___raises_terminated(self):
        worker_state.revoked.add('direct-id')
        self.behaviour = lambda: 'done'
        with mock.patch.object(self.task, 'request_stack') as stack:
            stack.top = mock.Mock(id='direct-id', called_directly=True)
            with self.assertRaises(Terminated):
                self.task._end_cancelled()

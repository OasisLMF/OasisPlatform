from unittest.mock import Mock, MagicMock, patch
from uuid import uuid4

from django.test import TestCase

from src.server.oasisapi.analyses.v2_api.task_controller import TaskParams, Controller
from src.server.oasisapi.analyses.v2_api.tests.fakes import fake_analysis
from src.server.oasisapi.auth.tests.fakes import fake_user
from celery import signature
from src.server.oasisapi.analyses.v2_api.tasks import record_sub_task_failure, record_sub_task_success


class FakeChord:
    def __init__(self):
        self.head = None
        self.body = None
        self.queue = None
        self.task_ids = None
        self.delay_called = False
        self.link_callback = None

    def __call__(self, head, body=None, queue=None):
        self.head = head
        self.body = body
        self.queue = queue
        self.task_ids = [uuid4().hex for h in head]
        return self

    def _make_fake_task(self, _id):
        res = Mock()
        res.id = _id
        return res

    def link_error(self, sig):
        self.link_callback = sig
        return self

    def delay(self):
        self.delay_called = True
        res = Mock()
        res.parent = Mock()
        res.parent.children = [self._make_fake_task(_id) for _id in self.task_ids]
        return res


class TaskController(TestCase):
    def test_get_subtask_signature_returns_the_correct_task_name_with_params_and_linked_tasks(self):
        analysis = fake_analysis(pk=133)
        initiator = fake_user(pk=82)

        with patch("src.server.oasisapi.analyses.v2_api.task_controller.signature") as mock_sig:
            mock_sig_return = MagicMock()
            mock_sig.return_value = mock_sig_return
            params = TaskParams('foo', bar='bar')
            signature = Controller.get_subtask_signature('test_task_name', analysis, initiator, 'test_uuid', 'test_slug', 'test_queue', params)
            self.assertEqual(mock_sig_return, signature)
            mock_sig.assert_called_once_with(
                'test_task_name', queue='test_queue', args=params.args, kwargs={
                    'initiator_id': 82,
                    'analysis_id': 133,
                    'slug': 'test_slug',
                    'run_data_uuid': 'test_uuid',
                    **params.kwargs
                })
            mock_sig_return.link.assert_called_once_with(record_sub_task_success.s(analysis_id=133, initiator_id=82, task_slug='test_slug'))
            mock_sig_return.link_error.assert_called_once_with(record_sub_task_failure.s(analysis_id=133, initiator_id=82, task_slug='test_slug'))

    def test_start___link_error_chained(self):
        analysis = MagicMock()
        analysis.priority = 12
        analysis.pk = 9
        analysis.sub_task_statuses = MagicMock()
        analysis.sub_task_statuses.all = MagicMock()
        initiator = fake_user()
        initiator.pk = 28
        with (patch("src.server.oasisapi.analyses.models.AnalysisTaskStatus.objects.create_statuses"),
              patch("src.server.oasisapi.analyses.v2_api.task_controller.chain") as mock_chain):
            create_chain = MagicMock()
            create_chain.delay = MagicMock()
            create_chain.delay.return_value = 59
            mock_chain.return_value = create_chain
            chain, task = Controller._start(analysis, initiator, {}, {}, 'uuid', 'traceback', 'failure')
            self.assertEqual(chain, create_chain)
            create_chain.link_error.assert_called_once_with(signature(
                'handle_task_failure',
                kwargs={
                    'analysis_id': 9,
                    'initiator_id': 28,
                    'run_data_uuid': 'uuid',
                    'traceback_property': 'traceback',
                    'failure_status': 'failure',
                }
            ))
            create_chain.delay.assert_called_once_with({}, priority=12)
            self.assertEqual(task, 59)

    def test_generate_inputs___chain_is_created_correctly(self):
        analysis = MagicMock()
        initiator = fake_user()

        mock_subtask_1 = MagicMock()
        mock_subtask_2 = MagicMock()
        mock_chain = [Mock(), Mock()]
        analysis.sub_task_statuses = MagicMock()
        analysis.sub_task_statuses.all.return_value = [mock_subtask_1, mock_subtask_2]

        class MockController(Controller):
            @classmethod
            def _get_inputs_generation_chunks(cls, *args):
                return 2

            @classmethod
            def get_inputs_generation_tasks(cls, *args):
                return None, None

            @classmethod
            def _start(cls, *args):
                return mock_chain, Mock(id='test_task_id')

            @classmethod
            def extract_celery_task_ids(cls, *args):
                return ['id_2', 'id_1']

        result_chain = MockController.generate_inputs(analysis, initiator, loc_lines=10)

        self.assertEqual(result_chain, mock_chain)

        self.assertEqual(mock_subtask_1.task_id, 'id_1')
        self.assertEqual(mock_subtask_2.task_id, 'id_2')
        mock_subtask_1.save.assert_called_once()
        mock_subtask_2.save.assert_called_once()

        self.assertEqual(analysis.lookup_chunks, 2)
        self.assertEqual(analysis.generate_inputs_task_id, 'test_task_id')
        analysis.save.assert_called_once_with(update_fields=[
            "lookup_chunks",
            "generate_inputs_task_id",
            "run_task_id"
        ])

    def test_generate_losses___chain_is_created_correctly(self):
        analysis = MagicMock()
        initiator = fake_user()
        events_total = 1000

        mock_subtask_1 = MagicMock()
        mock_subtask_2 = MagicMock()
        mock_chain = [Mock(), Mock()]
        analysis.sub_task_statuses = MagicMock()
        analysis.sub_task_statuses.all.return_value = [mock_subtask_1, mock_subtask_2]

        class MockController(Controller):
            @classmethod
            def _get_loss_generation_chunks(cls, *args):
                return 3

            @classmethod
            def get_loss_generation_tasks(cls, *args):
                return None, None

            @classmethod
            def _start(cls, *args):
                return mock_chain, Mock(id='test_task_id')

            @classmethod
            def extract_celery_task_ids(cls, *args):
                return ['id_2', 'id_1']

        result_chain = MockController.generate_losses(analysis, initiator, events_total)

        self.assertEqual(result_chain, mock_chain)

        self.assertEqual(mock_subtask_1.task_id, 'id_1')
        self.assertEqual(mock_subtask_2.task_id, 'id_2')
        mock_subtask_1.save.assert_called_once()
        mock_subtask_2.save.assert_called_once()

        self.assertEqual(analysis.analysis_chunks, 3)
        self.assertEqual(analysis.run_task_id, 'test_task_id')
        analysis.save.assert_called_once_with(update_fields=[
            "analysis_chunks",
            "run_task_id"
        ])

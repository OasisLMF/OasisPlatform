# from unittest.mock import patch
from unittest.mock import Mock
from uuid import uuid4

# from django.test import TestCase

# from src.server.oasisapi.analyses.models import AnalysisTaskStatus
# from src.server.oasisapi.analyses.task_controller import TaskParams
# from src.server.oasisapi.analyses.tests.fakes import fake_analysis
# from src.server.oasisapi.auth.tests.fakes import fake_user


class FakeChord:
    def __init__(self):
        self.head = None
        self.body = None
        self.task_ids = None
        self.delay_called = False

    def __call__(self, head, body=None):
        self.head = head
        self.body = body
        self.task_ids = [uuid4().hex for h in head]
        return self

    def _make_fake_task(self, _id):
        res = Mock()
        res.id = _id
        return res

    def delay(self):
        self.delay_called = True
        res = Mock()
        res.parent = Mock()
        res.parent.children = [self._make_fake_task(_id) for _id in self.task_ids]
        return res

###########################################
# No BaseController is available in this branch
#
# class TaskController(TestCase):
#     def test_get_subtask_signature_returns_the_correct_task_name_with_params_and_linked_tasks(self):
#         analysis = fake_analysis()
#         initiator = fake_user()
#
#         sig = BaseController.get_subtask_signature(
#             analysis,
#             initiator,
#             'the_task',
#             TaskParams('foo', bar='boo'),
#             'the_queue'
#         )
#
#         success_callback = sig.options['link']
#         error_callback = sig.options['link_error']
#
#         self.assertEqual(sig.task, 'the_task')
#         self.assertEqual(sig.args, ('foo', ))
#         self.assertEqual(sig.kwargs, {'bar': 'boo'})
#         self.assertEqual(sig.options['queue'], 'the_queue')
#
#         self.assertEqual(len(success_callback), 1)
#         self.assertEqual(success_callback[0].task, 'record_sub_task_success')
#         self.assertEqual(success_callback[0].args, (analysis.pk, initiator.pk, ))
#         self.assertEqual(success_callback[0].kwargs, {})
#         self.assertEqual(success_callback[0].options, {})
#
#         self.assertEqual(len(error_callback), 1)
#         self.assertEqual(error_callback[0].task, 'record_sub_task_failure')
#         self.assertEqual(error_callback[0].args, (analysis.pk, initiator.pk, ))
#         self.assertEqual(error_callback[0].kwargs, {})
#         self.assertEqual(error_callback[0].options, {})
#
#     def test_get_generate_inputs_results_callback_has_correct_signature(self):
#         analysis = fake_analysis()
#         initiator = fake_user()
#
#         sig = BaseController.get_generate_inputs_results_callback(analysis, initiator)
#
#         self.assertEqual(sig.task, 'generate_input_success')
#         self.assertEqual(sig.args, (analysis.pk, initiator.pk, ))
#         self.assertEqual(sig.kwargs, {})
#         self.assertEqual(sig.options, {})
#
#     def test_get_generate_inputs_failure_callback_has_correct_signature(self):
#         analysis = fake_analysis()
#         initiator = fake_user()
#
#         sig = BaseController.get_generate_inputs_error_callback(analysis, initiator)
#
#         self.assertEqual(sig.task, 'record_generate_inputs_failure')
#         self.assertEqual(sig.args, (analysis.pk, initiator.pk, ))
#         self.assertEqual(sig.kwargs, {})
#         self.assertEqual(sig.options, {})
#
#     def test_get_generate_losses_results_callback_has_correct_signature(self):
#         analysis = fake_analysis()
#         initiator = fake_user()
#
#         sig = BaseController.get_generate_losses_results_callback(analysis, initiator)
#
#         self.assertEqual(sig.task, 'record_run_analysis_result')
#         self.assertEqual(sig.args, (analysis.pk, initiator.pk, ))
#         self.assertEqual(sig.kwargs, {})
#         self.assertEqual(sig.options, {})
#
#     def test_get_generate_losses_failure_callback_has_correct_signature(self):
#         analysis = fake_analysis()
#         initiator = fake_user()
#
#         sig = BaseController.get_generate_losses_error_callback(analysis, initiator)
#
#         self.assertEqual(sig.task, 'record_run_analysis_failure')
#         self.assertEqual(sig.args, (analysis.pk, initiator.pk, ))
#         self.assertEqual(sig.kwargs, {})
#         self.assertEqual(sig.options, {})
#
#     def test_generate_inputs_with_single_task_param___error_and_success_callbacks_are_chained(self):
#         analysis = fake_analysis()
#         initiator = fake_user()
#
#         task_id = uuid4().hex
#         delay_res = Mock()
#         delay_res.id = task_id
#
#         subtask = Mock()
#         subtask.delay.return_value = delay_res
#
#         class MockController(BaseController):
#             @classmethod
#             def get_generate_inputs_tasks_params(cls, analysis, initiator):
#                 return TaskParams('foo', bar='boo')
#
#             @classmethod
#             def get_subtask_signature(cls, analysis, initiator, task_name, params, queue):
#                 return subtask
#
#             @classmethod
#             def get_generate_inputs_results_callback(cls, analysis, initiator):
#                 return 'generate_inputs_results_callback'
#
#             @classmethod
#             def get_generate_inputs_error_callback(cls, analysis, initiator):
#                 return 'generate_inputs_error_callback'
#
#         MockController.generate_inputs(analysis, initiator)
#
#         subtask.s.asset_called_once_with('foo', bar='boo')
#         subtask.link.assert_called_once_with('generate_inputs_results_callback')
#         subtask.link_error.assert_called_once_with('generate_inputs_error_callback')
#         subtask.delay.assert_called_once()
#         self.assertEqual(analysis.sub_task_statuses.count(), 1)
#         self.assertTrue(
#             analysis.sub_task_statuses.filter(
#                 task_id=task_id, status=AnalysisTaskStatus.status_choices.QUEUED
#             ).exists()
#         )
#
#     def test_generate_losses_with_single_task_param___error_and_success_callbacks_are_chained(self):
#         analysis = fake_analysis()
#         initiator = fake_user()
#
#         task_id = uuid4().hex
#         delay_res = Mock()
#         delay_res.id = task_id
#
#         subtask = Mock()
#         subtask.delay.return_value = delay_res
#
#         class MockController(BaseController):
#             @classmethod
#             def get_generate_losses_tasks_params(cls, analysis, initiator):
#                 return TaskParams('foo', bar='boo')
#
#             @classmethod
#             def get_subtask_signature(cls, analysis, initiator, task_name, params, queue):
#                 return subtask
#
#             @classmethod
#             def get_generate_losses_results_callback(cls, analysis, initiator):
#                 return 'generate_losses_results_callback'
#
#             @classmethod
#             def get_generate_losses_error_callback(cls, analysis, initiator):
#                 return 'generate_losses_error_callback'
#
#         MockController.generate_losses(analysis, initiator)
#
#         subtask.s.asset_called_once_with('foo', bar='boo')
#         subtask.link.assert_called_once_with('generate_losses_results_callback')
#         subtask.link_error.assert_called_once_with('generate_losses_error_callback')
#         subtask.delay.assert_called_once()
#         self.assertEqual(analysis.sub_task_statuses.count(), 1)
#         self.assertTrue(
#             analysis.sub_task_statuses.filter(
#                 task_id=task_id, status=AnalysisTaskStatus.status_choices.QUEUED
#             ).exists()
#         )
#
#     def test_generate_inputs_with_multiple_task_params___chord_is_created_correctly(self):
#         analysis = fake_analysis()
#         initiator = fake_user()
#
#         subtasks = [
#             Mock(),
#             Mock(),
#         ]
#
#         body = Mock()
#
#         chord = FakeChord()
#
#         class MockController(BaseController):
#             @classmethod
#             def get_generate_inputs_tasks_params(cls, analysis, initiator):
#                 return [
#                     TaskParams('foo', bar='boo'),
#                     TaskParams('far', boo='bar'),
#                 ]
#
#             @classmethod
#             def get_subtask_signature(cls, analysis, initiator, task_name, params, queue):
#                 return subtasks.pop()
#
#             @classmethod
#             def get_generate_inputs_results_callback(cls, analysis, initiator):
#                 return body
#
#             @classmethod
#             def get_generate_inputs_error_callback(cls, analysis, initiator):
#                 return 'generate_inputs_error_callback'
#
#             @classmethod
#             def get_chord_error_callback(cls):
#                 return 'chord_error_callback'
#
#         with patch('src.server.oasisapi.analyses.task_controller.chord', chord):
#             MockController.generate_inputs(analysis, initiator)
#
#             self.assertEqual(body.link_error.call_count, 2)
#             body.link_error.assert_any_call('generate_inputs_error_callback')
#             body.link_error.assert_any_call('chord_error_callback')
#
#             self.assertEqual(len(chord.head), 2)
#             chord.head[0].s.asset_called_once_with('foo', bar='boo')
#             chord.head[1].s.asset_called_once_with('far', boo='far')
#             self.assertEqual(chord.body, body)
#             self.assertTrue(chord.delay_called)
#
#             self.assertEqual(analysis.sub_task_statuses.count(), 2)
#             self.assertTrue(
#                 analysis.sub_task_statuses.filter(
#                     task_id=chord.task_ids[0], status=AnalysisTaskStatus.status_choices.QUEUED
#                 ).exists()
#             )
#             self.assertTrue(
#                 analysis.sub_task_statuses.filter(
#                     task_id=chord.task_ids[1], status=AnalysisTaskStatus.status_choices.QUEUED
#                 ).exists()
#             )
#
#     def test_generate_losses_with_multiple_task_params___chord_is_created_correctly(self):
#         analysis = fake_analysis()
#         initiator = fake_user()
#
#         subtasks = [
#             Mock(),
#             Mock(),
#         ]
#
#         body = Mock()
#
#         chord = FakeChord()
#
#         class MockController(BaseController):
#             @classmethod
#             def get_generate_losses_tasks_params(cls, analysis, initiator):
#                 return [
#                     TaskParams('foo', bar='boo'),
#                     TaskParams('far', boo='bar'),
#                 ]
#
#             @classmethod
#             def get_subtask_signature(cls, analysis, initiator, task_name, params, queue):
#                 return subtasks.pop()
#
#             @classmethod
#             def get_generate_losses_results_callback(cls, analysis, initiator):
#                 return body
#
#             @classmethod
#             def get_generate_losses_error_callback(cls, analysis, initiator):
#                 return 'generate_losses_error_callback'
#
#             @classmethod
#             def get_chord_error_callback(cls):
#                 return 'chord_error_callback'
#
#         with patch('src.server.oasisapi.analyses.task_controller.chord', chord):
#             MockController.generate_losses(analysis, initiator)
#
#             self.assertEqual(body.link_error.call_count, 2)
#             body.link_error.assert_any_call('generate_losses_error_callback')
#             body.link_error.assert_any_call('chord_error_callback')
#
#             self.assertEqual(len(chord.head), 2)
#             chord.head[0].s.asset_called_once_with('foo', bar='boo')
#             chord.head[1].s.asset_called_once_with('far', boo='far')
#             self.assertEqual(chord.body, body)
#             self.assertTrue(chord.delay_called)
#
#             self.assertEqual(analysis.sub_task_statuses.count(), 2)
#             self.assertTrue(
#                 analysis.sub_task_statuses.filter(
#                     task_id=chord.task_ids[0], status=AnalysisTaskStatus.status_choices.QUEUED
#                 ).exists()
#             )
#             self.assertTrue(
#                 analysis.sub_task_statuses.filter(
#                     task_id=chord.task_ids[1], status=AnalysisTaskStatus.status_choices.QUEUED
#                 ).exists()
#             )

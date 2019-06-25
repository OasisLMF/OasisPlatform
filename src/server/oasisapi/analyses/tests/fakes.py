import six
from celery.states import STARTED
from model_mommy import mommy

from ...files.tests.fakes import fake_related_file
from ..models import Analysis


class FakeAsyncResultFactory(object):
    def __init__(self, target_task_id=None, target_status=STARTED, target_result=None, target_traceback=None):
        self.target_task_id = target_task_id
        self.revoke_kwargs = {}
        self.revoke_called = False
        self.target_status = target_status
        self.target_result = target_result
        self.target_traceback = target_traceback

        class FakeAsyncResult(object):
            def __init__(_self, task_id):
                if task_id != target_task_id:
                    raise ValueError()

                _self.id = task_id
                _self.status = self.target_status
                _self.result = self.target_result
                _self.traceback = self.target_traceback

            def revoke(_self, **kwargs):
                self.revoke_called = True
                self.revoke_kwargs = kwargs

        self.fake_res = FakeAsyncResult

    def __call__(self, task_id):
        return self.fake_res(task_id)


def fake_analysis(**kwargs):
    if isinstance(kwargs.get('input_file'), (six.string_types, six.binary_type)):
        kwargs['input_file'] = fake_related_file(file=kwargs['input_file'])

    if isinstance(kwargs.get('lookup_errors_file'), (six.string_types, six.binary_type)):
        kwargs['lookup_errors_file'] = fake_related_file(file=kwargs['lookup_errors_file'])

    if isinstance(kwargs.get('lookup_success_file'), (six.string_types, six.binary_type)):
        kwargs['lookup_success_file'] = fake_related_file(file=kwargs['lookup_success_file'])

    if isinstance(kwargs.get('lookup_validation_file'), (six.string_types, six.binary_type)):
        kwargs['lookup_validation_file'] = fake_related_file(file=kwargs['lookup_validation_file'])

    if isinstance(kwargs.get('output_file'), (six.string_types, six.binary_type)):
        kwargs['output_file'] = fake_related_file(file=kwargs['output_file'])

    if isinstance(kwargs.get('settings_file'), (six.string_types, six.binary_type)):
        kwargs['settings_file'] = fake_related_file(file=kwargs['settings_file'])

    return mommy.make(Analysis, **kwargs)

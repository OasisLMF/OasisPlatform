import six
from model_mommy import mommy

from ...files.tests.fakes import fake_related_file
from ..models import Analysis


def fake_async_result_factory(target_status, target_task_id, target_result=None, result_traceback=None):
    class FakeAsyncResult(object):
        status = target_status
        result = target_result

        def __init__(self, task_id):
            if task_id != target_task_id:
                raise ValueError()

        def traceback(self):
            return result_traceback

    return FakeAsyncResult


def fake_analysis(**kwargs):
    if isinstance(kwargs.get('input_file'), (six.string_types, six.binary_type)):
        kwargs['input_file'] = fake_related_file(file=kwargs['input_file'])

    if isinstance(kwargs.get('input_errors_file'), (six.string_types, six.binary_type)):
        kwargs['input_errors_file'] = fake_related_file(file=kwargs['input_errors_file'])

    if isinstance(kwargs.get('output_file'), (six.string_types, six.binary_type)):
        kwargs['output_file'] = fake_related_file(file=kwargs['output_file'])

    if isinstance(kwargs.get('settings_file'), (six.string_types, six.binary_type)):
        kwargs['settings_file'] = fake_related_file(file=kwargs['settings_file'])

    return mommy.make(Analysis, **kwargs)

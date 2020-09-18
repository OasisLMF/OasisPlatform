import os
import string
import datetime
from backports.tempfile import TemporaryDirectory

from django.test import override_settings
from hypothesis import given, settings
from hypothesis.extra.django import TestCase
from hypothesis.strategies import text
from pathlib2 import Path

try:
    from hypothesis._strategies import sampled_from
except ModuleNotFoundError:
    from hypothesis.strategies import sampled_from

from ..models import Analysis
from ...auth.tests.fakes import fake_user
from ..tasks import record_run_analysis_result, record_run_analysis_failure, record_generate_input_result, record_generate_input_failure
from .fakes import fake_analysis

# Override default deadline for all tests to 8s
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
                    self.assertEqual(analysis.output_file.file.name, output_location)
                    self.assertEqual(analysis.output_file.content_type, 'application/gzip')
                    self.assertEqual(analysis.output_file.creator, initiator)
                else:
                      self.assertEqual(analysis.output_file, None)

                self.assertEqual(analysis.run_log_file.file.name, log_location)
                self.assertEqual(analysis.run_log_file.content_type, 'application/gzip')
                self.assertEqual(analysis.run_log_file.creator, initiator)

                self.assertEqual(analysis.run_traceback_file.file.name, traceback_location)
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
        traceback_fp=text(min_size=1, max_size=10, alphabet=string.ascii_letters),
    )
    def test_input_file_lookup_files_and_status_are_updated(self, input_location, lookup_error_fp, lookup_success_fp, lookup_validation_fp, summary_levels_fp, traceback_fp):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                Path(d, input_location).touch()
                Path(d, lookup_error_fp).touch()
                Path(d, lookup_success_fp).touch()
                Path(d, lookup_validation_fp).touch()
                Path(d, summary_levels_fp).touch()
                Path(d, traceback_fp).touch()

                initiator = fake_user()
                analysis = fake_analysis()
                return_code = 0

                record_generate_input_result((
                    os.path.join(d, input_location), 
                    os.path.join(d, lookup_error_fp), 
                    os.path.join(d, lookup_success_fp), 
                    os.path.join(d, lookup_validation_fp), 
                    os.path.join(d, summary_levels_fp), 
                    os.path.join(d, traceback_fp), 
                    return_code), analysis.pk, initiator.pk)
                analysis.refresh_from_db()

                self.assertEqual(analysis.input_file.file.name, input_location)
                self.assertEqual(analysis.input_file.content_type, 'application/gzip')
                self.assertEqual(analysis.input_file.creator, initiator)

                self.assertEqual(analysis.lookup_errors_file.file.name, lookup_error_fp)
                self.assertEqual(analysis.lookup_errors_file.content_type, 'text/csv')
                self.assertEqual(analysis.lookup_errors_file.creator, initiator)

                self.assertEqual(analysis.lookup_success_file.file.name, lookup_success_fp)
                self.assertEqual(analysis.lookup_success_file.content_type, 'text/csv')
                self.assertEqual(analysis.lookup_success_file.creator, initiator)

                self.assertEqual(analysis.lookup_validation_file.file.name, lookup_validation_fp)
                self.assertEqual(analysis.lookup_validation_file.content_type, 'application/json')
                self.assertEqual(analysis.lookup_validation_file.creator, initiator)

                self.assertEqual(analysis.summary_levels_file.file.name, summary_levels_fp)
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

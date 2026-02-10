from unittest.mock import patch
from hypothesis.extra.django import TestCase

from src.server.oasisapi.analyses.models import Analysis
from src.server.oasisapi.analyses.v2_api.tests.fakes import fake_analysis
from src.server.oasisapi.auth.tests.fakes import fake_user
from src.server.oasisapi.combine.tasks import record_combine_output
from src.server.oasisapi.files.v2_api.tests.fakes import fake_related_file


class RecordCombineOutput(TestCase):
    def test_success__store_output_and_status_complete(self):
        user = fake_user()
        analysis = fake_analysis()
        mock_related_file = fake_related_file()

        expected_output_path = '/path/to/output.tar.gz'
        result = (True, expected_output_path)

        with patch('src.server.oasisapi.combine.tasks.store_file') as mock_store_file:
            mock_store_file.return_value = mock_related_file

            record_combine_output(result, analysis_id=analysis.pk, user_id=user.pk)
            mock_store_file.assert_called_once_with(
                expected_output_path, 'application/gzip', user,
                filename=f'analysis_{analysis.pk}_outputs.tar.gz'
            )

            analysis.refresh_from_db()
            self.assertEqual(analysis.output_file, mock_related_file)
            self.assertEqual(analysis.status, Analysis.status_choices.RUN_COMPLETED)

    def test_error__creates_error_file_and_error_status(self):
        user = fake_user()
        analysis = fake_analysis()
        mock_related_file = fake_related_file()

        expected_error_traceback = 'Combine failed: Testing combine failure'
        result = (False, expected_error_traceback)

        with (patch('src.server.oasisapi.combine.tasks.RelatedFile.objects.create') as mock_create,
              patch('src.server.oasisapi.combine.tasks.ContentFile') as mock_file):
            mock_create.return_value = mock_related_file

            record_combine_output(result, analysis_id=analysis.pk, user_id=user.pk)
            mock_create.assert_called_once()
            call_args = mock_create.call_args[1]
            self.assertEqual(call_args['creator'], user)
            self.assertEqual(call_args['content_type'], 'text/plain')
            mock_file.assert_called_once()
            call_args = mock_file.call_args[1]
            self.assertEqual(call_args['content'], expected_error_traceback)

            analysis.refresh_from_db()
            self.assertEqual(analysis.run_traceback_file, mock_related_file)
            self.assertEqual(analysis.status, Analysis.status_choices.RUN_ERROR)

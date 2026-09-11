import logging
import os
from tempfile import NamedTemporaryFile
from unittest import TestCase

from src.model_execution_worker.utils import LoggingTaskContext


def _free_log_path():
    """ Returns a filesystem path that does not exist yet, but is safe to write to. """
    with NamedTemporaryFile(delete=False) as f:
        path = f.name
    os.remove(path)
    return path


class LoggingTaskContextTests(TestCase):
    def setUp(self):
        self.log_path = _free_log_path()

    def tearDown(self):
        if os.path.isfile(self.log_path):
            os.remove(self.log_path)

    def test_clean_exit___log_file_is_deleted(self):
        logger = logging.getLogger('test-logging-task-context-clean-exit')

        with LoggingTaskContext(logger, log_filename=self.log_path, level='INFO'):
            logger.info('some task output')

        self.assertFalse(os.path.isfile(self.log_path))

    def test_exception_during_task___log_file_is_preserved_with_its_content(self):
        logger = logging.getLogger('test-logging-task-context-exception')

        with self.assertRaises(ValueError):
            with LoggingTaskContext(logger, log_filename=self.log_path, level='INFO'):
                logger.info('KERNEL_STDERR:\nboom')
                logger.info('STDOUT:\nfailure output')
                raise ValueError('task failed')

        # The log file (including any KERNEL_STDERR/STDOUT output logged before the
        # failure) must survive so a 'task_failure' handler can still upload it.
        self.assertTrue(os.path.isfile(self.log_path))
        with open(self.log_path) as f:
            content = f.read()
        self.assertIn('KERNEL_STDERR', content)
        self.assertIn('STDOUT', content)

    def test_delete_on_exit_false___log_file_is_preserved_even_on_clean_exit(self):
        logger = logging.getLogger('test-logging-task-context-no-delete')

        with LoggingTaskContext(logger, log_filename=self.log_path, level='INFO', delete_on_exit=False):
            logger.info('some task output')

        self.assertTrue(os.path.isfile(self.log_path))

    def test_handler_and_filter_are_always_removed_regardless_of_outcome(self):
        logger = logging.getLogger('test-logging-task-context-cleanup')
        initial_handlers = list(logger.handlers)
        initial_filters = list(logger.filters)

        with self.assertRaises(ValueError):
            with LoggingTaskContext(logger, log_filename=self.log_path, level='DEBUG'):
                raise ValueError('task failed')

        self.assertEqual(logger.handlers, initial_handlers)
        self.assertEqual(logger.filters, initial_filters)

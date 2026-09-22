import logging
import os
import threading
from tempfile import TemporaryDirectory
from unittest import TestCase

from src.model_execution_worker.utils import LoggingTaskContext


class LoggingTaskContextThreadIsolation(TestCase):
    def test_concurrent_tasks_do_not_leak_into_each_others_log_file(self):
        with TemporaryDirectory() as tmp_dir:
            log_a = os.path.join(tmp_dir, 'chunk-a.log')
            log_b = os.path.join(tmp_dir, 'chunk-b.log')

            a_holding_context = threading.Event()
            b_done = threading.Event()

            def run_a():
                with LoggingTaskContext(logging.getLogger(), log_filename=log_a, level='INFO', delete_on_exit=False):
                    logging.info('chunk-a-start')
                    a_holding_context.set()
                    b_done.wait(timeout=5)
                    logging.info('chunk-a-end')

            def run_b():
                a_holding_context.wait(timeout=5)
                with LoggingTaskContext(logging.getLogger(), log_filename=log_b, level='INFO', delete_on_exit=False):
                    logging.info('chunk-b-start')
                    logging.info('chunk-b-end')
                b_done.set()

            t_a = threading.Thread(target=run_a)
            t_b = threading.Thread(target=run_b)
            t_a.start()
            t_b.start()
            t_a.join(timeout=5)
            t_b.join(timeout=5)

            with open(log_a) as f:
                content_a = f.read()
            with open(log_b) as f:
                content_b = f.read()

            self.assertIn('chunk-a-start', content_a)
            self.assertIn('chunk-a-end', content_a)
            self.assertNotIn('chunk-b-start', content_a)
            self.assertNotIn('chunk-b-end', content_a)

            self.assertIn('chunk-b-start', content_b)
            self.assertIn('chunk-b-end', content_b)
            self.assertNotIn('chunk-a-start', content_b)
            self.assertNotIn('chunk-a-end', content_b)


class LoggingTaskContextLevelIsolation(TestCase):
    def test_one_tasks_exit_does_not_drop_a_still_running_siblings_level(self):
        """ Regression test: A exiting used to reset the root logger's level to its
            own pre-entry baseline, dropping B's DEBUG logging while B was still running.
        """
        root_logger = logging.getLogger()
        original_level = root_logger.level
        root_logger.setLevel(logging.WARNING)
        try:
            with TemporaryDirectory() as tmp_dir:
                log_b = os.path.join(tmp_dir, 'chunk-b.log')

                a_entered = threading.Event()
                b_entered = threading.Event()
                a_exited = threading.Event()

                def run_a():
                    with LoggingTaskContext(root_logger, log_filename=os.path.join(tmp_dir, 'chunk-a.log'),
                                            level='DEBUG', delete_on_exit=False):
                        a_entered.set()
                        b_entered.wait(timeout=5)
                        # A exits first, while B is still running (crossing overlap, not nested)
                    a_exited.set()

                def run_b():
                    a_entered.wait(timeout=5)
                    with LoggingTaskContext(root_logger, log_filename=log_b, level='DEBUG', delete_on_exit=False):
                        b_entered.set()
                        a_exited.wait(timeout=5)
                        logging.debug('b-debug-after-a-exits')

                t_a = threading.Thread(target=run_a)
                t_b = threading.Thread(target=run_b)
                t_a.start()
                t_b.start()
                t_a.join(timeout=5)
                t_b.join(timeout=5)

                with open(log_b) as f:
                    content_b = f.read()

                self.assertIn('b-debug-after-a-exits', content_b)
                self.assertEqual(root_logger.level, logging.WARNING)
        finally:
            root_logger.setLevel(original_level)

from random import randint
from unittest import TestCase

import os

from src.server import app
from src.server.settings import settings


class AppTestCase(TestCase):
    def setUp(self):
        self._init_testing = app.APP.config['TESTING']
        self.app = app.APP.test_client()

    def tearDown(self):
        app.APP.config['TESTING'] = self._init_testing

    def create_input_file(self, path, size_in_bytes=None, data=b''):
        path = os.path.join(settings['INPUTS_DATA_DIRECTORY'], path)

        with open(path, 'wb') as outfile:
            for x in xrange(size_in_bytes or 0):
                outfile.write(chr(randint(0, 255)))

            outfile.write(data)

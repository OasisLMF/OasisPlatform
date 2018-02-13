import string
from unittest import TestCase

import os
from hypothesis import given
from hypothesis.strategies import text

from src.conf.settings import Settings


def setting_text():
    return text(min_size=1, alphabet=string.ascii_letters)


class SettingsGet(TestCase):
    def setUp(self):
        self.init_env = os.environ.copy()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.init_env)

    @given(setting_text(), setting_text())
    def test_variable_is_set_in_section_and_default___section_value_is_returned(self, section, default):
        settings = Settings()

        settings.read_dict({
            'default': {'foo': default},
            'section': {'foo': section}
        })

        self.assertEqual(settings.get('section', 'foo'), section)

    @given(setting_text(), setting_text())
    def test_variable_is_set_in_default___default_value_is_returned(self, section, default):
        settings = Settings()

        settings.read_dict({
            'default': {'foo': default},
            'section': {'other': section}
        })

        self.assertEqual(settings.get('section', 'foo'), default)

    @given(setting_text(), setting_text(), setting_text())
    def test_variable_is_set_in_global_env_setting_and_default___env_value_is_returned(self, section, default, env):
        os.environ['OASIS_API_foo'] = env

        settings = Settings()

        settings.read_dict({
            'default': {'foo': default},
            'section': {'env': section}
        })

        self.assertEqual(settings.get('section', 'foo'), env)

    @given(setting_text(), setting_text(), setting_text(), setting_text())
    def test_variable_is_set_in_global_and_section_env_setting_and_default___setting_env_value_is_returned(self, section, default, global_env, section_env):
        os.environ['OASIS_API_foo'] = global_env
        os.environ['OASIS_API_SECTION_foo'] = section_env

        settings = Settings()

        settings.read_dict({
            'default': {'foo': default},
            'section': {'env': section}
        })

        self.assertEqual(settings.get('section', 'foo'), section_env)

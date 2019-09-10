from __future__ import unicode_literals, absolute_import

import string
from tempfile import NamedTemporaryFile
from unittest import TestCase

import os
from hypothesis import given, settings
from hypothesis.strategies import text, integers
from mock import patch

from src.conf.iniconf import Settings

# Override default deadline for all tests to 8s
settings.register_profile("ci", deadline=800.0)
settings.load_profile("ci")


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
        os.environ['OASIS_foo'] = env

        settings = Settings()

        settings.read_dict({
            'default': {'foo': default},
            'section': {'env': section}
        })

        self.assertEqual(settings.get('section', 'foo'), env)

    @given(setting_text(), setting_text(), setting_text(), setting_text())
    def test_variable_is_set_in_global_and_section_env_setting_and_default___setting_env_value_is_returned(self, section, default, global_env, section_env):
        os.environ['OASIS_foo'] = global_env
        os.environ['OASIS_SECTION_foo'] = section_env

        settings = Settings()

        settings.read_dict({
            'default': {'foo': default},
            'section': {'env': section}
        })

        self.assertEqual(settings.get('section', 'foo'), section_env)

    @given(setting_text())
    def test_config_file_is_set_in_environment_variable___specified_values_are_from_new_config_others_are_default(self, value):
        with NamedTemporaryFile('w') as f:
            f.writelines([
                '[default]\n',
                'LOG_LEVEL = {}\n'.format(value)
            ])
            f.flush()
            os.environ['OASIS_INI_PATH'] = f.name

            settings = Settings()

            self.assertEqual(settings.get('default', 'LOG_LEVEL'), value)
            self.assertEqual(settings.get('default', 'MEDIA_ROOT'), '/shared-fs/')


class SettingsSetupLogging(TestCase):
    @given(setting_text(), setting_text(), setting_text(), integers(), integers())
    def test_oasis_logging_is_setup_correctly(self, path, name, level, size, count):
        with patch('src.conf.iniconf.read_log_config') as log_conf_mock:
            settings = Settings()
            settings.add_section('newsection')
            settings.update({
                'newsection': {
                    'LOG_FILENAME': name,
                    'LOG_DIRECTORY': path,
                    'LOG_LEVEL': level,
                    'LOG_MAX_SIZE_IN_BYTES': size,
                    'LOG_BACKUP_COUNT': count,
                }
            })

            settings.setup_logging('newsection')

            log_conf_mock.assert_called_once_with({
                'LOG_FILE': os.path.join(path, name),
                'LOG_LEVEL': level,
                'LOG_MAX_SIZE_IN_BYTES': size,
                'LOG_BACKUP_COUNT': count,
            })

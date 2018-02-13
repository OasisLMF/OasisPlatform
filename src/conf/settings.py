from __future__ import absolute_import, unicode_literals

import os

from chainmap import ChainMap

from configparser import ConfigParser

from oasislmf.utils.log import read_log_config


class Settings(ConfigParser):
    default_log_format = '%(asctime)s - %(levelname)s - %(message)s'

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('default_section', 'default')

        super(Settings, self).__init__(*args, **kwargs)

        ini_files = [os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, 'conf.ini')]

        specified_ini = os.environ.get('OASIS_API_INI_PATH', None)
        if specified_ini and os.path.exists(specified_ini):
            ini_files.append(specified_ini)

        self.read(ini_files)

    def _get_section_env_vars(self, section):
        section_env_prefix = 'OASIS_API_{}_'.format(section.upper())
        global_env_prefix = 'OASIS_API_'

        return ChainMap(
            {k.replace(section_env_prefix, ''): v for k, v in os.environ.items() if k.startswith(section_env_prefix)},
            {k.replace(global_env_prefix, ''): v for k, v in os.environ.items() if k.startswith(global_env_prefix)},
        )

    def get(self, section, option, **kwargs):
        kwargs.setdefault('vars', self._get_section_env_vars(section))
        return super(Settings, self).get(section, option, **kwargs)

    def replace(self, new):
        self.clear()
        self.update(new)

    def setup_logging(self, section):
        """
        Read an Oasis standard logging config
        """
        log_dir = self.get(section, 'LOG_DIRECTORY', fallback=self.default_log_format)
        log_filename = self.get(section, 'LOG_FILENAME', fallback=self.default_log_format)
        log_path = os.path.join(log_dir, log_filename)

        read_log_config({
            'LOG_FILE': log_path,
            'LOG_LEVEL': self.get(section, 'LOG_LEVEL', fallback='DEBUG'),
            'LOG_MAX_SIZE_IN_BYTES': self.getint(section, 'LOG_MAX_SIZE_IN_BYTES', fallback=10240),
            'LOG_BACKUP_COUNT': self.getint(section, 'LOG_BACKUP_COUNT', fallback=5),
        })


settings = Settings()


class SettingsPatcher(object):
    def __init__(self, to_patch=None, **globals):
        self._initial = {k: dict(v.items()) for k, v in settings.items()}
        self._to_patch = to_patch or {}
        self._globals = globals

    def __enter__(self):
        if self._globals:
            for k, v in settings.items():
                v.update(self._globals)

        if self._to_patch:
            settings.update(self._to_patch)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.revert()

    def revert(self):
        settings.read_dict(self._initial)

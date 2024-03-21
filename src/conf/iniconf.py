from __future__ import absolute_import, unicode_literals

import logging
import os

from datetime import timedelta
from logging.handlers import RotatingFileHandler

from chainmap import ChainMap

from configparser import ConfigParser


def read_log_config(config_parser):
    """
    Read an Oasis standard logging config
    """
    log_file = config_parser['LOG_FILE']
    log_level = config_parser['LOG_LEVEL']
    log_max_size_in_bytes = int(config_parser['LOG_MAX_SIZE_IN_BYTES'])
    log_backup_count = int(config_parser['LOG_BACKUP_COUNT'])

    log_dir = os.path.dirname(log_file)
    os.makedirs(log_dir, exist_ok=True)

    handler = RotatingFileHandler(
        log_file, maxBytes=log_max_size_in_bytes,
        backupCount=log_backup_count)
    logging.getLogger().setLevel(log_level)
    logging.getLogger().addHandler(handler)
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)


class Settings(ConfigParser):
    def __init__(self, *args, global_env=True, **kwargs):
        kwargs.setdefault('default_section', 'default')
        self.global_env = global_env
        super(Settings, self).__init__(*args, **kwargs)

        ini_files = [os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, 'conf.ini')]

        specified_ini = os.environ.get('OASIS_INI_PATH', None)
        if specified_ini and os.path.exists(specified_ini):
            ini_files.append(specified_ini)

        self.read(ini_files)

    def _section_to_env_prefix(self, section):
        return '_'.join(section.split('.')).upper()

    def _get_section_env_vars(self, section):
        section_env_prefix = 'OASIS_{}_'.format(self._section_to_env_prefix(section))

        if self.global_env:
            global_env_prefix = 'OASIS_'
        else:
            global_env_prefix = section_env_prefix

        return ChainMap(
            {k.replace(section_env_prefix, ''):
                v for k, v in os.environ.items() if k.startswith(section_env_prefix)},
            {k.replace(global_env_prefix, ''):
                v for k, v in os.environ.items() if k.startswith(global_env_prefix)},
        )

    def get(self, section, option, global_env=True, **kwargs):
        if not option:
            section_env_prefix = 'OASIS_{}_'.format(self._section_to_env_prefix(section))
            from_env = {
                k.replace(section_env_prefix, '').lower():
                v for k, v in os.environ.items() if k.startswith(section_env_prefix)
            }
            try:
                res = self[section]
                res = dict(res.items())
            except KeyError:
                res = {}

            return {
                **res,
                **from_env,
            }
        else:
            kwargs.setdefault('vars', self._get_section_env_vars(section))
            return super(Settings, self).get(section, option, **kwargs)

    def getint(self, section, option, **kwargs):
        kwargs.setdefault('vars', self._get_section_env_vars(section))
        return super(Settings, self).getint(section, option, **kwargs)

    def get_timedelta(self, section, option, **kwargs):
        ''' Use for reading timedelta argument strings and returns a timedelta
            object

            Example
            =======
            in: settings.get_timedelta('server', 'TOKEN_ACCESS_LIFETIME', fallback='days=5')
            out: datetime.timedelta(days=5)
        '''
        kwargs.setdefault('vars', self._get_section_env_vars(section))
        kwargs_string = super(Settings, self).get(section, option, **kwargs)
        try:
            kwargs = {k.split('=')[0].strip(): int(k.split('=')[1])
                      for k in kwargs_string.split(',')}
        except (TypeError, IndexError):
            kwargs = {k.split('=')[0].strip(): int(k.split('=')[1])
                      for k in kwargs['fallback'].split(',')}
        return timedelta(**kwargs)

    def getboolean(self, section, option, **kwargs):
        kwargs.setdefault('vars', self._get_section_env_vars(section))
        return super(Settings, self).getboolean(section, option, **kwargs)

    def setup_logging(self, section):
        """
        Read an Oasis standard logging config
        """
        log_dir = self.get(section, 'LOG_DIRECTORY')
        log_filename = self.get(section, 'LOG_FILENAME')
        log_path = os.path.join(log_dir, log_filename)

        read_log_config({
            'LOG_FILE': log_path,
            'LOG_LEVEL': self.get(section, 'LOG_LEVEL'),
            'LOG_MAX_SIZE_IN_BYTES': self.getint(section, 'LOG_MAX_SIZE_IN_BYTES'),
            'LOG_BACKUP_COUNT': self.getint(section, 'LOG_BACKUP_COUNT'),
        })


settings = Settings()
settings_local = Settings(global_env=False)  # only returns envs within a set section


class SettingsPatcher(object):
    def __init__(self, **to_patch):
        self._initial = {k: dict(v.items()) for k, v in settings.items()}
        self._to_patch = to_patch

    def __enter__(self):
        for k, v in settings.items():
            v.update(self._to_patch)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.revert()

    def revert(self):
        settings.read_dict(self._initial)

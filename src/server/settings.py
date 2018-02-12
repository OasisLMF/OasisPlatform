import os

import six
from oasislmf.utils.conf import load_ini_file
from oasislmf.utils.log import read_log_config


class Settings(dict):
    def __init__(self):
        self._ini_path = os.environ.get('SERVER_INI_PATH', os.path.join(os.path.dirname(__file__), 'OasisApi.ini'))

        _dict = load_ini_file(self._ini_path)
        _dict.update(self.load_env())
        _dict.update(
            {
                'LOG_FILE': _dict['LOG_FILE'].replace('%LOG_DIRECTORY%', _dict['LOG_DIRECTORY'])
            }
        )
        read_log_config(_dict)
        super(Settings, self).__init__(**_dict)

    def load_env(self):
        return {
            k.replace('OASIS_API_', ''): v for k, v in filter(lambda kv: kv[0].startswith('OASIS_API_'), six.iteritems(os.environ))
        }

    def replace(self, new):
        self.clear()
        self.update(new)


settings = Settings()


class SettingsPatcher(object):
    def __init__(self, **to_patch):
        self._initital = settings.copy()
        self._to_patch = to_patch

    def __enter__(self):
        settings.update(self._to_patch)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.revert()

    def revert(self):
        settings.replace(self._initital)


def override_settings(**to_patch):
    def wrapper(fn, *args, **kwargs):
        with SettingsPatcher(**to_patch):
            return fn(*args, **kwargs)

    return wrapper

from .models import User
import importlib


class InvalidAuthBackend(ValueError):
    def __init__(self, *args, **kwargs):
        super(InvalidAuthBackend, self).__init__('invalid AUTH_BACKEND')


class InvalidUserException(Exception):
    pass


class DefaultAuthBackend(object):
    def authenticate(**credentials):
        from .models import check_hash
        password = credentials.get('password', '')
        username = credentials.get('username', '')

        user = User.query.filter_by(username=username).first()

        if user is None:
            check_hash(password, password)
            raise InvalidUserException()

        if not user.default_credentials.check_password(password):
            raise InvalidUserException()

        return user


def load_auth_backend(app):
    backend_path = app.config['AUTH_BACKEND']
    if not backend_path:
        return DefaultAuthBackend()

    if '.' not in backend_path:
        raise InvalidAuthBackend()

    mod, cls = backend_path.rsplit('.', 1)
    backend_mod = importlib.import_module(mod)
    try:
        return getattr(backend_mod, cls)
    except AttributeError:
        raise ImportError(backend_path)

from src.server.models import db, DefaultCredentials, User
from src.server.auth_backend import DefaultAuthBackend, load_auth_backend, InvalidAuthBackend
from .base import AppTestCase


class FakeAuthBackend(object):
    pass


class Authentication(AppTestCase):
    def setUp(self):
        super(Authentication, self).setUp()
        # self.username = 'dirk'
        # self.user = user_datastore.create_user(username=self.username, password=self.password)
        # db.session.commit()

    def test_load_authentication_backend___backend_returned(self):
        with self.app.app_context() as ctx:
            ctx.app.config['AUTH_BACKEND'] = 'tests.test_auth.FakeAuthBackend'
            backend = load_auth_backend(self.app)
            self.assertEqual(backend, FakeAuthBackend)

    def test_load_missing_authentication_backend___exception_is_raised(self):
        with self.app.app_context() as ctx:
            ctx.app.config['AUTH_BACKEND'] = 'tests.test_auth.MissingBackend'
            with self.assertRaises(ImportError) as ex:
                load_auth_backend(self.app)
            self.assertEqual('tests.test_auth.MissingBackend', str(ex.exception))

    def test_load_invalid_authentication_backend___exception_is_raised(self):
        with self.app.app_context() as ctx:
            ctx.app.config['AUTH_BACKEND'] = 'foo'
            with self.assertRaises(InvalidAuthBackend) as ex:
                load_auth_backend(self.app)
            self.assertEqual('invalid AUTH_BACKEND', str(ex.exception))

    def test_load_default_backend___default_backend_returned(self):
        # Create default user
        username = 'foo'
        password = 'bar'
        creds = DefaultCredentials.create(username=username, password=password)

        # Authenticate user
        backend = load_auth_backend(self.app)
        user = backend.authenticate(username=username, password=password)
        self.assertEqual(user.id, creds.user.id)

    # def test_authenticate_with_default_backend___user_id_returned(self):
    #     raise Exception('implement this')

    # def test_authenticate_with_custom_backend___user_id_returned(self):
    #     raise Exception('implement this')

    # def test_fail_authenticate_with_custom_backend___exception_raised(self):
    #     raise Exception('implement this')

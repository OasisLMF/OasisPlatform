"""The celery results DB URI only gets the PostgreSQL ``sslmode`` option by default for PostgreSQL (#1228)."""
import importlib
import os
from unittest import TestCase

from mock import patch

import src.conf.base as conf_base
from src.conf.base import default_db_ssl_mode

DB_ENV = {
    'OASIS_CELERY_DB_USER': 'celery',
    'OASIS_CELERY_DB_PASS': 'password',
    'OASIS_CELERY_DB_HOST': 'celery-db',
    'OASIS_CELERY_DB_PORT': '3306',
}


def result_backend(**env):
    environ = {k: v for k, v in os.environ.items() if not k.startswith('OASIS_CELERY_DB_')}
    with patch.dict(os.environ, {**environ, **DB_ENV, **env}, clear=True):
        return importlib.reload(conf_base).CELERY_RESULT_BACKEND


class DefaultDbSslMode(TestCase):
    def tearDown(self):
        importlib.reload(conf_base)

    def test_postgres_engines_default_to_sslmode_prefer(self):
        for engine in ('db+postgresql+psycopg', 'db+postgresql+psycopg2', 'db+postgresql', 'db+PostgreSQL'):
            self.assertEqual(default_db_ssl_mode(engine), '?sslmode=prefer')

    def test_other_engines_get_no_sslmode(self):
        for engine in ('db+mysql+pymysql', 'db+mysql', 'db+mssql+pyodbc', '', None):
            self.assertEqual(default_db_ssl_mode(engine), '')

    def test_mysql_uri_has_no_sslmode(self):
        uri = result_backend(OASIS_CELERY_DB_ENGINE='db+mysql+pymysql')
        self.assertEqual(uri, 'db+mysql+pymysql://celery:password@celery-db:3306/celery')

    def test_postgres_uri_keeps_sslmode_prefer(self):
        uri = result_backend(OASIS_CELERY_DB_ENGINE='db+postgresql+psycopg', OASIS_CELERY_DB_PORT='5432')
        self.assertEqual(uri, 'db+postgresql+psycopg://celery:password@celery-db:5432/celery?sslmode=prefer')

    def test_explicit_ssl_mode_still_overrides(self):
        uri = result_backend(OASIS_CELERY_DB_ENGINE='db+postgresql+psycopg', OASIS_CELERY_DB_PORT='5432',
                             OASIS_CELERY_DB_SSL_MODE='?sslmode=require')
        self.assertTrue(uri.endswith('/celery?sslmode=require'))
        uri = result_backend(OASIS_CELERY_DB_ENGINE='db+mysql+pymysql', OASIS_CELERY_DB_SSL_MODE='?ssl=true')
        self.assertTrue(uri.endswith('/celery?ssl=true'))

import threading
from datetime import datetime, timedelta

from sqlalchemy import event
from sqlalchemy.engine.url import make_url

from celery.backends.database import DatabaseBackend
from celery.backends.database.session import SessionManager
from celery.exceptions import BackendError

from celery import current_app

import logging

import importlib
import urllib
from src.conf.iniconf import settings


logger = logging.getLogger(__name__)



def import_class_from_string(class_path: str):
    """Import a class from a string path like 'module.submodule.ClassName'."""
    module_path, class_name = class_path.rsplit('.', 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)






class TokenSessionManager(SessionManager):
    """
    A custom SessionManager that attaches an event listener to any engine
    it creates. This is the reliable way to inject our token logic.
    """
    def __init__(self, backend, *args, **kwargs):
        self.backend = backend  # Keep a reference to our backend instance
        super().__init__(*args, **kwargs)
        self._init_token_provider()



    def _init_token_provider(self):
        """Initialize the token provider from configuration."""
        # Get token provider class from config
        token_class_path = current_app.conf.get('CELERY_BACKEND_TOKEN_CLASS')
        if not token_class_path:
            raise ValueError("CELERY_BACKEND_TOKEN_CLASS must be configured")

        # Get token provider config
        token_config = current_app.conf.get('CELERY_BACKEND_TOKEN_CONFIG', {})

        # Import and instantiate the token provider
        TokenProviderClass = import_class_from_string(token_class_path)
        self.token_provider = TokenProviderClass(**token_config)
        print(f"Initialized token provider: {TokenProviderClass.__name__}")




    def get_engine(self, dburi, **kwargs):
        # Always get fresh token before creating engine
        #self.backend._ensure_token_valid()
        #
        ## Update the URI with fresh token
        from celery.contrib import rdb; rdb.set_trace()
        token_url = make_url(dburi)
        token_url = token_url.set(password=self.token_provider.get_token())
        engine = super().get_engine(token_url, **kwargs)




        ## this should be called when establishing a connection
        #@event.listens_for(engine, "connect")
        #def _on_connect(dbapi_connection, connection_record):
        #    logger.info("New connection established")

        ## this is called when connection failed
        #@event.listens_for(engine, "invalidate")
        #def _on_invalidate(dbapi_connection, connection_record, exception):
        #    logger.info(f"Connection invalidated: {exception}")
        #    # Next connection attempt will call get_engine again


        @event.listens_for(engine, "handle_error")
        def handle_token_error(exception_context):
            from celery.contrib import rdb; rdb.set_trace()
            error_msg = str(exception_context.original_exception).lower()
            logger.info(f"Error with DB connection: {error_msg}")

            ## Check if it's a token/auth related error
            if any(pattern in error_msg for pattern in [
                'authentication failed', 'access denied', 'token expired',
                'invalid authorization', 'password authentication failed'
            ]):
                logger.info("Token authentication failed, refreshing...")
                self.token_provider.force_refresh()

                # Invalidate current connections to force new ones
                engine.dispose()

                # Optionally return True to suppress the original error
                # and let SQLAlchemy retry with the new token
                return True



            #
            #    # Refresh the token
            #    self.backend._ensure_token_valid()
            #
            #    # Update connection info for future connections
            #    from sqlalchemy.engine.url import make_url
            #    url = make_url(dburi)
            #    url = url.set(password=self.backend._token)
            #
            #    engine.dispose()
            #


        return engine





class AuthTokenDatabaseBackend(DatabaseBackend):
    """
    A custom Celery result backend that subclasses the standard DatabaseBackend
    to handle expiring database tokens (e.g., IAM tokens for PostgreSQL/MySQL).
    """
    def __init__(self, dburi=None, *args, **kwargs):
        logger.info("RUNNING CELERY CUSTOM RESULTS DB BACKEND")
        super().__init__(dburi=self._get_database_connection_string(), *args, **kwargs)


    def _get_database_connection_string(self):

        # Load DB connection string
        dburi = '{DB_ENGINE}://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}{SSL_MODE}'.format(
            #DB_ENGINE=settings.get('celery', 'db_engine'),
            DB_ENGINE='postgresql+psycopg',   # <---- must strip out 'DB+' if set
            DB_USER=urllib.parse.quote(settings.get('celery', 'db_user')),
            #DB_PASS=urllib.parse.quote(settings.get('celery', 'db_pass'), '%PLACEHOLDER%'),
            DB_PASS="%PLACEHOLDER%", 
            DB_HOST=settings.get('celery', 'db_host'),
            DB_PORT=settings.get('celery', 'db_port'),
            DB_NAME=settings.get('celery', 'db_name', fallback='celery'),
            SSL_MODE=settings.get('celery', 'db_ssl_mode', fallback='?sslmode=prefer'),
        )
        return dburi


    # Load custom session Manager
    def ResultSession(self):
        session_manager=TokenSessionManager(backend=self)
        return session_manager.session_factory(
            dburi=self.url,
            short_lived_sessions=self.short_lived_sessions,
            **self.engine_options)


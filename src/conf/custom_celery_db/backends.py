import threading
from datetime import datetime, timedelta

from sqlalchemy import event
from celery.backends.database import DatabaseBackend
from celery.backends.database.session import SessionManager
from celery.exceptions import BackendError

import logging

import urllib
from src.conf.iniconf import settings


logger = logging.getLogger(__name__)


class ExpiringTokenSessionManager(SessionManager):
    """
    A custom SessionManager that attaches an event listener to any engine
    it creates. This is the reliable way to inject our token logic.
    """
    def __init__(self, backend, *args, **kwargs):
        self.backend = backend  # Keep a reference to our backend instance
        super().__init__(*args, **kwargs)

    def get_engine(self, dburi, **kwargs):
        # Always get fresh token before creating engine
        #self.backend._ensure_token_valid()
        #
        ## Update the URI with fresh token
        #from sqlalchemy.engine.url import make_url
        #url = make_url(dburi)
        #url = url.set(password=self.backend._token)
        #
        engine = super().get_engine(dburi, **kwargs)

        # this should be called when establishing a connection
        @event.listens_for(engine, "connect")
        def _on_connect(dbapi_connection, connection_record):
            logger.info("New connection established")

        # this is called when connection failed
        @event.listens_for(engine, "invalidate")
        def _on_invalidate(dbapi_connection, connection_record, exception):
            logger.info(f"Connection invalidated: {exception}")
            # Next connection attempt will call get_engine again


        @event.listens_for(engine, "handle_error")
        def handle_token_error(exception_context):
            from celery.contrib import rdb; rdb.set_trace()
            error_msg = str(exception_context.original_exception).lower()
            
            ## Check if it's a token/auth related error
            #if any(pattern in error_msg for pattern in [
            #    'authentication failed', 'access denied', 'token expired',
            #    'invalid authorization', 'password authentication failed'
            #]):
            #    print("Token authentication failed, refreshing...")
            #    
            #    # Refresh the token
            #    self.backend._ensure_token_valid()
            #    
            #    # Update connection info for future connections
            #    from sqlalchemy.engine.url import make_url
            #    url = make_url(dburi)
            #    url = url.set(password=self.backend._token)
            #    
            #    # Invalidate current connections to force new ones
            #    engine.dispose()
            #    
            #    # Optionally return True to suppress the original error
            #    # and let SQLAlchemy retry with the new token
            #    return True


        return engine





class ExpiringTokenDatabaseBackend(DatabaseBackend):
    """
    A custom Celery result backend that subclasses the standard DatabaseBackend
    to handle expiring database tokens (e.g., IAM tokens for PostgreSQL/MySQL).
    """
    def __init__(self, dburi=None, *args, **kwargs):
        logger.info("RUNNING CELERY CUSTOM RESULTS DB BACKEND")
        # # We keep our token management logic
        # self._token = None
        # self._token_expiry = None
        # self._token_lock = threading.Lock()

        # # Important: Call super().__init__ AFTER setting up the lock
        # # because the parent __init__ will call `_create_engine`.

        #from celery.contrib import rdb; rdb.set_trace()

        new_dburi = '{DB_ENGINE}://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}{SSL_MODE}'.format(
            #DB_ENGINE=settings.get('celery', 'db_engine'),
            DB_ENGINE='postgresql+psycopg',
            #DB_USER=urllib.parse.quote(settings.get('celery', 'db_user')),
            DB_USER='INVALID',
            DB_PASS=urllib.parse.quote(settings.get('celery', 'db_pass')),
            DB_HOST=settings.get('celery', 'db_host'),
            DB_PORT=settings.get('celery', 'db_port'),
            DB_NAME=settings.get('celery', 'db_name', fallback='celery'),
            SSL_MODE=settings.get('celery', 'db_ssl_mode', fallback='?sslmode=prefer'),
        )
        super().__init__(dburi=new_dburi, *args, **kwargs)


    def ResultSession(self):
        # from celery.contrib import rdb; rdb.set_trace()
        session_manager=ExpiringTokenSessionManager(backend=self)
        return session_manager.session_factory(
            dburi=self.url,
            short_lived_sessions=self.short_lived_sessions,
            **self.engine_options)




    def _get_new_token(self):
        """Fetches a new database token."""
        # Your actual token fetching logic (e.g., from AWS, Google Cloud, etc.)
        print(f"[{datetime.utcnow().isoformat()}] FETCHING NEW DATABASE TOKEN...")
        #new_token = f"db_token_{int(datetime.utcnow().timestamp())}"
        #expiry_time = datetime.utcnow() + timedelta(minutes=10)
        #print(f"[{datetime.utcnow().isoformat()}] NEW TOKEN ACQUIRED...")
        #return new_token, expiry_time

    def _ensure_token_valid(self):
        """Ensures the current token is valid, refreshing if needed."""
        return True
        # Use a buffer to refresh token before it expires
        #if self._token is None or datetime.utcnow() > self._token_expiry - timedelta(seconds=60):
        #    with self._token_lock:
        #        # Double-checked locking
        #        if self._token is None or datetime.utcnow() > self._token_expiry - timedelta(seconds=60):
        #            self._token, self._token_expiry = self._get_new_token()


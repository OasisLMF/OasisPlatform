import threading
from datetime import datetime, timedelta

from sqlalchemy import event
from celery.backends.database import DatabaseBackend
from celery.backends.database.session import SessionManager
from celery.exceptions import BackendError


import urllib
from src.conf.iniconf import settings




class ExpiringTokenSessionManager(SessionManager):
    """
    A custom SessionManager that attaches an event listener to any engine
    it creates. This is the reliable way to inject our token logic.
    """
    def __init__(self, backend, *args, **kwargs):
        self.backend = backend  # Keep a reference to our backend instance
        super().__init__(*args, **kwargs)

    def create_session(self, dburi, **kwargs):
        """
        This method IS called every time a new engine is created.
        We override it to attach our listener.
        """
        # Create the engine as normal
        from celery.contrib import rdb; rdb.set_trace()
        engine = super().get_engine(dburi, **kwargs)

        # Now, attach the listener that will inject the fresh token
        @event.listens_for(engine, "do_connect")
        def _do_connect(dialect, conn_rec, cargs, ckwargs):
            print("CUSTOME CONNECT")
            # We call the _ensure_token_valid method on our backend instance
            self.backend._ensure_token_valid()
            # Overwrite the password with our temporary token
            ckwargs["password"] = self.backend._token

        return engine



class ExpiringTokenDatabaseBackend(DatabaseBackend):
    """
    A custom Celery result backend that subclasses the standard DatabaseBackend
    to handle expiring database tokens (e.g., IAM tokens for PostgreSQL/MySQL).
    """
    def __init__(self, dburi=None, *args, **kwargs):
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
            DB_USER=urllib.parse.quote(settings.get('celery', 'db_user')),
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



    #def _get_new_token(self):
    #    """
    #    This is where you fetch a new database token/password.
    #    For example, using AWS Boto3 to get an IAM RDS token.
    #    """
    #    print(f"[{datetime.utcnow().isoformat()}] FETCHING NEW DATABASE TOKEN...")

    #    # --- YOUR TOKEN FETCHING LOGIC GOES HERE ---
    #    # This function should return the token (which will be used as the password)
    #    # and its expiry time.

    #    # Simulated example:
    #    new_token = f"db_token_{int(datetime.utcnow().timestamp())}"
    #    expiry_time = datetime.utcnow() + timedelta(minutes=10) # Tokens are valid for 10 mins

    #    print(f"[{datetime.utcnow().isoformat()}] NEW TOKEN ACQUIRED, EXPIRES AT {expiry_time.isoformat()}Z")
    #    return new_token, expiry_time

    #def _ensure_token_valid(self):
    #    """
    #    Checks if the current token is valid, and refreshes it if not.
    #    This method is thread-safe.
    #    """
    #    # Check with a 60-second buffer to be safe
    #    if self._token is None or datetime.utcnow() > self._token_expiry - timedelta(seconds=60):
    #        with self._token_lock:
    #            # Double-checked locking pattern
    #            if self._token is None or datetime.utcnow() > self._token_expiry - timedelta(seconds=60):
    #                self._token, self._token_expiry = self._get_new_token()

    # This is the magic part: We override how the SQLAlchemy engine is created.
    #def _create_engine(self, dburi, **kwargs):
    #    """
    #    Override _create_engine to attach our token-refreshing event listener.
    #    """
    #    # Create the engine as Celery normally would.
    #    from celery.contrib import rdb; rdb.set_trace()
    #    engine = super()._create_engine(dburi, **kwargs)

    #    # Now, attach a listener that will execute BEFORE any new connection
    #    # is made to the database.
    #    @event.listens_for(engine, "do_connect")
    #    def _do_connect(dialect, conn_rec, cargs, ckwargs):
    #        """
    #        Listen for the 'do_connect' event and inject the fresh token.
    #        """

    #        # Ensure our token is fresh before connecting.
    #        #self._ensure_token_valid()

    #        # The 'ckwargs' dictionary contains connection arguments.
    #        # We will overwrite the password with our temporary token.
    #        # For PostgreSQL, the argument is 'password'. This may vary for other DBs.
    #        #ckwargs["password"] = self._token

    #    return engine

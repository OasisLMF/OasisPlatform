import urllib
from celery import Celery
from src.conf.iniconf import settings
from src.conf.celery_db_backend import CeleryDatabaseBackend

#: Celery config - Ignore task results?
CELERY_IGNORE_RESULT = False

#: Celery config - RabbitMQ connection
BROKER_URL = "amqp://{RABBIT_USER}:{RABBIT_PASS}@{RABBIT_HOST}:{RABBIT_PORT}//".format(
    RABBIT_USER=settings.get("celery", "rabbit_user", fallback="rabbit"),
    RABBIT_PASS=settings.get("celery", "rabbit_pass", fallback="rabbit"),
    RABBIT_HOST=settings.get("celery", "rabbit_host", fallback="127.0.0.1"),
    RABBIT_PORT=settings.get("celery", "rabbit_port", fallback="5672"),
)

#: Initialize Celery app with broker
app = Celery("oasisapi", broker=BROKER_URL)  # ✅ Explicitly setting broker

#: Initialize Celery Database Backend
celery_db_backend = CeleryDatabaseBackend(settings)

#: Retrieve the database engine from settings
CELERY_RESULTS_DB_BACKEND = settings.get("celery", "DB_ENGINE", fallback="db+sqlite")

# 🔹 Debugging Output
print(f"🔍 DB_ENGINE from settings: {CELERY_RESULTS_DB_BACKEND}")

if CELERY_RESULTS_DB_BACKEND == "db+sqlite":
    app.conf.result_backend = "sqlite:///{DB_NAME}".format(
        DB_NAME=settings.get("celery", "db_name", fallback="celery.db.sqlite"),
    )
elif CELERY_RESULTS_DB_BACKEND.startswith("db+postgresql"):
    # 🔹 Remove 'db+' prefix to match Celery expected format
    db_engine = CELERY_RESULTS_DB_BACKEND.replace("db+", "")

    # ✅ Force use of Service Principal
    service_principal_user = settings.get("celery", "AZURE_SERVICE_PRINCIPAL_USER")
    azure_token = celery_db_backend.get_azure_access_token()
    db_host = settings.get("celery", "db_host")  # 🔹 Define db_host before using it

    app.conf.result_backend = "{DB_ENGINE}://{SP_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}".format(
        DB_ENGINE=db_engine,  # ✅ Using 'postgresql+psycopg2'
        SP_USER=urllib.parse.quote(service_principal_user),  # 🔹 Force Service Principal
        DB_PASS=urllib.parse.quote(azure_token),  # 🔹 Auto-rotating token
        DB_HOST=db_host,
        DB_PORT=settings.get("celery", "db_port"),
        DB_NAME=settings.get("celery", "db_name", fallback="celery"),
    )

    # ✅ Mask Azure token in logs
    masked_backend = app.conf.result_backend.replace(urllib.parse.quote(azure_token), "**T*O*K*E*N**")
else:
    db_user = settings.get("celery", "db_user", fallback="user")
    db_pass = settings.get("celery", "db_pass", fallback="password")
    db_host = settings.get("celery", "db_host", fallback="localhost")
    db_port = settings.get("celery", "db_port", fallback="5432")
    db_name = settings.get("celery", "db_name", fallback="celery")

    app.conf.result_backend = f"{CELERY_RESULTS_DB_BACKEND}://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

    # ✅ Mask Password in Logs for Non-Azure DBs
    masked_backend = app.conf.result_backend.replace(db_pass, "**P*A*S*S*W*O*R*D**")

print("✅ Celery broker set to:", app.conf.broker_url)
print("✅ Celery result backend set to:", masked_backend)

#: Celery config - AMQP task result expiration time
CELERY_AMQP_TASK_RESULT_EXPIRES = 1000

#: Celery config - task serializer
CELERY_TASK_SERIALIZER = 'json'

#: Celery config - result serializer
CELERY_RESULT_SERIALIZER = 'json'

#: Celery config - accept content type
CELERY_ACCEPT_CONTENT = ['json']

#: Celery config - timezone (default == UTC)
# CELERY_TIMEZONE = 'Europe/London'

#: Celery config - enable UTC
CELERY_ENABLE_UTC = True

#: Celery config - concurrency
CELERYD_CONCURRENCY = 1

#: Disable celery task prefetch
#: https://docs.celeryproject.org/en/stable/userguide/configuration.html#std-setting-worker_prefetch_multiplier
CELERYD_PREFETCH_MULTIPLIER = 1

worker_task_kwargs = {
    'autoretry_for': (Exception,),
    'max_retries': 2,               # The task will be run max_retries + 1 times
    'default_retry_delay': 6,       # A small delay to recover from temporary bad states
}


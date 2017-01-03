CELERY_IGNORE_RESULT = False
# IP address of the server running RabbitMQ and Celery
BROKER_URL = "amqp://guest:guest@rabbit:%RABBIT_PORT%//"
CELERY_RESULT_BACKEND = 'db+mysql://celery:password@mysql:%MYSQL_PORT%/celery'
CELERY_AMQP_TASK_RESULT_EXPIRES = 1000
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TIMEZONE = 'Europe/London'
CELERY_ENABLE_UTC = True
CELERYD_CONCURRENCY = 1

CELERY_IGNORE_RESULT = False
# IP address of the server running RabbitMQ and Celery
BROKER_URL = "rabbit"
CELERY_RESULT_BACKEND = 'db+mysql://celery:password@mysql/celery'
CELERY_AMQP_TASK_RESULT_EXPIRES = 1000
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TIMEZONE = 'Europe/London'
CELERY_ENABLE_UTC = True

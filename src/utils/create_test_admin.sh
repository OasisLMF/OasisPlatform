#!/bin/bash

USERNAME='admin'
EMAIL='admin@example.com'
PASSWORD='password'

cd /var/www/oasis
echo "from django.contrib.auth.models import User; User.objects.create_superuser('${USERNAME}', '${EMAIL}', '${PASSWORD}')" | python manage.py shell

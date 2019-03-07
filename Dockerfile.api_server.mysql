FROM coreoasis/api_base:latest

ENV OASIS_SERVER_DB_ENGINE django.db.backends.mysql
RUN apt-get update && apt-get install -y --no-install-recommends libmariadbclient-dev-compat && rm -rf /var/lib/apt/lists/*
RUN pip install mysqlclient

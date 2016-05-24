FROM python:2.7
RUN pip install \
    celery \
    ConfigParser

RUN useradd -ms /bin/bash worker
USER worker
WORKDIR /home/worker

COPY ./CeleryConfig.py  ./
COPY ./Tasks.ini  ./
COPY ./tasks.py  ./
COPY ./TaskStatus.py  ./
COPY ./startup.sh  ./

ENTRYPOINT ./startup.sh;bash

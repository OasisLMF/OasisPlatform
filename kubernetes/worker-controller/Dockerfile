FROM alpine:3.16
ARG PIP_TRUSTED_HOSTS

WORKDIR /app/worker-controller/
RUN adduser  --home /app/worker-controller/ --shell /bin/bash --disabled-password --gecos "" worker-controller
COPY requirements.txt .
COPY entrypoint.sh .
COPY src/ .

RUN apk update && apk upgrade --available && apk --no-cache add python3 py3-pip bash gcc musl-dev python3-dev
RUN pip install -r requirements.txt --ignore-installed six $(for host in $PIP_TRUSTED_HOSTS; do echo --trusted-host "$host"; done)

RUN chown -R worker-controller:worker-controller /app/worker-controller/
USER worker-controller

ENTRYPOINT [ "/app/worker-controller/entrypoint.sh" ]

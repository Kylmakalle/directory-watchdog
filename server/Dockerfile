FROM python:3.7.7-alpine

RUN mkdir -p /opt/directory-watchdog/server
WORKDIR /opt/directory-watchdog/server
ADD . /opt/directory-watchdog/server

### Для установки ujson в alpine контейнер
RUN apk add --no-cache --virtual .build-deps g++ musl-dev \
     && pip install -r requirements.txt
###

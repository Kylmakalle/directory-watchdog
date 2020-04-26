FROM python:3.7.7-alpine

RUN mkdir -p /opt/directory-watchdog/client
WORKDIR /opt/directory-watchdog/client
ADD . /opt/directory-watchdog/client

### Для установки ujson в alpine контейнер
RUN apk add --no-cache --virtual .build-deps g++ musl-dev \
     && pip install -r requirements.txt
###

CMD ["python3", "client.py"]

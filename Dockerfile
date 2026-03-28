FROM python:3.12-slim

RUN groupadd -g 1000 app && useradd -u 1000 -g app -m app

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --root-user-action=ignore \
    -r /tmp/requirements.txt pytest && \
    rm /tmp/requirements.txt

USER app
WORKDIR /app

FROM python:3.10.4-slim
COPY . /ethelease
WORKDIR /ethelease
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
    && apt-get install -y g++ gcc git \
    && pip install --upgrade pip \
    && pip install -r requirements.txt \
    && pip install . \
    && apt-get purge -y --auto-remove g++ gcc git \
    && apt-get clean \
    && rm -rf \
        /var/lib/apt/lists/* \
        /tmp/* \
        /var/tmp/* \
        /usr/share/man \
        /usr/share/doc \
        /usr/share/doc-base
WORKDIR /

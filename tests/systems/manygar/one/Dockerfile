FROM python:3.10.4-slim
COPY . /app
WORKDIR /app
ARG DEBIAN_FRONTEND=noninteractive
RUN pip install -r requirements.txt \
    && pip install .

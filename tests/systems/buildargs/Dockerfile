FROM python:3.10.4-slim
COPY . /app
WORKDIR /app
ARG _A_
ARG _B_
ARG _C_
RUN pip install -r requirements.txt \
    && pip install .
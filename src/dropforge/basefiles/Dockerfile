ARG _AWS_ACCT_ID_
ARG _BASE_IMG_VERSION_
FROM {}
COPY . /app
WORKDIR /app
ARG _AWS_ACCT_ID_
ENV AWS_ACCT_ID=${_AWS_ACCT_ID_}
RUN pip install -r requirements.txt \
    && pip install .

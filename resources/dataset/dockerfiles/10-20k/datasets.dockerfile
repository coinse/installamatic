FROM python:3.11

COPY . /app/

WORKDIR /app

RUN pip install -r ".[dev]"

RUN make test
FROM python:3.10.10-slim
ARG WORKDIR=/app

ARG WORKDIR
ARG USERNAME=appuser
ARG USER_UID=1000
ARG USER_GID=$USER_UID

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV POETRY_VERSION 1.4.0
ENV POETRY_VIRTUALENVS_IN_PROJECT true

WORKDIR $WORKDIR

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

RUN adduser -u $USER_UID --disabled-password --gecos "" $USERNAME && chown -R $USERNAME $WORKDIR
USER $USERNAME
ENV PATH /app/.venv/bin:$PATH:/home/$USERNAME/.local/bin

RUN pip install --user -U pip
RUN curl -sSL https://install.python-poetry.org | python3 -

COPY ./README.md ./README.md
COPY ./poetry.lock ./pyproject.toml ./
COPY ./eventiq ./eventiq
COPY ./examples ./examples

RUN poetry install -E cli -E nats -E orjson -E prometheus -E opentelemetry

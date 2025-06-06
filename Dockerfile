FROM public.ecr.aws/docker/library/python:3.12

ARG POETRY_ARGS="--no-root --no-ansi --only main"

RUN useradd -u 1000 django_govuk

RUN pip install poetry gunicorn

COPY pyproject.toml poetry.lock /app/

WORKDIR /app

RUN poetry config virtualenvs.create false && \
    poetry install ${POETRY_ARGS}

COPY manage.py /app/
COPY django_govuk /app/django_govuk

RUN sed -i 's/\r$//' /app/manage.py  && \
    chmod +x /app/manage.py

ENV SECRET_KEY=unneeded
ENV DOMAIN_NAME=http://localhost:2010

RUN  /app/manage.py collectstatic --no-input

RUN mkdir /var/run/django_govuk && \
    chown django_govuk:django_govuk /var/run/django_govuk

RUN mkdir /home/django_govuk && \
    chown django_govuk:django_govuk /home/django_govuk

USER django_govuk

EXPOSE 8020

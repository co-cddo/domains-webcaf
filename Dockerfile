FROM public.ecr.aws/docker/library/python:3.12

USER root
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

RUN apt-get update && \
    apt-get purge -y --auto-remove git sqlite3 libexpat1 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

ARG POETRY_ARGS="--no-root --no-ansi --only main"

RUN useradd -u 1000 webcaf

RUN pip install poetry gunicorn

COPY pyproject.toml poetry.lock /app/

WORKDIR /app

RUN poetry config virtualenvs.create false && \
    poetry install ${POETRY_ARGS}

COPY manage.py /app/
COPY webcaf /app/webcaf
COPY frameworks /app/frameworks

RUN sed -i 's/\r$//' /app/manage.py  && \
    chmod +x /app/manage.py

ENV SECRET_KEY=unneeded
ENV DOMAIN_NAME=http://localhost:2010
ENV SSO_MODE=external

#Pass SSO_MODE=none for static file generation since we don't need SSO
#but we keep the default value of False in the environment
#so the caller can override it if needed
RUN SSO_MODE=none /app/manage.py collectstatic --no-input

RUN mkdir /var/run/webcaf && \
    chown webcaf:webcaf /var/run/webcaf

RUN mkdir /home/webcaf && \
    chown webcaf:webcaf /home/webcaf

USER webcaf

EXPOSE 8020

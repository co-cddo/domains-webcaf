FROM public.ecr.aws/docker/library/python:3.12

ARG POETRY_ARGS="--no-root --no-ansi --only main"

RUN useradd -u 1000 webcaf

RUN pip install poetry gunicorn

COPY pyproject.toml poetry.lock /app/

WORKDIR /app

RUN poetry config virtualenvs.create false && \
    poetry install ${POETRY_ARGS}

COPY manage.py /app/
COPY webcaf /app/webcaf

RUN sed -i 's/\r$//' /app/manage.py  && \
    chmod +x /app/manage.py

ENV SECRET_KEY=unneeded
ENV DOMAIN_NAME=http://localhost:2010

RUN  /app/manage.py collectstatic --no-input

RUN mkdir /var/run/webcaf && \
    chown webcaf:webcaf /var/run/webcaf

RUN mkdir /home/webcaf && \
    chown webcaf:webcaf /home/webcaf

USER webcaf

EXPOSE 8020

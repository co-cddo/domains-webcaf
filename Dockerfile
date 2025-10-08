FROM public.ecr.aws/amazonlinux/amazonlinux:2023

ARG POETRY_ARGS="--no-root --no-ansi --only main"

RUN dnf -y install python3.12 python3.12-devel python3-pip shadow-utils
RUN alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 100
RUN ln -s /usr/bin/python3 /usr/bin/python
RUN python3 -m ensurepip
RUN pip3 install --no-cache-dir --upgrade pip setuptools wheel

RUN useradd -u 1000 -m webcaf

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

USER webcaf

EXPOSE 8020

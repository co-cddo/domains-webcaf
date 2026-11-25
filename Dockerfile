FROM public.ecr.aws/amazonlinux/amazonlinux:2023

# Extra flags for `uv sync`
# docker-compose passes --all-groups for a dev image
ARG UV_SYNC_ARGS="--no-dev"

RUN dnf -y install python3.12 python3.12-devel shadow-utils \
        pango gcc gcc-c++ zlib-devel libjpeg-devel openjpeg2-devel libffi-devel && \
    ln -s /usr/bin/python3.12 /usr/bin/python && \
    dnf clean all && \
    rm -rf /var/cache/dnf

RUN useradd -u 1000 -m webcaf

COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /uvx /bin/

ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON=/usr/bin/python3.12 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml uv.lock /app/

WORKDIR /app

RUN uv sync --frozen --no-cache ${UV_SYNC_ARGS}

# The ECS task definition and the migration step use the local path
RUN ln -s /opt/venv/bin/gunicorn /usr/local/bin/gunicorn

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

#Copy gunicon configuration
COPY gunicorn_conf.py /app/gunicorn_conf.py

USER webcaf

EXPOSE 8010

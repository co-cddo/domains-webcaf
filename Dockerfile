# A version tag, not a digest, so each rebuild picks up security patches.
FROM public.ecr.aws/amazonlinux/amazonlinux:2023

# Production installs the runtime dependencies only. docker-compose.yml passes
# an empty value so the local web container also gets the dev tools.
ARG UV_EXPORT_ARGS="--no-dev"

ARG GOV_UK_ONE_LOGIN_PRIVATE_KEY

RUN dnf -y install python3.14 python3.14-devel python3-pip shadow-utils

# Libraries used for PDF generation
RUN dnf -y install pango gcc gcc-c++ zlib-devel libjpeg-devel openjpeg2-devel libffi-devel


RUN ln -s /usr/bin/python3.14 /usr/bin/python
RUN python3.14 -m ensurepip
RUN pip3 install --no-cache-dir --upgrade pip setuptools wheel

RUN useradd -u 1000 -m webcaf

# uv is a single binary, at the version that wrote uv.lock.
COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock /app/

WORKDIR /app

# Install exactly what uv.lock says, hashes checked, into the app's Python
# (python3 on Amazon Linux is the OS's own 3.9). gunicorn comes from the lock.
# --locked fails the build if uv.lock is out of step with pyproject.toml,
# as poetry install did; --frozen would install a stale lock silently.
# --no-config: the [tool.uv] settings in pyproject.toml are already applied
# in uv.lock; read again here they would add an unpinned line that
# --require-hashes rejects.
RUN uv export --locked --no-emit-project ${UV_EXPORT_ARGS} -o /tmp/requirements.txt && \
  uv pip install --system --python /usr/bin/python3.14 --no-config --require-hashes --no-cache -r /tmp/requirements.txt && \
  rm /tmp/requirements.txt

COPY manage.py /app/
COPY webcaf /app/webcaf
COPY frameworks /app/frameworks

RUN sed -i 's/\r$//' /app/manage.py  && \
  chmod +x /app/manage.py

ENV SECRET_KEY=unneeded
ENV DOMAIN_NAME=http://localhost:2010
ENV SSO_MODE=internal-access

#Pass SSO_MODE=none for static file generation since we don't need SSO
#but we keep the default value of False in the environment
#so the caller can override it if needed
RUN SSO_MODE=none /app/manage.py collectstatic --no-input

RUN mkdir /var/run/webcaf && \
  chown webcaf:webcaf /var/run/webcaf && \
  chown -R webcaf:webcaf /app/webcaf/static

RUN echo "$GOV_UK_ONE_LOGIN_PRIVATE_KEY" > /var/run/webcaf/private.pem

# Optional: If you want to make sure it has the right permissions (e.g., restricted read access)
RUN chmod 600 /var/run/webcaf/private.pem
RUN chown webcaf:webcaf /var/run/webcaf/private.pem

#Copy gunicon configuration
COPY gunicorn_conf.py /app/gunicorn_conf.py

USER webcaf

EXPOSE 8010

# Set the main executable
ENTRYPOINT ["/usr/local/bin/gunicorn"]

# Provide the default configuration and application module as arguments
CMD ["--config", "/app/gunicorn_conf.py", "webcaf.wsgi:application"]

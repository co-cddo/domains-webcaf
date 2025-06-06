# Django GOVUK Boilerplate

A boilerplate Django project using the GOV.UK Design System, including a basic Dockerfile and docker-compose.yml.

It is based on the [Register a gov.uk Domain service](https://github.com/co-cddo/domains-register-a-govuk-domain).

## Running

```
docker compose up
```

This brings up Postgres, runs an init container to apply migrations and collect static files, then brings up the app. It includes a single page, accessible at `localhost:8000`

## Developing

```
pip install poetry
poetry install
pre-commit install
```

It's probably a good idea to also run `poetry update` before making any changes.

The Django version is pinned to 5.1.9. As of June 2025 this is the highest version supported by `govuk-frontend-django`. If you change the version in `pyproject.toml` before running `poetry install`, remember to run `poetry lock` first.

# WebCAF Prototype

A work in progress application to enable users to self-assess against the NCSC Cyber Assessment Framework, designed to enable future versions or different assessments to be represented with minimal code additions.

## Running

```
docker compose up
```

This brings up Postgres, runs an init container to apply migrations and collect static files, then brings up the app.

The current flow is a single pass through the CAF v3.2. It starts at `localhost:8010/a-managing-security-risk/`

It is purely a proof of concept for now. Field values are not retained across pages. Nothing is done with the data at the end. It lacks any pages to bookend the flow. The only validations are those provided by default (e.g. text boxes cannot be empty).

What it does do is demonstrate that a user flow can be generated using GOV.UK components from a machine-readable version of a CAF and that it doesn't take a huge amount of code to do it.

## Developing

Make sure the python version you use is the same as in the [Dockerfile](Dockerfile)

Create a file called `.env` containing the following line:

```
DATABASE_URL=postgres://localhost/webcaf
```

Then run in a terminal

``` shell
pip install poetry pre-commit
poetry install
pre-commit install
poetry run dotenv run ./manage.py migrate
```

and to run the local server:

``` shell
poetry run dotenv run ./manage.py runserver
```
### SSO settings
We use LOCAL_SSO environment variable to decide which SSO implementation should be used.
If LOCAL_SSO is set to true, then the application will connect to the [DEX](https://dexidp.io/) instance
deployed locally in the docker compose setup.

This will have two users configured:
 - a normal user called Alice, alice@example.gov.uk
 - Admin user called Tin, admin@example.gov.uk

Both the users have the same password set to 'password'

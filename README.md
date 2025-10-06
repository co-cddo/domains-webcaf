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
We use the `SSO_MODE` environment variable to decide which SSO implementation should be used.
- if set to `dex`, then the application will connect to the [DEX](https://dexidp.io/) instance deployed locally in the docker compose setup.
- set it to `local`if you want to the application to connect to a DEX instance running on the host machine (at `localhost:5556`)
- otherwise it'll take from `OIDC_*` environment variables (see `settings.py`)

This will have two users configured:
 - a normal user called Alice, alice@example.gov.uk
 - Admin user called Tin, admin@example.gov.uk

Both the users have the same password set to 'password'

### Seed Data

Once migrations have been run the following command will add an admin user ("admin", "password"), an organisation and two systems. If you have already logged in with either of the SSO users, the command will set up a UserProfile for each and attach it to the Organisation. If you have not logged in with one of the SSO users then as far as Django is concerned it does not exist and this step is skipped. See the terminal output for more information.

```
python manage.py add_seed_data
```

### End-to-end testing

This service uses pytest-playwright to perform browser-based end-to-end tests. In order to run the tests,
follow the steps above to install poetry and run a local server, then in a terminal:

``` shell
cd end-to-end-tests
poetry run pytest # add "--headed" to see the browser window
```

### Deployment strategy

#### Staging
We deploy the latest image created from the main branch to staging. Each time a PR is merged to main,
the image is rebuilt and deployed to staging. This is hanby the stage-ecr-deployment-workflow in the GitHub Actions.

#### Production
We deploy the latest image created from the main branch to production. Each time a release tag i.e release-v1.0.0 is created from
the main branch.
the image is rebuilt and deployed to production. This is handled by the prod-ecr-deployment-workflow in the GitHub Actions.

#### dependencies
 - Production and the staging account information are stored in the GitHub secrets.
   - Deployment roles are created in the domains-iac repo.
     - You will need to run the following once per account to enable Github OIDC login for the workflow to obtain the credentials.
     ```bash
      aws iam create-open-id-connect-provider \
      --url https://token.actions.githubusercontent.com \
      --client-id-list sts.amazonaws.com \
      --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1 --profile <profile>
      ```
     NOTE: if the github changes the thumbprint, you will need to run the above command with the new value.

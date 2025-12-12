# WebCAF Prototype

Application to enable users to self-assess against the NCSC Cyber Assessment Framework, designed to
enable future versions or different assessments to be represented with minimal code additions.

# Configuration

We store the default configuration in the database, which can be accessed through the admin screens. The fields that are
required for the
functioning of the application are:

- current_assessment_period
- assessment_period_end
- default_framework

Default values are provided in the migrations for the year 2025 and 2026.

Year 2025 values are:
with the values of "25/26", "31 March 2026 11:59pm" and "caf32" respectively.

Year 2026 values are:
with the values of "26/27", "31 March 2027 11:59pm" and "caf32" respectively.

This will enable the application to automatically switch to the next period when the current period ends.

**NOTE:** Users will need to add a new configuration for the period after the current period ends

# Review permissions


The review pages use a common mixin to manage who can view and edit content. The logic lives in `webcaf/webcaf/views/assessor/util.py` in the `BaseReviewMixin`, which extends `UserRoleCheckMixin`.

- Allowed roles for review-related views are returned by `BaseReviewMixin.get_allowed_roles()`:
  - `cyber_advisor`
  - `organisation_lead`
  - `reviewer`
  - `assessor`

- Read-only roles are returned by `BaseReviewMixin.get_read_only_roles()`. By default this is:
  - `organisation_lead`

- The edit permission flag is set on the object returned by the view’s `get_object()` implementation inside `BaseReviewMixin`. Specifically:

  - When an object is fetched, the current user’s `UserProfile.role` is checked.
  - The mixin sets `obj.can_edit = current_profile.role not in self.get_read_only_roles()`.
  - As a result, all allowed roles can edit except those explicitly listed as read‑only (currently `organisation_lead`).

This `can_edit` attribute is then available to templates and forms to decide whether to render edit controls (e.g. show/hide buttons) or enforce read-only behaviour. If additional roles should be read-only in future, override `get_read_only_roles()` in a subclass or update the default list in the mixin.

The mixin also sets `login_url` to the OIDC route and leverages `UserRoleCheckMixin` to enforce authentication and role checks across review-related views.


## Running

```
docker compose up
```

This brings up Postgres, runs an init container to apply migrations and collect static files, then brings up the app.

The current flow is a single pass through the CAF v3.2. It starts at `localhost:8010/`



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

### Privacy and Logging Best Practices

**IMPORTANT:** When logging user information (emails, usernames, or any personally identifiable information), always use the `mask_email` utility function to protect user privacy.

```python
from webcaf.webcaf.utils import mask_email

# Good - email is masked
logger.info(f"Sent verification to {mask_email(user.email)}")

# Bad - exposes full email address
logger.info(f"Sent verification to {user.email}")
```

The `mask_email` function replaces email addresses with a masked version (e.g., `us***@example.com`), showing only the first two characters of the username while preserving the domain for debugging purposes.

### SSO settings

We use the `SSO_MODE` environment variable to decide which SSO implementation should be used.

- if set to `dex`, then the application will connect to the [DEX](https://dexidp.io/) instance deployed locally in the
  docker compose setup.
- set it to `local`if you want to the application to connect to a DEX instance running on the host machine (at
  `localhost:5556`)
- otherwise it'll take from `OIDC_*` environment variables (see `settings.py`)

This will have two users configured:

- a normal user called Alice, alice@example.gov.uk
- Admin user called Tin, admin@example.gov.uk

Both the users have the same password set to 'password'

### Seed Data

Use this command, either locally or in deployment, to load the initial list of organisations into the database:

```
python manage.py add_organisations
```

The following command will add an admin user ("admin", "password"). If you have already logged in with either of the SSO
users, the command will set up a UserProfile for each and attach it to the Organisation. If you have not logged in with
one of the SSO users then as far as Django is concerned it does not exist and this step is skipped. See the terminal
output for more information.

```
python manage.py add_seed_data
```

> This command requires one or more organisations to exist in the database. Use the add_organisations command to do
> this.

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

We deploy the latest image created from the main branch to production. Each time a release tag i.e release-v1.0.0 is
created from
the main branch.
the image is rebuilt and deployed to production. This is handled by the prod-ecr-deployment-workflow in the GitHub
Actions.

#### dependencies

- Production and the staging account information are stored in the GitHub secrets.
    - Deployment roles are created in the domains-iac repo.
        - You will need to run the following once per account to enable Github OIDC login for the workflow to obtain the
          credentials.
      ```bash
       aws iam create-open-id-connect-provider \
       --url https://token.actions.githubusercontent.com \
       --client-id-list sts.amazonaws.com \
       --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1 --profile <profile>
       ```
      NOTE: if the github changes the thumbprint, you will need to run the above command with the new value.

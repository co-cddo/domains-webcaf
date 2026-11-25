# WebCAF

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


# Tip permissions


The Tip (Targeted Improvement Plan) pages use a common mixin to manage who can view and edit content. The logic lives in `webcaf/webcaf/tip/util.py` in the `BaseTipMixin`, which extends `UserRoleCheckMixin`.

- Allowed roles for tip-related views are returned by `BaseTipMixin.get_allowed_roles()`:
  - `cyber_advisor`
  - `organisation_lead`
  - `organisation_user`

- Read-only roles are returned by `BaseTipMixin.get_read_only_roles()`. By default this is:
  - `cyber_advisor`

- The edit permission flag is set on the object returned by the view’s `get_object()` implementation inside `BaseTipMixin`. Specifically:

  - When an object is fetched, the current user’s `UserProfile.role` is checked.
  - The mixin sets `obj.can_edit = current_profile and current_profile.role not in self.get_read_only_roles()`.
  - Additionally, once a tip has been submitted (`tip.is_submitted`), `can_edit` is forced to `False`, so submitted tips are read-only for everyone.

- Which tips a user can see is scoped by `BaseTipMixin.get_tip_for_user()` (used by `get_queryset()`): only tips belonging to the user’s own organisation whose underlying review has been finalised (the assessment is `submitted` and `review_finalised` is set) are returned.

- Approving and rejecting a tip is separate from editing and is restricted to Django staff users. The `Tip` model defines the custom permissions `can_approve_tip` and `can_reject_tip` (see `Tip.Meta.permissions`), and `Tip.approve()` / `Tip.reject()` both require `current_user.is_staff`.

This `can_edit` attribute is then available to templates and forms to decide whether to render edit controls or enforce read-only behaviour. As with reviews, the mixin also sets `login_url` to the OIDC route and leverages `UserRoleCheckMixin` to enforce authentication and role checks across tip-related views.


# Admin permissions and user groups

The application defines 4 user groups (automatically initialized in migrations):

- `admin` - has full access the data in the system
- `data analyst admin` - not implemented yet
- `data analyst` - not implemented yet
- `cyber advisor` - read access to all relevant entities + approve/reject Tip

### User Association and Scoped Entity Visibility

Django Admin provides a **User Association** screen (`UserAssociation` model) allowing administrators to associate any backend user with one or more frontend users who have the `cyber_advisor` role.

- **Organisation-scoped access:** When a backend user belongs to the `cyber advisor` group, their visibility in the admin interface (`OrganisationAdmin`, `SystemAdmin`, `AssessmentAdmin`, `ReviewAdmin`, `TipAdmin`, and `ScopedUserAdmin`) is automatically scoped down:
  - The user only sees entities (Organisations, Systems, Assessments, Reviews, Tips, and Users) that belong to the organisations of their associated frontend `cyber_advisor` user(s).
  - If a user in the `cyber advisor` group does not have an association configured, a warning message is displayed prompting an admin to create one, and no organisation entities are returned.
- **Unrestricted access:** Superusers and members of the `admin` group have full access to view and manage all organisations and entities without restriction.

### Editable JSON Fields in Admin

Assessment and Review admin forms include JSON data fields displayed in a readable, pretty-printed format.

- **Read/Write access:** Superusers and any user in the `admin` group can edit and save the JSON data fields directly in the admin form (implemented via `JsonDataEnableEditMixin`). Submitted values are validated to ensure valid JSON syntax before saving.
- **Read-Only access:** For all other users with admin access, the JSON data fields are rendered in read-only mode.


## Running

```
docker compose up
```

This brings up the full stack defined in `docker-compose.yml`:

- `postgres` — the PostgreSQL database (also exposed on the host at port `54321`).
- `oauth` — a local [DEX](https://dexidp.io/) identity provider used for SSO (`SSO_MODE=dex`).
- `init` — a one-shot container that runs `local-init.sh` (`makemigrations`, `collectstatic`, then `migrate`) and then exits.
- `web` — the application, served by Gunicorn with `--reload`, started once `init` has completed successfully and Postgres is healthy.

The app is available at `localhost:8010/` and supports the CAF v3.2 and v4.0 frameworks (v3.2 is the default).

Alternatively, use the Make targets, which wrap the same compose files:

``` shell
make up-devserver   # run the app with Django's auto-reloading runserver instead of Gunicorn
make up_dex         # bring up only the DEX (oauth) container
make shell          # open a bash shell in the running web container
make clear-db       # tear everything down and drop the Postgres volume
```



## Developing

Dependencies are managed with [uv](https://docs.astral.sh/uv/), which installs the Python version pinned in `.python-version` (3.12, the same as the [Dockerfile](Dockerfile)).

The database credentials are defined in `docker-compose.yml`: the Postgres container uses the user/password/database `webcaf`/`webcaf`/`webcaf` and is exposed on the host at port `54321`. To develop against it, first start Postgres (for example `docker compose up postgres`), then create a file called `.env` containing:

```
DATABASE_URL=postgresql://webcaf:webcaf@localhost:54321/webcaf #pragma: allowlist secret
```

Then run in a terminal

``` shell
uv sync --all-groups
uv run pre-commit install
uv run --env-file .env ./manage.py migrate
```

WeasytPrint needs Pango and you can install it with `brew install pango`.
The mypy pre-commit hook adds `/opt/homebrew/lib` to the library search path however if you've installed with something else then update the path accordingly.

and to run the local server:

``` shell
uv run --env-file .env ./manage.py runserver
```

### Running tests

The unit tests and BDD feature tests run inside containers via the Make targets:

``` shell
make test     # run the pytest suite (writes an HTML report to reports/)
make behave   # build and run the behave feature tests
make build    # (re)build the images
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

The browser-based end-to-end tests are the behave feature tests under `features/`, driven by Playwright.
Run them with `make behave`; see `features/README.md` for running a subset or with a visible browser.

### Deployment strategy

GitHub Actions builds the image and pushes it to the `web-caf-app-ecr` repository of one AWS account per GitHub environment. The runtime infrastructure (ECS, RDS, CloudFront) lives in a private repository and deploys whichever image carries the `latest` tag for now.

| Event | Environment | Image tags |
|---|---|---|
| Pull request to `main` | `PLATFORM_DEV` | commit sha, `latest` |
| Push to `main` | `PLATFORM_DEV` | commit sha, `latest` |
| `Deploy - Dev` run by hand from any branch | `PLATFORM_DEV`, optionally a developer stack's `<unique id>-web-caf-app-ecr` | commit sha, `latest` |
| Pre-release published with a `vX.Y.Z` tag | `PLATFORM_STAGING` | commit sha, `vX.Y.Z`, `latest` |
| Release published | `PLATFORM_PROD` | commit sha, `vX.Y.Z`, `latest` |

Staging and production are gated GitHub environments: a reviewer must approve the deployment, and only a
`v*.*.*` tag can deploy. To release, create a pre-release from `main` with the next `vX.Y.Z` tag (deploys
staging), test it, then edit the release and untick "pre-release" (deploys production).

`infra/` holds the CDK stack for the ECR repository. The `Create ECR repositories` workflow deploys it to a
chosen environment; tick `import` on the first run in an account to adopt the repository that already exists.

Each GitHub environment holds the secrets the workflows need (`AWS_ACCOUNT_ID`, `AWS_IAM_ROLE_ECR_PUSH`,
`AWS_IAM_ROLE_CDK_DEPLOY`, `AWS_REGION`). The IAM roles, the OIDC provider and the environments themselves are
provisioned centrally by the platform bootstrap, not by this repository.

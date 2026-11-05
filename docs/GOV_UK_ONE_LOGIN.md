# GOV.UK One Login

WebCAF uses `govuk-onelogin-django` for GOV.UK One Login and retains `mozilla-django-oidc` for DEX and generic OIDC providers. Application authorisation remains in WebCAF's `UserProfile`, organisation and role models.

## Local simulator

The official [GOV.UK One Login simulator](https://github.com/govuk-one-login/simulator) is an explicitly selected alternative to GDS Internal Access. It exercises the One Login protocol flow without a registered integration-environment client. DEX remains available through explicit commands for generic OIDC testing.

## One Login Simulator vs DEX

The GOV.UK One Login Simulator is retained for optional local development and automated BDD testing. It provides a closer representation of the GOV.UK One Login authentication flow than DEX and allows One Login-specific behaviour to be exercised locally and in CI.

DEX is retained as an optional generic OIDC provider. This allows WebCAF's underlying OIDC integration to be exercised independently of GOV.UK One Login and avoids coupling the local development and test environments exclusively to a single identity provider.

Retaining DEX also preserves a generic OIDC development path. GDS Internal Access uses this OIDC integration; see [Internal Access sandbox configuration](INTERNAL_ACCESS.md). Internal Access is the default locally and in sandbox. One Login is retained as an inactive, configurable alternative.

The two providers therefore have distinct purposes:

- **GOV.UK One Login Simulator** - an optional local provider and the explicitly selected provider for One Login automated/BDD testing.
- **DEX** - retained for generic OIDC testing and for exercising provider-independent authentication behaviour.

The simulator is intended to reproduce the One Login interfaces needed for development and automated testing, but it is not the real GOV.UK One Login service. Successful testing against the simulator therefore does not replace integration testing against GOV.UK One Login in an appropriate deployed environment.
Copy `webcaf/.env.example` to `webcaf/.env`. To opt into the simulator on the host, replace the Internal Access selection and enable these values:

```text
SSO_MODE=one-login
GOV_UK_ONE_LOGIN_CLIENT_ID=webcaf-local
GOV_UK_ONE_LOGIN_PRIVATE_KEY_PATH=tests/fixtures/one-login-simulator-private-key.pem
GOV_UK_ONE_LOGIN_OPENID_CONFIG_URL=http://one-login.localhost:3000/.well-known/openid-configuration
GOV_UK_ONE_LOGIN_SCOPE="openid email"
GOV_UK_ONE_LOGIN_ENVIRONMENT=integration
```

The committed private key is the simulator project's published default test key. It is public, is not a deployment credential, and must never be used outside the local simulator.

Start the complete containerised application at `http://localhost:8010` with:

```shell
make up_one_login
```

The `one-login.localhost` simulator hostname resolves to the published simulator port for the host browser and to the simulator network alias for WebCAF's server-side requests. To run Django on the host instead, start PostgreSQL, Valkey and the simulator, then run migrations and the development server:

```shell
make up_one_login_simulator
uv run python manage.py migrate
uv run python manage.py runserver 0.0.0.0:8010
```

Open `http://localhost:8010` and select **Sign in**. The simulator runs in interactive mode and displays a response form pre-populated with a production-shaped subject, `alice@example.gov.uk`, a verified email and the `P0` confidence level requested by WebCAF. Core Identity VC is an empty object and postal address details are blank because WebCAF requests authentication without identity verification. Select **Continue** to use those values, or edit them to exercise another response.

Named presets can update the values shown on the next sign-in:

```shell
make one_login_user PRESET=alice
make one_login_user PRESET=organisation_user
make one_login_user PRESET=cyber_advisor
make one_login_user PRESET=assessor
make one_login_user PRESET=unverified
```

The available presets are `alice`, `admin`, `organisation_user`, `organisation_lead`, `cyber_advisor`, `assessor`, and `unverified`. Each preset uses `P0`, an empty Core Identity VC object and no postal address details. The empty object works around the simulator rejecting a blank Core Identity field when its interactive form is submitted; WebCAF does not request that claim. Running `make up_one_login_simulator` applies the Alice preset after startup. Set `ONE_LOGIN_SIMULATOR_INTERACTIVE_MODE=false` before starting the service if the configured response should be returned without displaying the form.

For a new user, first add the exact email domain to **Allowed email domains** in Django admin. One Login creates the Django user but does not create a `UserProfile`, so an administrator must also assign the organisation and role before the account can use protected WebCAF functionality. Existing non-staff users are matched by email and retain their profiles.

An opt-in smoke test performs a real authorization, token, JWKS and UserInfo exchange against the running simulator. It uses an isolated Django test database and restores the simulator's configured redirect URLs:

```shell
RUN_ONE_LOGIN_SIMULATOR_TESTS=true uv run python manage.py test tests.test_one_login_simulator
```

The test is skipped during normal local test runs. Run it only after starting the simulator and configuring `webcaf/.env` with the simulator values above. It supports both interactive and non-interactive simulator modes and runs automatically in pull-request CI.

Stop the simulator with:

```shell
docker compose stop one-login-simulator
```

The feature-test stack uses the internal `one-login-simulator` hostname because both WebCAF and Playwright run on the Compose network. This avoids relying on special `.localhost` resolution inside test containers while retaining a single issuer for each workflow.

## Simulator feature tests

Run the shared application scenarios and One Login-specific browser scenarios with:

```shell
make behave
```

The feature-test Compose configuration uses Docker-resolvable URLs for the Playwright browser, WebCAF and simulator. It runs the simulator non-interactively and configures a deterministic identity before each login. The default suite contains 26 application scenarios, two provider-independent Django admin scenarios, and four additional scenarios covering a profiled user, a user without a profile, an unverified email, and front-channel logout. The suite runs serially because `/config` controls global simulator state.

Run only the four One Login-specific scenarios with:

```shell
make behave FEATURE_TEST_ARGS="--tags=one_login"
```

Run the focused DEX login and logout coverage separately with:

```shell
make behave_dex
```

## One Login integration environment

The registered local URLs are:

```text
Redirect URI:             http://localhost:8010/one-login/callback/
Post-logout redirect URI: http://localhost:8010/
```

Create `webcaf/.env` from `webcaf/.env.example`, set `SSO_MODE=one-login`, and replace the simulator client ID, private key path and OpenID configuration URL with the registered integration-environment values. Keep the private key in the ignored repository-root `.secrets/` directory and set `GOV_UK_ONE_LOGIN_PRIVATE_KEY_PATH` to its absolute path or a path relative to the repository root.

Install dependencies, then start the local PostgreSQL database, Valkey and WebCAF with:

```shell
uv sync
docker compose up -d postgres redis
uv run python manage.py migrate
uv run python manage.py runserver 0.0.0.0:8010
```

Open `http://localhost:8010`. The normal DEX Docker Compose workflow uses the same host port, so stop that stack before running the One Login integration server.

## User mapping and authorisation

One Login must return `sub`, `email` and `email_verified=true`. WebCAF matches one non-staff Django user by email or creates a new Django user with an unusable password.

New users can be created only when their email domain has an exact matching `Allowed email domain` entry in Django admin. The allowlist applies to GOV.UK One Login, DEX and generic OIDC, and an empty allowlist denies all new automatic users. It does not affect existing users, Django admin, management commands or WebCAF's user-management form. Add each permitted subdomain separately. Rejected users see a domain-specific error page and the attempt is logged with a masked email address.

Authentication does not create a `UserProfile`, assign an organisation or assign a role. A newly created user reaches the existing no-profile page with a 403 response until a WebCAF administrator creates the appropriate profile. Existing profiles remain attached when a pre-provisioned user is matched.

Email is currently the account-linking identifier. If a user's One Login email changes, an administrator may need to reconcile the WebCAF account. Durable provider subject mapping is deferred until multiple external authentication providers are introduced.

## Authentication policy

WebCAF requests:

```text
Scopes:              openid email
Authentication:      Cl.Cm
Identity confidence: P0
```

WebCAF's email OTP is disabled in `one-login` mode because `Cl.Cm` provides medium-level authentication. Back-channel logout is disabled. User-initiated logout clears the WebCAF session and uses One Login front-channel logout.

Provider denials, incomplete callbacks, token exchange failures and identities that cannot be mapped are redirected to a generic authentication error page. State and token validation failures remain bad requests rather than being hidden.

## Runtime configuration

Set these non-secret variables in `.env` or the deployment environment:

```text
SSO_MODE=one-login
GOV_UK_ONE_LOGIN_CLIENT_ID
GOV_UK_ONE_LOGIN_OPENID_CONFIG_URL
GOV_UK_ONE_LOGIN_SCOPE
GOV_UK_ONE_LOGIN_ENVIRONMENT
```

Configure exactly one private-key source:

```text
GOV_UK_ONE_LOGIN_CLIENT_SECRET
GOV_UK_ONE_LOGIN_PRIVATE_KEY_PATH
```

`GOV_UK_ONE_LOGIN_CLIENT_SECRET` is the package's name for the base64-encoded RSA private key. Use this form with AWS Secrets Manager or an equivalent deployment secret store. `GOV_UK_ONE_LOGIN_PRIVATE_KEY_PATH` is intended for local development and must point to the PEM file.

Continue to provide WebCAF's existing `SECRET_KEY`, database, host, domain, Notify and other environment-specific settings. No credential or private key should be included in an image, ordinary environment configuration or source control.

## ECS deployment

Store the base64-encoded PEM private key in AWS Secrets Manager and inject it into the ECS task as `GOV_UK_ONE_LOGIN_CLIENT_SECRET`. Do not set `GOV_UK_ONE_LOGIN_PRIVATE_KEY_PATH` in ECS.

The task execution role must allow `secretsmanager:GetSecretValue` for the secret and, when the secret uses a customer-managed KMS key, `kms:Decrypt` for that key. Do not put the value in the task definition's ordinary `environment` section, container image, logs or source control.

If the secret is a JSON object, configure the task-definition `valueFrom` ARN to select the key holding the base64-encoded PEM. Register the matching public key with GOV.UK One Login. After rotating the secret or registered key, start new ECS tasks so the updated secret is injected.

## AWS sandbox registration

When the sandbox hostname is available, register these exact URLs in the One Login console:

```text
Redirect URI:             https://<sandbox-host>/one-login/callback/
Post-logout redirect URI: https://<sandbox-host>/
```

The application builds callback and post-logout URLs from the incoming request. It uses `X-Forwarded-Proto` to identify HTTPS requests independently of debug mode, so the load balancer must preserve the public host and set an authoritative `X-Forwarded-Proto=https` value. Requests without that value, including normal local development over HTTP, remain HTTP.

This configuration assumes the application can only be reached through the trusted load balancer or proxy, and that the final trusted proxy replaces any client-supplied `X-Forwarded-Proto` value. Django does not verify the source of this header. If an untrusted client can reach the application directly, a client-supplied value must not be trusted; network controls must prevent direct access to the application target.

# GDS Internal Access locally and in sandbox

GDS Internal Access is the application and container default for local development
and the selected provider for sandbox. Sandbox must also be configured in ECS and
the deployment workflow as described below. One Login and DEX remain available as
explicitly selected alternatives. Staging and production retain their existing
provider selections.

## Authentication architecture

`SSO_MODE=internal-access` selects `webcaf.auth.OIDCBackend` and
`InternalAccessCallbackView`. Unauthenticated requests to protected pages start the
OIDC flow through `/oidc/authenticate/`. After the provider returns to
`/oidc/callback/`, the OIDC library exchanges the code and validates the token and
nonce before WebCAF establishes a Django session. The normal landing page is
`/my-account/`; existing assessor/reviewer routing still applies after that.

WebCAF's additional email OTP is disabled in Internal Access mode. Profiles,
organisations and roles continue to be managed within WebCAF.

Internal Access matches non-staff users by case-insensitive email, including accounts
whose username differs from their email. Multiple matching accounts are rejected;
administrators must reconcile these accounts before rollout. Other generic OIDC
modes retain their existing username-and-email matching. Existing user IDs and
profile associations are preserved. Inactive users cannot establish a session.

New accounts follow the existing exact email-domain allowlist. An empty allowlist
denies new automatic accounts. New users have an unusable password and receive no
profile, organisation or role automatically. A user without a profile receives the
existing 403 no-profile page. Existing users are not subjected to the new-account
domain check. Email is the linking identifier; durable provider-subject linking is
not implemented.

## Local setup

Copy `webcaf/.env.example` to the ignored `webcaf/.env`. Obtain a registered local
client ID and secret through the agreed secure channel and fill in the empty values.
Register `http://localhost:8010/oidc/callback/` with IA and configure the client's
`app_url` as the intended local return URL after logout.
Use the provider endpoints confirmed for that client; the example lists the current
integration endpoint configuration. Do not use sandbox credentials without agreement.

`docker compose up --build -d` starts WebCAF, PostgreSQL, Valkey and initialization.
It does not start One Login or DEX. The containers read IA credentials from
`webcaf/.env`; Compose selects Internal Access unless explicitly overridden. A
client and credentials are required for real IA sign-in, including when running locally.

For Django on the host, ensure the private `.env` also selects Internal Access, start
`docker compose up -d postgres redis`, then run migrations and Django on port 8010.
Never commit the private `.env` or include it in an image.

Use `make up_one_login` or `make up_dex` to explicitly activate an alternative in Docker.
For the host One Login workflow, set the documented simulator values in `.env` and use
`make up_one_login_simulator` to start dependencies only. Explicit automated test and
BDD configurations continue to use simulators; they do not change the developer default.

## Sandbox runtime configuration

Configure the following on the sandbox ECS container:

```text
SSO_MODE=internal-access
INTERNAL_ACCESS_CLIENT_ID=<registered sandbox client ID>
INTERNAL_ACCESS_AUTHORIZATION_ENDPOINT=<registered provider authorization endpoint>
INTERNAL_ACCESS_TOKEN_ENDPOINT=<registered provider token endpoint>
INTERNAL_ACCESS_USERINFO_ENDPOINT=<registered provider UserInfo endpoint>
INTERNAL_ACCESS_JWKS_ENDPOINT=<registered provider JWKS endpoint>
INTERNAL_ACCESS_LOGOUT_ENDPOINT=<registered provider logout endpoint>
```

Pass `INTERNAL_ACCESS_SECRET_ARN` from the Sandbox GitHub environment into the ECS
container environment. WebCAF retrieves the secret directly using the ECS task role
and extracts `INTERNAL_ACCESS_CLIENT_SECRET` from its JSON `SecretString`:

```json
{"INTERNAL_ACCESS_CLIENT_SECRET": "<client secret>"}
```

The task role (not only the execution role) needs `secretsmanager:GetSecretValue`
permission for that secret and KMS decryption permission where applicable. No AWS
access keys are configured in the application. The SDK uses workload credentials.
`AWS_REGION` selects the region, falling back to `AWS_DEFAULT_REGION` and then
`eu-west-2`. The secret is read when each application process loads its settings,
not on each request. Redeploy after rotating the secret or changing its ARN.

When an ARN is configured, retrieval or JSON validation failure stops startup; the
application does not silently fall back to an environment secret. Error messages
exclude secret values and provider response details. Without an ARN, local development
continues to read `INTERNAL_ACCESS_CLIENT_SECRET` from the ignored `.env`.

Changing to a replacement secret requires changing the configured ARN and redeploying,
with the same JSON key and appropriate task-role access. Never put secret values in
ordinary deployment variables, build arguments or images.

Register the exact sandbox callback URI
`https://<sandbox-host>/oidc/callback/` with Internal Access and configure the
client's `app_url` as the intended sandbox return URL after logout.

The trusted load balancer must preserve the public host and set
`X-Forwarded-Proto=https`; callback URLs are built from the incoming request.
Keep the application inaccessible through routes that bypass this trusted proxy.

The sandbox deployment workflow currently reuses the existing ECS task definition.
The IA variables, including `INTERNAL_ACCESS_SECRET_ARN`, must be present in the
rendered definition before deployment. Repository changes alone do not register the client, provision
secrets or verify the deployed configuration.

## Failure handling and logging

Provider denials, incomplete callbacks and unresolved accounts use the existing
authentication-error page. Provider request failures also use this page. Failed
callbacks clear the local session and stored tokens, retaining only the flag needed
to display the approved-domain error message. Invalid state and token validation
errors retain the OIDC library's secure error handling.

The IA callback logs successful authentication by WebCAF user ID and logs failed
authentication without provider error descriptions, response bodies or tokens.
Existing account-provisioning logs mask email addresses. Logs use the existing
console logging and deployed monitoring configuration.

An IA-hosted “No access” page is controlled by Internal Access and may prevent the
browser from reaching WebCAF's callback. Its wording and support contact cannot be
changed in WebCAF templates. Test this separately from a denial returned to WebCAF.

Logout is a POST to WebCAF's `/logout/`. It clears the Django session and redirects
to IA's configured `/sign-out` endpoint with `to_client=<client ID>`, even when no
ID token remains locally. In the reviewed IA implementation, this endpoint clears
the IA session and returns to the client's registered `app_url`. It does not use
`id_token_hint`, `client_id` or `redirect_uri` for this flow. `LOGOUT_REDIRECT_URL`
does not control IA's return URL; it remains available for generic OIDC providers.
IA's `from_app` parameter displays a confirmation page rather than immediately
clearing the session, so WebCAF does not use it for this redirect.

Automated tests verify the generated request. Confirm the deployed IA service's
logout behaviour and registered `app_url` during local and sandbox verification.

## Retaining and re-enabling One Login

Keep One Login's client registration and securely stored private key. Do not build
the key into the sandbox image. See [One Login runtime and ECS configuration](GOV_UK_ONE_LOGIN.md).
To switch back, set sandbox `SSO_MODE=one-login`, supply the documented One Login
settings and inject `GOV_UK_ONE_LOGIN_CLIENT_SECRET` at runtime. Remove any ordinary
`GOV_UK_ONE_LOGIN_PRIVATE_KEY_PATH` setting when using the runtime secret, because
the two key sources are mutually exclusive. Register the matching
`https://<sandbox-host>/one-login/callback/` URI and start new ECS tasks.

## Automated tests

The focused regression suite explicitly selects One Login as its test configuration.
The Internal Access tests override the relevant settings and mock the provider
exchange; this does not change the default provider for development or deployment:

```shell
SSO_MODE=one-login uv run pytest tests/test_internal_access_settings.py tests/test_internal_access_flow.py tests/test_oidc_backend.py tests/test_auth_middleware.py tests/test_one_login_backend.py tests/test_one_login_flow.py tests/test_logout_view.py
```

Automated tests mock the Internal Access provider. They do not verify connectivity
or authentication against the live service.

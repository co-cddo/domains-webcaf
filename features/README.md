# BDD feature tests

Run these commands from the repository root. They require Make and a recent Docker Compose release with support for the
`!override` and `!reset` YAML tags used by the feature-test overrides. See the main [developer guide](../README.md) for
the general setup and unit-test workflow.

Feature tests run in dedicated Docker Compose projects with their own PostgreSQL database, Valkey instance, network
and volumes. The default One Login suite uses `webcaf-behave`; focused DEX coverage uses `webcaf-behave-dex`. Neither
project publishes host ports, so the tests can run while the normal development stack is running.

The automated suite explicitly selects the One Login simulator; normal local development uses GDS Internal Access.
`make behave` runs the application, focused One Login and
provider-independent Django admin scenarios while excluding scenarios tagged `@dex`. `make behave_dex` runs only the
scenarios tagged `@dex` that explicitly verify DEX login and logout.

Each target removes stale resources before the run, checks that model changes have committed migrations, applies the
migrations, creates scenario data and removes the test containers, network and volumes afterwards. Cleanup runs
whether the scenarios pass or fail. The normal development database, containers and Python virtual environment are
not used.

Application and Behave sources are built into the test images instead of mounting the repository at runtime. The only
host directories mounted by the test runner are `reports/` and `artifacts/`; the tracked One Login test key is supplied
as a read-only Compose secret. The focused DEX image also contains its test configuration rather than mounting
`oauth-stub/`.

The identifiers in `behave.ini` are cleanup filters used between scenarios so each scenario starts from predictable
state in the disposable database. They do not restrict which records a scenario may create.

## Commands

```shell
# Run the default One Login suite.
make behave

# Run only the focused One Login scenarios.
make behave FEATURE_TEST_ARGS="--tags=one_login"

# Run the focused DEX authentication scenarios.
make behave_dex

# Run a selected provider-independent feature with One Login services available.
make behave FEATURE_TEST_ARGS="-i admin-login.feature"
```

The containerized workflow is headless by default. Pass `-D headless_testing=false` through `FEATURE_TEST_ARGS` only
when the environment supports headed Playwright. Do not run Behave directly against the normal development Compose
stack because that bypasses the disposable test database.

The HTML report is written to `reports/report.html`. Failed scenarios write screenshots and page HTML to
`artifacts/`. A failed One Login run writes `artifacts/one-login-docker-compose.log`; a failed DEX run writes
`artifacts/dex-docker-compose.log` before cleanup.

If a run is forcibly terminated before cleanup completes, the next invocation removes stale resources before creating
a fresh environment. Both isolated projects can also be removed explicitly with:

```shell
make behave-clean
```

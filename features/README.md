#  BDD Testing framework
This assumes that the application, the SSO system and the database systems are already running.

The behave.ini file contains the names of the user emails and the organisations that can be used in the testing.
This is fixed so that the cleanup process can reset the database to its orignal state before each scenario is run.

## Disable headless mode
Sometimes it is easy to debug when we see what is displayed on the browser. To view the browser window, we have to
disable the headless mode by providing a user data parameter.

You will need to add ```-D headless_testing=false``` to the main command to get this set up.

Command to run.
```shell
#  This will run the tests in headless mode.
  make behave

  #  This will run the selected tests in headless mode.
  make behave FEATURE_TEST_ARGS="-i admin-login.feature"

  # If you want to see the browser window, then you will need to invoke
  # behave directly from the command line.
  # Single command: start containers and run the tests with browser visible.
  docker compose -f docker-compose.yml up -d && \
    SSO_MODE=localhost \
    DATABASE_URL=postgresql://webcaf:webcaf@localhost:54321/webcaf \  #  pragma: allowlist secret
    SECRET_KEY=unused \
    poetry run behave -D headless_testing=false
```

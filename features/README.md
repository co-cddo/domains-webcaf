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
  SSO_MODE: localhost DATABASE_URL=<db connection> poetry run behave
```

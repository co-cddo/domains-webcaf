#!/bin/bash
#Wrapper file to pass the environment variables for the mypy pre-commit command

export SSO_MODE=none

exec mypy "$@"

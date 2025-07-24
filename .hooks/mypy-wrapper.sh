#!/bin/bash
#Wrapper file to pass the environment variables for the mypy pre-commit command

export LOCAL_SSO=True

exec mypy "$@"

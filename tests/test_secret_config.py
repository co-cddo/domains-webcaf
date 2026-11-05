import json
from unittest.mock import patch

import pytest
from botocore.exceptions import ClientError, NoCredentialsError
from django.core.exceptions import ImproperlyConfigured

from webcaf.secret_config import get_internal_access_client_secret

SECRET_ARN = "arn:aws:secretsmanager:eu-west-2:123456789012:secret:internalAccess-test"  # pragma: allowlist secret


@patch("webcaf.secret_config.boto3.client")
def test_fetches_internal_access_json_secret_using_workload_credentials(create_client):
    create_client.return_value.get_secret_value.return_value = {
        "SecretString": json.dumps({"INTERNAL_ACCESS_CLIENT_SECRET": "dummy-client-secret"})
    }

    assert get_internal_access_client_secret(SECRET_ARN, "eu-west-2") == "dummy-client-secret"
    create_client.return_value.get_secret_value.assert_called_once_with(SecretId=SECRET_ARN)
    assert create_client.call_args.args == ("secretsmanager",)
    assert create_client.call_args.kwargs["region_name"] == "eu-west-2"
    assert "aws_access_key_id" not in create_client.call_args.kwargs
    assert "aws_secret_access_key" not in create_client.call_args.kwargs


@pytest.mark.parametrize(
    "response",
    [
        {"SecretBinary": b"unsupported"},
        {"SecretString": "not-json-sensitive-value"},  # pragma: allowlist secret
        {"SecretString": "[]"},
        {"SecretString": "{}"},
        {"SecretString": '{"INTERNAL_ACCESS_CLIENT_SECRET": null}'},
        {"SecretString": '{"INTERNAL_ACCESS_CLIENT_SECRET": 42}'},
        {"SecretString": '{"INTERNAL_ACCESS_CLIENT_SECRET": "  "}'},
    ],
)
@patch("webcaf.secret_config.boto3.client")
def test_rejects_invalid_secret_without_exposing_value(create_client, response):
    create_client.return_value.get_secret_value.return_value = response

    with pytest.raises(ImproperlyConfigured) as error:
        get_internal_access_client_secret(SECRET_ARN, "eu-west-2")

    assert "not-json-sensitive-value" not in str(error.value)


@pytest.mark.parametrize(
    "failure",
    [
        NoCredentialsError(),
        ClientError({"Error": {"Code": "AccessDeniedException", "Message": "sensitive"}}, "GetSecretValue"),
    ],
)
@patch("webcaf.secret_config.boto3.client")
def test_aws_failure_stops_startup_with_safe_error(create_client, failure):
    create_client.return_value.get_secret_value.side_effect = failure

    with pytest.raises(ImproperlyConfigured, match="Unable to retrieve") as error:
        get_internal_access_client_secret(SECRET_ARN, "eu-west-2")

    assert "sensitive" not in str(error.value)
    assert error.value.__suppress_context__

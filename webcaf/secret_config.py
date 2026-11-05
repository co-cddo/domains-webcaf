"""Load application configuration secrets using the workload's AWS credentials."""

import json

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from django.core.exceptions import ImproperlyConfigured


def get_internal_access_client_secret(secret_arn: str, region: str) -> str:
    """Read the IA JSON secret at startup without exposing provider error details."""
    try:
        client = boto3.client(
            "secretsmanager",
            region_name=region,
            config=Config(connect_timeout=5, read_timeout=5, retries={"mode": "standard", "max_attempts": 2}),
        )
        response = client.get_secret_value(SecretId=secret_arn)
    except (BotoCoreError, ClientError):
        raise ImproperlyConfigured("Unable to retrieve the Internal Access secret from Secrets Manager") from None

    raw_secret = response.get("SecretString")
    if not isinstance(raw_secret, str):
        raise ImproperlyConfigured("The Internal Access secret must contain a JSON SecretString")
    try:
        values = json.loads(raw_secret)
    except ValueError:
        raise ImproperlyConfigured("The Internal Access secret must contain valid JSON") from None

    secret = values.get("INTERNAL_ACCESS_CLIENT_SECRET") if isinstance(values, dict) else None
    if not isinstance(secret, str) or not secret.strip():
        raise ImproperlyConfigured("The Internal Access secret requires a non-empty INTERNAL_ACCESS_CLIENT_SECRET")
    return secret

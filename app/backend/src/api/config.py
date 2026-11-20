"""Settings, read from environment variables and checked when the app starts.

A wrong or missing setting stops the app at start-up, with a clear message, instead of
failing later on some request.
"""

import os
from functools import lru_cache
from typing import Literal, Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Lambda sets this variable in every function. Its presence means "running in AWS".
LAMBDA_MARKER = "AWS_LAMBDA_FUNCTION_NAME"


class Settings(BaseSettings):
    """Each field is read from the environment variable of the same name, in capitals."""

    model_config = SettingsConfigDict(extra="ignore")

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # The one DynamoDB table (I-08).
    dynamodb_table: str = "productivity-app-data"

    # Only for the laptop: the address of DynamoDB Local. In AWS it stays unset and the
    # AWS SDK finds the real DynamoDB by itself. Terraform never sets it.
    dynamodb_endpoint_url: str | None = None

    # Folder with the built React app (index.html and assets/). Set in the runtime image,
    # where the build is copied in; unset locally, where Vite serves the frontend
    # (ADR-0007).
    static_dir: str | None = None

    # ---- Sign-in (B4, ADR-0003) -------------------------------------------------------
    # "cognito": tokens from our Cognito user pool. The only mode Terraform uses (it does
    # not even set this variable, so the default applies).
    # "local": tokens from the local OIDC server in Compose (B4-05). Refused in Lambda.
    auth_mode: Literal["cognito", "local"] = "cognito"

    # Lambda sets AWS_REGION itself.
    aws_region: str = "us-east-1"

    # Set by Terraform. Not secret: the browser sees all three anyway.
    cognito_user_pool_id: str | None = Field(
        default=None, pattern=r"^[a-z]{2}-[a-z]+-\d_[A-Za-z0-9]+$"
    )
    cognito_client_id: str | None = Field(default=None, pattern=r"^[a-z0-9]{1,128}$")
    # The hosted sign-in address, for example https://tethrix-app.auth.us-east-1.amazoncognito.com
    cognito_domain: str | None = Field(
        default=None, pattern=r"^https://[a-z0-9-]+\.auth\.[a-z]{2}-[a-z]+-\d\.amazoncognito\.com$"
    )

    # Local mode only. The issuer is the address the browser uses (localhost); the keys
    # are fetched by the backend container, which reaches the server by its Compose name.
    local_oidc_issuer: str | None = None
    local_oidc_jwks_url: str | None = None
    local_oidc_client_id: str | None = None

    @model_validator(mode="after")
    def _local_settings_never_in_lambda(self) -> Self:
        # A deployed function pointed at some other "DynamoDB" address would send user
        # data there, and one that trusts a local token issuer lets anyone sign in as
        # anyone (T-004). Refuse to start instead (SR-06).
        if LAMBDA_MARKER not in os.environ:
            return self
        if self.dynamodb_endpoint_url is not None:
            raise ValueError("DYNAMODB_ENDPOINT_URL is a local-only setting; it is set in Lambda")
        if self.auth_mode != "cognito":
            raise ValueError("AUTH_MODE=local is a local-only setting; it is set in Lambda")
        if self.local_oidc_issuer or self.local_oidc_jwks_url or self.local_oidc_client_id:
            raise ValueError("LOCAL_OIDC_* are local-only settings; one is set in Lambda")
        if not (self.cognito_user_pool_id and self.cognito_client_id and self.cognito_domain):
            raise ValueError(
                "COGNITO_USER_POOL_ID, COGNITO_CLIENT_ID and COGNITO_DOMAIN are required in Lambda"
            )
        return self

    @property
    def issuer_url(self) -> str | None:
        """Who must have signed the tokens, or None when sign-in is not configured."""
        if self.auth_mode == "local":
            return self.local_oidc_issuer
        if self.cognito_user_pool_id is None:
            return None
        # Built from the pool ID, so it is always an AWS Cognito address (guard 3, B4-05).
        return f"https://cognito-idp.{self.aws_region}.amazonaws.com/{self.cognito_user_pool_id}"

    @property
    def app_client_id(self) -> str | None:
        return self.local_oidc_client_id if self.auth_mode == "local" else self.cognito_client_id

    @property
    def jwks_url(self) -> str | None:
        if self.auth_mode == "local":
            return self.local_oidc_jwks_url
        issuer = self.issuer_url
        return f"{issuer}/.well-known/jwks.json" if issuer else None


@lru_cache
def get_settings() -> Settings:
    """Read the settings once and reuse them."""
    return Settings()

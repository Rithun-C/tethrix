"""Settings, read from environment variables and checked when the app starts.

A wrong or missing setting stops the app at start-up, with a clear message, instead of
failing later on some request.
"""

import os
from functools import lru_cache
from typing import Literal, Self

from pydantic import model_validator
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

    @model_validator(mode="after")
    def _local_settings_never_in_lambda(self) -> Self:
        # A deployed function pointed at some other "DynamoDB" address would send user
        # data there. Refuse to start instead. Same idea as the local sign-in guard
        # planned for B4 (SR-06).
        if self.dynamodb_endpoint_url is not None and LAMBDA_MARKER in os.environ:
            raise ValueError("DYNAMODB_ENDPOINT_URL is a local-only setting; it is set in Lambda")
        return self


@lru_cache
def get_settings() -> Settings:
    """Read the settings once and reuse them."""
    return Settings()

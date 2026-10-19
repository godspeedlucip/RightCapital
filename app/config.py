from datetime import timedelta
import re
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = Field(alias="DATABASE_URL")
    internal_auth_token: str = Field(alias="INTERNAL_AUTH_TOKEN")
    worker_enabled: bool = Field(True, alias="WORKER_ENABLED")
    poll_interval: timedelta = Field(timedelta(seconds=1), alias="POLL_INTERVAL")
    lease_duration: timedelta = Field(timedelta(seconds=30), alias="LEASE_DURATION")
    request_timeout: timedelta = Field(timedelta(seconds=10), alias="REQUEST_TIMEOUT")
    max_attempts: int = Field(5, alias="MAX_ATTEMPTS")
    retry_delay: timedelta = Field(timedelta(seconds=10), alias="RETRY_DELAY")
    max_request_bytes: int = Field(1048576, alias="MAX_REQUEST_BYTES")
    allowed_hosts: str = Field("", alias="ALLOWED_HOSTS")

    @field_validator("poll_interval", "lease_duration", "request_timeout", "retry_delay", mode="before")
    @classmethod
    def parse_duration(cls, value):
        if isinstance(value, str):
            match = re.fullmatch(r"\s*([0-9]+(?:\.[0-9]+)?)\s*(ms|s|m|h)\s*", value)
            if match:
                amount = float(match.group(1)); unit = match.group(2)
                factor = {"ms": 0.001, "s": 1, "m": 60, "h": 3600}[unit]
                value = timedelta(seconds=amount * factor)
        return value

    @field_validator("poll_interval", "lease_duration", "request_timeout", "retry_delay")
    @classmethod
    def positive_duration(cls, value: timedelta) -> timedelta:
        if value.total_seconds() <= 0:
            raise ValueError("duration must be positive")
        return value

    @model_validator(mode="after")
    def validate_relationships(self):
        if self.max_attempts < 1 or self.max_request_bytes < 1:
            raise ValueError("MAX_ATTEMPTS and MAX_REQUEST_BYTES must be positive")
        if self.lease_duration <= self.request_timeout:
            raise ValueError("LEASE_DURATION must be greater than REQUEST_TIMEOUT")
        return self

    def host_allowlist(self) -> set[str]:
        return {host.strip().lower() for host in self.allowed_hosts.split(",") if host.strip()}

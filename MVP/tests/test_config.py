import pytest
from pydantic import ValidationError
from app.config import Settings

def test_defaults_and_relationships():
    settings = Settings(DATABASE_URL="sqlite:///test.db", INTERNAL_AUTH_TOKEN="secret")
    assert settings.max_attempts == 5
    assert settings.retry_delay.total_seconds() == 10
    assert settings.lease_duration > settings.request_timeout

def test_required_values():
    with pytest.raises(ValidationError):
        Settings()

def test_invalid_lease_is_rejected():
    with pytest.raises(ValidationError):
        Settings(DATABASE_URL="sqlite:///test.db", INTERNAL_AUTH_TOKEN="secret", LEASE_DURATION="5s")

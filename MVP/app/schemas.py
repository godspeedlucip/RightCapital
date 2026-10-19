from typing import Any
from pydantic import BaseModel, Field, field_validator

class TargetIn(BaseModel):
    url: str
    method: str = "POST"
    headers: dict[str,str] = Field(default_factory=dict)
    body: Any = Field(default_factory=dict)

class NotificationIn(BaseModel):
    provider: str = Field(min_length=1,max_length=128)
    event_type: str = Field(min_length=1,max_length=128)
    target: TargetIn
    idempotency_key: str|None = Field(default=None,max_length=256)
    @field_validator("target")
    @classmethod
    def normalize_method(cls,v):
        v.method=v.method.upper() or "POST";return v

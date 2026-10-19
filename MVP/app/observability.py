import json
import logging

SENSITIVE={"authorization","cookie","x-api-key","proxy-authorization"}
def redact_headers(headers: dict) -> dict: return {k:("[REDACTED]" if k.lower() in SENSITIVE else v) for k,v in headers.items()}
def log_transition(logger: logging.Logger, **fields): logger.info(json.dumps(fields,default=str,sort_keys=True))
class Metrics:
    def __init__(self): self.created=self.delivered=self.failed=self.pending=0

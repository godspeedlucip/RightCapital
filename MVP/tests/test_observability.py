from app.observability import redact_headers
def test_redacts_sensitive_headers():
    result=redact_headers({"Authorization":"secret","Cookie":"session","Content-Type":"application/json"})
    assert result["Authorization"]=="[REDACTED]" and result["Cookie"]=="[REDACTED]" and result["Content-Type"]=="application/json"

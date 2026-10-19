CREATE TABLE IF NOT EXISTS notifications (
  id VARCHAR(64) PRIMARY KEY, provider VARCHAR(128) NOT NULL, event_type VARCHAR(128) NOT NULL,
  target_url TEXT NOT NULL, http_method VARCHAR(16) NOT NULL, headers_json JSON NOT NULL, body_json JSON NOT NULL,
  idempotency_key VARCHAR(256), request_digest VARCHAR(64) NOT NULL,
  status VARCHAR(32) NOT NULL, attempt_count INTEGER NOT NULL CHECK (attempt_count >= 0), max_attempts INTEGER NOT NULL CHECK (max_attempts >= 1),
  next_attempt_at TIMESTAMP WITH TIME ZONE NOT NULL, lease_until TIMESTAMP WITH TIME ZONE,
  last_error_code VARCHAR(64), last_error_message TEXT, created_at TIMESTAMP WITH TIME ZONE NOT NULL, updated_at TIMESTAMP WITH TIME ZONE NOT NULL, delivered_at TIMESTAMP WITH TIME ZONE
);
CREATE INDEX IF NOT EXISTS poll_idx ON notifications(status, next_attempt_at, created_at);
CREATE INDEX IF NOT EXISTS lease_idx ON notifications(status, lease_until);

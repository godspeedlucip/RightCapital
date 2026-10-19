# API Notification Service MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a runnable internal notification service that persists notification tasks, asynchronously delivers them at least once to HTTP(S) suppliers, retries temporary failures, recovers expired leases, and provides a README plus truthful AI usage notes required by the assignment.

**Architecture:** A Go HTTP API accepts authenticated notification requests, validates the target and payload, and stores them in PostgreSQL before returning `202 Accepted`. A Worker polls the same database, atomically claims tasks with a lease, sends the HTTP request, and updates the task through `PENDING`, `DELIVERING`, `RETRY_WAITING`, `DELIVERED`, and `FAILED`. The MVP uses a database task table instead of a message queue; the database is the source of truth for recovery and status queries.

**Tech Stack:** Go 1.22+; standard `net/http`, `database/sql`, and `testing`; PostgreSQL; `github.com/jackc/pgx/v5/stdlib`; Docker Compose; SQL migrations; httptest-based supplier server.

**Spec:** [docs/superpowers/specs/2026-10-14-api-notification-service-design.md](../specs/2026-10-14-api-notification-service-design.md)

## Global Constraints

- Delivery semantics are at-least-once; strict exactly-once delivery is explicitly not promised.
- The API must persist a task before returning `202 Accepted`; a database failure returns `5xx` without a successful task ID.
- Supported target schemes are only `http` and `https`; production must support an allowlist or equivalent egress restriction.
- System-generated `Idempotency-Key` and `X-Notification-ID` headers cannot be overridden by the caller.
- Default retry configuration is `MAX_ATTEMPTS=5`, `RETRY_DELAY=10s`, `REQUEST_TIMEOUT=10s`, `POLL_INTERVAL=1s`, and `LEASE_DURATION=30s`.
- `attempt_count` counts HTTP requests actually started; the first request is attempt 1 while stored `attempt_count` starts at 0.
- HTTP `2xx` is success; network errors, timeouts, `408`, `425`, `429`, `500`, `502`, `503`, and `504` are retryable; the specified `4xx` and security/validation failures are terminal.
- All timestamps are server-generated UTC RFC 3339 values at the API boundary.
- Sensitive headers, credentials, and complete request bodies must not appear in logs or status responses.
- MVP does not include a queue, supplier management UI, workflow orchestration, business-response compensation, multi-region failover, or automatic capacity management.
- Integration tests must use a local test supplier and must not depend on real third-party accounts.
- The final repository must contain a project README, runnable MVP code, and a truthful AI usage explanation.

## Review Focus

- A supplier returns a response after the Worker loses the connection: the task must remain retryable and may produce a duplicate, never silently disappear; test in Task 4.
- Two Workers race to claim the same task: exactly one conditional update may win; test in Task 2.
- The same `idempotency_key` is submitted with different payload content: the API must return `409 Conflict` and leave the original task unchanged; test in Task 3.
- A caller attempts to use an internal/private target or override system idempotency headers: validation/security policy must reject it or apply the configured allowlist; test in Task 3.
- A Worker crashes with a task in `DELIVERING`: after `lease_until` expires, another Worker must reclaim it without overwriting an active lease; test in Task 4.

---

### Task 1: Project Bootstrap, Configuration, and Local Runtime

**Files:**
- Create: `go.mod`
- Create: `cmd/notificationd/main.go`
- Create: `internal/config/config.go`
- Create: `internal/config/config_test.go`
- Create: `.env.example`
- Create: `docker-compose.yml`
- Create: `Makefile`
- Create: `.gitignore`

**Interfaces:**
- Produces `config.Config` with typed fields for `DatabaseURL`, `InternalAuthToken`, `WorkerEnabled`, `PollInterval`, `LeaseDuration`, `RequestTimeout`, `MaxAttempts`, `RetryDelay`, `MaxRequestBytes`, and optional supplier host allowlist.
- Produces `config.Load(environ func(string) string) (config.Config, error)`.
- Produces startup validation requiring `DATABASE_URL` and `INTERNAL_AUTH_TOKEN`, positive durations, `MAX_ATTEMPTS >= 1`, and `LEASE_DURATION > REQUEST_TIMEOUT`.

- [ ] **Step 1: Write failing configuration tests** for defaults, missing required values, invalid durations, and invalid lease/timeout relationships.
- [ ] **Step 2: Run `go test ./internal/config` and verify the tests fail** because configuration types and loader do not exist.
- [ ] **Step 3: Implement typed configuration loading and validation** in `internal/config/config.go`; keep environment parsing independent of HTTP and database packages.
- [ ] **Step 4: Add the minimal application entrypoint and local runtime files** so the service can load configuration and fail fast with a clear error before opening listeners.
- [ ] **Step 5: Run `go test ./internal/config` and `go test ./...`**; expected result is PASS for configuration tests and a compiling repository.
- [ ] **Step 6: Commit** with `git add go.mod cmd internal/config .env.example docker-compose.yml Makefile .gitignore && git commit -m "chore: bootstrap notification service"`.

### Task 2: Domain Model, Database Schema, Repository, and Idempotency

**Files:**
- Create: `internal/notification/model.go`
- Create: `internal/notification/model_test.go`
- Create: `internal/repository/repository.go`
- Create: `internal/repository/postgres.go`
- Create: `internal/repository/postgres_test.go`
- Create: `migrations/001_create_notifications.sql`
- Modify: `Makefile`

**Interfaces:**
- Consumes `config.Config.DatabaseURL`.
- Produces `notification.Notification`, `notification.CreateInput`, `notification.Status`, and `notification.StatusView`.
- Produces repository methods:
  - `Create(ctx context.Context, input notification.CreateInput) (notification.Notification, error)`
  - `Get(ctx context.Context, id string) (notification.Notification, error)`
  - `ClaimNext(ctx context.Context, now time.Time, leaseUntil time.Time) (notification.Notification, bool, error)`
  - `RecoverExpiredLeases(ctx context.Context, now time.Time) (int64, error)`
  - `MarkDelivered(ctx context.Context, id string, attempt int, deliveredAt time.Time) error`
  - `MarkRetry(ctx context.Context, id string, attempt int, nextAttemptAt time.Time, code string, message string) error`
  - `MarkFailed(ctx context.Context, id string, attempt int, code string, message string) error`
- The repository must enforce conditional state updates using task ID plus current status/lease predicates.

- [ ] **Step 1: Write failing model and repository contract tests** covering valid state values, idempotent creation, conflicting idempotency content, atomic claim races, conditional completion, and expired lease recovery.
- [ ] **Step 2: Run the repository tests against a temporary PostgreSQL test database** and verify failures identify missing schema/repository behavior.
- [ ] **Step 3: Create the migration** with the `notifications` table, status/check constraints, JSON columns, timestamps, idempotency uniqueness, and the required polling and lease indexes.
- [ ] **Step 4: Implement the domain model and PostgreSQL repository** using transactions and conditional updates; distinguish “same idempotency key and same request digest” from `409 Conflict` content mismatch.
- [ ] **Step 5: Add migration and database lifecycle commands** to `Makefile` and verify the repository integration tests pass, including the two-Worker claim race.
- [ ] **Step 6: Commit** with `git add internal/notification internal/repository migrations Makefile && git commit -m "feat: persist notification tasks"`.

### Task 3: Authenticated HTTP API, Validation, and Status Queries

**Files:**
- Create: `internal/api/handler.go`
- Create: `internal/api/request.go`
- Create: `internal/api/validation.go`
- Create: `internal/api/handler_test.go`
- Modify: `cmd/notificationd/main.go`

**Interfaces:**
- Consumes the repository interface from Task 2 and `config.Config.InternalAuthToken`.
- Produces `POST /v1/notifications` and `GET /v1/notifications/{notification_id}`.
- Produces request types matching the spec: `provider`, `event_type`, `target.url`, `target.method`, `target.headers`, `target.body`, and optional `idempotency_key`.
- Produces exact behavior: `202` after commit, `400` malformed input, `401/403` auth failure, `409` idempotency conflict, `422` policy/size validation failure, `404` missing task, and `500` persistence failure.

- [ ] **Step 1: Write failing handler tests** for successful creation, malformed JSON, missing fields, auth failure, unsupported scheme, oversized request, forbidden header override, unknown task, and same/different idempotency submissions.
- [ ] **Step 2: Run `go test ./internal/api` and verify the tests fail** because the handlers and validation functions do not exist.
- [ ] **Step 3: Implement request decoding and validation** with bounded body/header sizes, HTTP(S)-only URLs, non-empty bounded provider identifiers, POST-only MVP behavior, and configured host allowlist checks.
- [ ] **Step 4: Implement auth middleware and handlers**; use UTC RFC 3339 responses, never return supplier credentials/body in status output, and only return `202` after repository commit succeeds.
- [ ] **Step 5: Run `go test ./internal/api` and `go test ./...`**; expected result is PASS with all status mappings covered.
- [ ] **Step 6: Commit** with `git add internal/api cmd/notificationd/main.go && git commit -m "feat: add notification HTTP API"`.

### Task 4: HTTP Delivery Worker, Retry Classification, and Lease Recovery

**Files:**
- Create: `internal/delivery/http_client.go`
- Create: `internal/delivery/http_client_test.go`
- Create: `internal/worker/worker.go`
- Create: `internal/worker/worker_test.go`
- Modify: `cmd/notificationd/main.go`

**Interfaces:**
- Consumes repository methods from Task 2 and `config.Config` timing/retry values.
- Produces `delivery.Client.Do(ctx context.Context, task notification.Notification) (delivery.Result, error)`.
- Produces `delivery.Classify(result delivery.Result, err error) delivery.Outcome`.
- Produces `worker.Run(ctx context.Context) error`, which recovers expired leases, claims due tasks, sends requests, and writes conditional outcomes.
- The delivery client must inject `Idempotency-Key` and `X-Notification-ID`, reject redirects by default, apply the configured total timeout, and avoid storing response bodies.

- [ ] **Step 1: Write failing delivery tests** for 2xx success, retryable network/timeout errors, retryable 408/425/429/5xx responses, terminal 4xx responses, system header injection, and no response-body persistence.
- [ ] **Step 2: Write failing Worker tests** using an httptest supplier that returns `[503, 503, 200]`, `400`, and a delayed response; assert state transitions, attempt counts, fixed 10-second scheduling, and expired lease recovery.
- [ ] **Step 3: Run the focused delivery and Worker tests** and verify they fail for missing delivery and Worker implementations.
- [ ] **Step 4: Implement the HTTP client and explicit error classifier**; use fixed `RETRY_DELAY`, treat HTTP 2xx as success, and preserve the at-least-once behavior when the result is uncertain.
- [ ] **Step 5: Implement the Worker loop** with poll interval, atomic claim, lease recovery, context cancellation, conditional state writes, and no task deletion.
- [ ] **Step 6: Run `go test ./internal/delivery ./internal/worker ./...`**; expected result is PASS, including the race and crash/reclaim tests.
- [ ] **Step 7: Commit** with `git add internal/delivery internal/worker cmd/notificationd/main.go && git commit -m "feat: deliver notifications with retries"`.

### Task 5: Logging, Metrics, and Operational Safety

**Files:**
- Create: `internal/observability/logging.go`
- Create: `internal/observability/metrics.go`
- Create: `internal/observability/observability_test.go`
- Modify: `internal/api/handler.go`
- Modify: `internal/worker/worker.go`

**Interfaces:**
- Produces structured state-transition logging with `notification_id`, `provider`, `event_type`, `attempt_count`, `status`, `error_code`, and request duration.
- Produces counters or equivalent in-process metrics for created, delivered, failed, and pending tasks.
- Redaction must remove Authorization, Cookie, X-API-Key, complete bodies, and other configured sensitive headers.

- [ ] **Step 1: Write failing redaction and event tests** asserting sensitive values and bodies never appear in serialized log output.
- [ ] **Step 2: Implement structured logging and minimal metrics** without adding Prometheus or distributed tracing dependencies.
- [ ] **Step 3: Integrate logs/metrics at API creation, Worker state changes, and final failure points.**
- [ ] **Step 4: Run `go test ./internal/observability ./...`**; expected result is PASS and logs remain safe under test inputs.
- [ ] **Step 5: Commit** with `git add internal/observability internal/api internal/worker && git commit -m "feat: add safe observability"`.

### Task 6: End-to-End Acceptance Tests and Local Run Path

**Files:**
- Create: `internal/integration/notification_test.go`
- Create: `internal/integration/test_supplier.go`
- Modify: `Makefile`
- Modify: `docker-compose.yml`

**Interfaces:**
- Consumes the running API, Worker, migration, repository, and delivery components from Tasks 1–5.
- Produces a repeatable local test path using a local supplier server and PostgreSQL.
- Must verify the spec’s minimum matrix: create/PENDING, same idempotency key, conflicting idempotency key, 200/DELIVERED, 503/503/200 retry success, 400/FAILED, lease recovery, database failure, and URL policy rejection.

- [ ] **Step 1: Write the integration harness and failing acceptance tests** with a supplier response sequence and request recorder.
- [ ] **Step 2: Run the integration tests against Docker PostgreSQL** and verify failures expose missing end-to-end wiring.
- [ ] **Step 3: Implement only the wiring and test fixtures needed to make the acceptance matrix pass**; do not introduce a queue or external service.
- [ ] **Step 4: Add `make migrate`, `make run-api`, `make run-worker`, and `make test` commands** with documented prerequisites.
- [ ] **Step 5: Run the complete command `make test`**; expected result is all unit and integration tests passing without real supplier credentials.
- [ ] **Step 6: Commit** with `git add internal/integration Makefile docker-compose.yml && git commit -m "test: add end-to-end notification acceptance suite"`.

### Task 7: Project README, AI Usage Notes, and Final Verification

**Files:**
- Modify: `README.md`
- Create: `docs/ai-usage.md`
- Create: `scripts/check-docs.ps1`
- Modify: `docs/superpowers/specs/2026-10-14-api-notification-service-design.md` only if implementation decisions require a documented correction

**Interfaces:**
- Consumes the actual commands, environment variables, API examples, test names, and limitations produced by Tasks 1–6.
- Produces a README that explains problem understanding, architecture, system boundary, at-least-once semantics, failure handling, trade-offs, local setup, API examples, test execution, and known limitations.
- Produces `docs/ai-usage.md` with three truthful sections: AI assistance, rejected AI suggestions, and decisions made by the author with reasons.

- [ ] **Step 1: Write `scripts/check-docs.ps1`** to check required README headings/commands and the presence of all three AI usage sections; make it exit non-zero on a missing requirement.
- [ ] **Step 2: Rewrite `README.md` as the project README**; include `docker compose up -d db`, migration, API/Worker startup, create/query examples, test command, status semantics, and no-external-account acceptance path.
- [ ] **Step 3: Fill `docs/ai-usage.md` from the actual implementation history**; do not claim suggestions or decisions that did not occur.
- [ ] **Step 4: Run the documentation checks and `make test`**, then manually verify that README commands match the Makefile and environment variable names.
- [ ] **Step 5: Commit** with `git add README.md docs/ai-usage.md docs/superpowers/specs && git commit -m "docs: complete assignment delivery documentation"`.

## Final Verification

- [ ] Run `gofmt -w` on all Go files and `go vet ./...`.
- [ ] Run `make test` from a clean local database/container state.
- [ ] Verify API returns `202` only after persistence and `5xx` on database failure.
- [ ] Verify the supplier test server reproduces success, retry, final failure, duplicate/idempotency, and lease recovery.
- [ ] Verify logs and query responses contain no credentials or complete bodies.
- [ ] Verify README commands, `.env.example`, Makefile targets, migration names, and actual HTTP routes agree.
- [ ] Verify the repository name requirement `rc_{your_nickname}` and add the truthful AI usage file before submission.


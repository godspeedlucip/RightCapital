# API Notification Service MVP — Python Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Implement the notification-service MVP in one Python stack, with a FastAPI API, durable database tasks, an asynchronous Worker, at-least-once delivery, retries, lease recovery, tests, and assignment-ready documentation.

**Architecture:** FastAPI receives authenticated requests and persists them before returning `202`. A Worker polls the same database, claims tasks with a lease, calls suppliers through `httpx`, and conditionally writes delivery outcomes. SQLAlchemy provides a database abstraction; SQLite is the default local/test database and PostgreSQL is supported through configuration and Docker Compose.

**Tech Stack:** Python 3.12+; FastAPI; Uvicorn; Pydantic; SQLAlchemy 2; httpx; pytest; pytest-asyncio; SQLite for local tests; PostgreSQL for the production-like Compose path.

**Spec:** `docs/superpowers/specs/2026-10-14-api-notification-service-design.md`

## Global Constraints

- Return `202 Accepted` only after durable persistence; database failures return `5xx` without a successful task ID.
- Delivery is at-least-once; duplicate supplier requests are possible and must be documented.
- Retry defaults are `MAX_ATTEMPTS=5`, `RETRY_DELAY=10s`, `REQUEST_TIMEOUT=10s`, `POLL_INTERVAL=1s`, and `LEASE_DURATION=30s`.
- Only `http` and `https` targets are accepted; configured host allowlists must be enforced when present.
- Inject `Idempotency-Key` and `X-Notification-ID`; reject caller attempts to override them.
- HTTP `2xx` succeeds; network errors/timeouts and `408`, `425`, `429`, `500`, `502`, `503`, `504` retry; specified `4xx` and security failures are terminal.
- Do not log credentials, sensitive headers, complete bodies, or supplier response bodies.
- Integration tests use a local `httpx`/ASGI or local HTTP supplier and no real supplier account.

## Review Focus

- Conditional claim prevents two Workers from delivering the same task concurrently; test in Task 2.
- Same `(provider, idempotency_key)` with different content returns `409` and preserves the original; test in Task 3.
- A timeout after the supplier may have received the request remains retryable and may duplicate; test in Task 4.
- An expired `DELIVERING` lease becomes reclaimable, while an active lease cannot be overwritten; test in Task 4.
- Redaction removes Authorization/Cookie/API-key values and full bodies from logs/status responses; test in Task 5.

### Task 1: Python Project and Configuration

**Files:** Create `pyproject.toml`, `.env.example`, `docker-compose.yml`, `Makefile`, `app/__init__.py`, `app/config.py`, `tests/test_config.py`.

- [ ] Write tests for defaults, missing required values, invalid durations, and `LEASE_DURATION > REQUEST_TIMEOUT`.
- [ ] Run `pytest tests/test_config.py -q`; verify failure because configuration is absent.
- [ ] Implement typed `Settings` and `load_settings()` using environment variables and exact spec defaults.
- [ ] Add `make test`, `make run-api`, `make run-worker`, and `make migrate` commands.
- [ ] Run `pytest -q`; expected result: configuration tests pass and the package imports cleanly.

### Task 2: Domain Model, Schema, Repository, and Idempotency

**Files:** Create `app/domain.py`, `app/db.py`, `app/repository.py`, `app/models.py`, `migrations/001_create_notifications.sql`, `tests/test_repository.py`.

- [ ] Write repository tests for create/get, idempotency reuse/conflict, atomic claim, conditional state writes, and expired lease recovery.
- [ ] Run the repository tests and observe the expected missing-implementation failures.
- [ ] Implement SQLAlchemy models and migration-compatible constraints/indexes for the five statuses and required timestamps.
- [ ] Implement `NotificationRepository.create/get/claim_next/recover_expired_leases/mark_delivered/mark_retry/mark_failed` with conditional updates.
- [ ] Run repository tests on SQLite; expected result: all persistence and race-condition tests pass.

### Task 3: FastAPI API, Auth, Validation, and Status

**Files:** Create `app/api.py`, `app/schemas.py`, `tests/test_api.py`.

- [ ] Write tests for `202`, malformed JSON (`400`), auth (`401/403`), policy failure (`422`), missing task (`404`), idempotency conflict (`409`), size limits, and header override rejection.
- [ ] Run `pytest tests/test_api.py -q`; observe failures before implementation.
- [ ] Implement `POST /v1/notifications` and `GET /v1/notifications/{notification_id}` with bearer-token auth and UTC RFC 3339 responses.
- [ ] Ensure status responses omit sensitive headers/body and creation returns only after commit.
- [ ] Run API tests and the full unit suite.

### Task 4: Delivery Client, Retry Policy, Worker, and Lease Recovery

**Files:** Create `app/delivery.py`, `app/worker.py`, `tests/test_delivery.py`, `tests/test_worker.py`.

- [ ] Write tests for system header injection, redirect behavior, success/retry/terminal classification, fixed 10-second retry scheduling, `[503, 503, 200]`, `400`, timeout uncertainty, and lease recovery.
- [ ] Run focused tests and observe expected failures.
- [ ] Implement `DeliveryClient` with `httpx.AsyncClient`, total timeout, no redirect following, no response-body persistence, and explicit classification.
- [ ] Implement `Worker.run_once()` and `Worker.run_forever()` with lease recovery, conditional claim, graceful cancellation, and state writes.
- [ ] Run delivery/worker tests and the full suite.

### Task 5: Logging, Metrics, and Safe Redaction

**Files:** Create `app/observability.py`, `tests/test_observability.py`; modify API and Worker modules.

- [ ] Write redaction tests for Authorization, Cookie, X-API-Key, complete bodies, and response bodies.
- [ ] Implement structured JSON logging and minimal counters for created/delivered/failed/pending tasks.
- [ ] Integrate logs at state changes without changing delivery behavior.
- [ ] Run observability tests and the full suite.

### Task 6: Integration Acceptance Matrix and Runtime Wiring

**Files:** Create `tests/integration/test_notification_flow.py`, `tests/integration/conftest.py`; modify `app/main.py`, `app/worker_main.py`, `docker-compose.yml`, `Makefile`.

- [ ] Write tests for create/PENDING, idempotency, `200`, `503/503/200`, `400`, lease recovery, database failure, and URL allowlist rejection using a local supplier.
- [ ] Run the integration tests against SQLite first, then PostgreSQL when Docker is available.
- [ ] Wire API startup and Worker startup without introducing a queue or external scheduler.
- [ ] Run `make test`; expected result: complete unit and integration suite passes without external accounts.

### Task 7: Assignment Documentation and Final Verification

**Files:** Modify `README.md`; create `docs/ai-usage.md`, `scripts/check-docs.py`.

- [ ] Implement a documentation check for required README commands/headings and the three truthful AI-usage sections.
- [ ] Rewrite README with problem understanding, architecture, boundaries, at-least-once semantics, trade-offs, environment setup, migration, API examples, tests, and known limitations.
- [ ] Fill `docs/ai-usage.md` from the actual implementation process; do not invent rejected suggestions.
- [ ] Run `python scripts/check-docs.py`, `python -m compileall app tests`, and `make test`.
- [ ] Verify `.env.example`, Makefile targets, routes, migrations, and README commands agree.

## Final Verification

- [ ] `python -m compileall app tests` succeeds.
- [ ] `pytest -q` or `make test` succeeds with zero failures.
- [ ] The local supplier reproduces success, retry, final failure, duplicate/idempotency, and lease recovery.
- [ ] Logs and status responses contain no credentials or complete payloads.
- [ ] The final repository includes a runnable MVP, project README, truthful AI usage notes, and repository name `rc_{your_nickname}`.

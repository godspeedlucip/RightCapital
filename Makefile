.PHONY: test run-api run-worker migrate

test:
	python -m pytest -q

run-api:
	uvicorn app.main:app --host 127.0.0.1 --port 8000

run-worker:
	python -m app.worker_main

migrate:
	python -m app.db

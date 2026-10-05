# All database writes are guarded; real-data migration saves a local backup.
PYTHON := backend/.venv/bin/python
BACKEND := backend
.PHONY: dev-up migrate seed seed-synthetic dev worker test check-slice dev-down build-ui generate-client migrate-test

dev-up:
	@echo "Local PG required; no shared service is modified or reset."
migrate:
	$(PYTHON) tools/local_manage.py migrate
migrate-test:
	$(PYTHON) tools/local_manage.py migrate-test
seed seed-synthetic:
	cd $(BACKEND) && .venv/bin/python scripts_seed.py
dev:
	$(PYTHON) tools/local_manage.py start
worker:
	cd $(BACKEND) && .venv/bin/python -m app.worker --once
test check-slice:
	cd $(BACKEND) && .venv/bin/python -m pytest tests/ -q
dev-down:
	$(PYTHON) tools/local_manage.py stop
build-ui:
	npm --prefix frontend run build
generate-client:
	$(PYTHON) tools/export_openapi.py
	npm --prefix frontend run generate

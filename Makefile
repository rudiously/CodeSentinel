.PHONY: setup test lint up down train-smoke demo
PYTHON ?= python3.11
VENV ?= .venv/bin
PYTHON_ONLY ?= 0
setup:
	$(PYTHON) -m venv .venv
	if [ "$$(uname -s)" = Linux ]; then $(VENV)/pip install torch==2.7.1 --index-url https://download.pytorch.org/whl/cpu; fi
	$(VENV)/pip install -r requirements-dev.txt -r backend/requirements.txt -r model_service/requirements.txt -r ml/requirements.txt
	if [ "$(PYTHON_ONLY)" != 1 ]; then npm --prefix frontend install --ignore-scripts; fi
test:
	$(VENV)/pytest -q
	if [ "$(PYTHON_ONLY)" = 1 ]; then echo "Frontend tests explicitly skipped; full gate not verified"; else npm --prefix frontend test; fi
lint:
	$(VENV)/ruff check ml backend model_service shared action scripts examples/seed_demo_data.py
	$(VENV)/black --check ml backend model_service shared action scripts examples/seed_demo_data.py
	$(VENV)/mypy ml backend model_service shared action scripts examples/seed_demo_data.py
	if [ "$(PYTHON_ONLY)" = 1 ]; then echo "Frontend lint explicitly skipped; full gate not verified"; else npm --prefix frontend run lint; fi
up:
	docker compose -f deploy/docker-compose.yml up -d --build
down:
	docker compose -f deploy/docker-compose.yml down
train-smoke:
	$(VENV)/python -m ml.train --config ml/configs/train_smoke.yaml
demo:
	bash scripts/e2e_demo.sh

.PHONY: init up down test lint demo fault-demo
init:
	python tools/bootstrap.py
up: init
	docker compose up -d --build --force-recreate
	@echo "Topology: http://127.0.0.1:8000 | Grafana: http://127.0.0.1:3000"
down:
	docker compose down
test:
	python -m pytest -q
lint:
	python -m ruff check .
	python -m ruff format --check .
demo:
	@echo "Open http://127.0.0.1:8000 and read docs/demo.md"
	python -m signalatlas.diagnostics --url http://127.0.0.1:8000/api/topology
fault-demo:
	python tools/fault_demo.py

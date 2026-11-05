SHELL := /bin/bash

.PHONY: build up down download init optimize analytics benchmark validate

build:
	docker compose build

up:
	docker compose up -d postgres airflow superset-init superset superset-bootstrap

down:
	docker compose down

download:
	@test -n "$(START)" -a -n "$(END)" || (echo "Use: make download START=2025-01 END=2026-08"; exit 1)
	docker compose --profile tools run --rm downloader --start "$(START)" --end "$(END)"

init:
	docker compose --profile tools run --rm warehouse-init

optimize:
	docker compose --profile tools run --rm warehouse-optimize

analytics:
	./scripts/run_analytics.sh

benchmark:
	./scripts/benchmark_optimizations.sh

validate:
	docker compose config --quiet
	python3 -c "from pathlib import Path; compile(Path('scripts/download_tlc_data.py').read_text(), 'download_tlc_data.py', 'exec')"
	bash -n scripts/*.sh etl/*.sh

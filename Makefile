.PHONY: lint format check test install

install:
	pip install -e ".[dev]"

lint:
	ruff check ninja_service_objects

format:
	ruff format ninja_service_objects
	ruff check --fix ninja_service_objects

check:
	ruff format --check ninja_service_objects
	ruff check ninja_service_objects
	mypy ninja_service_objects

test:
	pytest

.PHONY: install up down test smoke api headed lint format

install:            ## Install the suite and the Chromium browser
	pip install -e ".[dev]"
	python -m playwright install chromium

up:                 ## Start a disposable Rocket.Chat + MongoDB and wait until healthy
	docker compose up -d --wait

down:               ## Stop it and delete its data
	docker compose down -v

test:               ## Full suite, in parallel
	pytest -n auto

smoke:              ## Critical-path checks only
	pytest -n auto -m smoke

api:                ## REST checks only (no browser)
	pytest -m api

headed:             ## Watch the browser, one test at a time
	pytest --headed --slowmo 250 -n 0

lint:
	ruff check .
	ruff format --check .

format:
	ruff check --fix .
	ruff format .

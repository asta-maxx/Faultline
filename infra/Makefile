# Faultline infrastructure and developer Makefile

COMPOSE_FILE = infra/docker-compose.yml
PYTHON = python

.PHONY: up down seed reset test dump build

up:
	docker compose -f $(COMPOSE_FILE) up -d

down:
	docker compose -f $(COMPOSE_FILE) down

build:
	docker compose -f $(COMPOSE_FILE) build

seed:
	$(PYTHON) -m data.seed --tenant northwind

reset:
	$(PYTHON) -m data.seed --reset --tenant northwind

test:
	pytest -v

dump:
	bash infra/scripts/dump_graph.sh

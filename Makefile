.PHONY: db-up db-down db-reset db-logs db-shell db-psql

COMPOSE := docker compose -f infra/docker/docker-compose.yml --env-file .env

db-up:
	$(COMPOSE) up -d postgres
	@echo "Waiting for postgres to be healthy..."
	@until $(COMPOSE) ps postgres | grep -q "(healthy)"; do sleep 1; done
	@echo "Postgres ready on localhost:5433"

db-down:
	$(COMPOSE) down

db-reset:
	$(COMPOSE) down -v
	$(MAKE) db-up

db-logs:
	$(COMPOSE) logs -f postgres

db-shell:
	docker exec -it keystone-postgres bash

db-psql:
	docker exec -it keystone-postgres psql -U keystone -d keystone
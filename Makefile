.PHONY: help up down logs test lint seed migrate clean build

# Default target
help:
	@echo "PdM Platform Development Commands"
	@echo "================================="
	@echo "up         - Start all services in development mode"
	@echo "down       - Stop all services and remove containers"
	@echo "logs       - Follow logs from all services"
	@echo "test       - Run all tests"
	@echo "lint       - Run linting and formatting"
	@echo "seed       - Seed database with demo data"
	@echo "migrate    - Run database migrations"
	@echo "clean      - Clean up volumes and images"
	@echo "build      - Build all images"
	@echo "backend-shell - Open shell in backend container"
	@echo "db-shell   - Open psql shell"

up:
	@echo "Starting PdM Platform services..."
	docker-compose up -d postgres redis minio nats
	@echo "Waiting for services to be ready..."
	sleep 10
	docker-compose up -d backend ml-service frontend pgadmin mailhog
	@echo "Services started! Access:"
	@echo "  Frontend: http://localhost:3000"
	@echo "  Backend API: http://localhost:8000"
	@echo "  API Docs: http://localhost:8000/docs"
	@echo "  ML Service: http://localhost:8001"
	@echo "  PgAdmin: http://localhost:5050"
	@echo "  MailHog: http://localhost:8025"
	@echo "  MinIO Console: http://localhost:9001"

down:
	@echo "Stopping all services..."
	docker-compose down

logs:
	docker-compose logs -f

logs-backend:
	docker-compose logs -f backend

logs-frontend:
	docker-compose logs -f frontend

logs-ml:
	docker-compose logs -f ml-service

test:
	@echo "Running backend tests..."
	docker-compose exec backend pytest tests/ -v
	@echo "Running frontend tests..."
	docker-compose exec frontend npm test

lint:
	@echo "Running backend linting..."
	docker-compose exec backend ruff check . --fix
	docker-compose exec backend black . --check
	docker-compose exec backend mypy .
	@echo "Running frontend linting..."
	docker-compose exec frontend npm run lint
	docker-compose exec frontend npm run type-check

seed:
	@echo "Seeding database with demo data..."
	docker-compose exec backend python -m app.seed

migrate:
	@echo "Running database migrations..."
	docker-compose exec backend alembic upgrade head

reset-db:
	@echo "Resetting database..."
	docker-compose exec backend alembic downgrade base
	docker-compose exec backend alembic upgrade head
	$(MAKE) seed

backend-shell:
	docker-compose exec backend bash

db-shell:
	docker-compose exec postgres psql -U postgres -d pdm_platform

redis-shell:
	docker-compose exec redis redis-cli

clean:
	@echo "Cleaning up containers, networks, and volumes..."
	docker-compose down -v
	docker system prune -f

build:
	@echo "Building all images..."
	docker-compose build --no-cache

restart:
	$(MAKE) down
	$(MAKE) up

# Development helpers
dev-backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && npm run dev

dev-ml:
	cd ml && uvicorn service.main:app --reload --host 0.0.0.0 --port 8001

# Load testing
load-test:
	@echo "Running load tests..."
	docker run --rm -i grafana/k6 run - < tools/load_test.js

# Security scanning
security-scan:
	@echo "Running security scan..."
	docker run --rm -v $(pwd):/src securecodewarrior/docker-security-scanning

# Generate API client
generate-client:
	@echo "Generating TypeScript API client..."
	docker-compose exec backend python -m app.generate_client

# Backup database
backup-db:
	@echo "Creating database backup..."
	docker-compose exec postgres pg_dump -U postgres pdm_platform > backup_$(shell date +%Y%m%d_%H%M%S).sql

# Monitor services
monitor:
	@echo "Service status:"
	@docker-compose ps
	@echo "\nHealth checks:"
	@docker-compose exec postgres pg_isready -U postgres
	@docker-compose exec redis redis-cli ping
	@docker-compose exec backend curl -f http://localhost:8000/health || echo "Backend not ready"

# Documentation
docs:
	@echo "Building documentation..."
	cd backend && python -m mkdocs build
	cd frontend && npm run build-docs

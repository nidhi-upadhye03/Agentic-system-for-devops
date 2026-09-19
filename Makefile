.PHONY: help install build test lint format clean deploy start stop restart logs ps health

# Variables
DOCKER_COMPOSE := docker-compose
DOCKER := docker
KUBECTL := kubectl
PYTHON := python3
PIP := pip3
NPM := npm
NODE := node

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m # No Color

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "$(BLUE)DevOps Platform - Makefile Commands$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

# Installation targets
install: install-python install-node ## Install all dependencies
	@echo "$(GREEN)All dependencies installed successfully$(NC)"

install-python: ## Install Python dependencies for all services
	@echo "$(BLUE)Installing Python dependencies...$(NC)"
	cd services/llm-service && $(PIP) install -r requirements.txt
	cd services/worker && $(PIP) install -r requirements.txt
	@echo "$(GREEN)Python dependencies installed$(NC)"

install-node: ## Install Node.js dependencies for all services
	@echo "$(BLUE)Installing Node.js dependencies...$(NC)"
	cd services/approval-backend && $(NPM) install
	cd services/approval-frontend && $(NPM) install
	@echo "$(GREEN)Node.js dependencies installed$(NC)"

install-dev: ## Install development dependencies
	@echo "$(BLUE)Installing development dependencies...$(NC)"
	$(PIP) install pytest pytest-cov black flake8 mypy pylint
	$(NPM) install -g eslint prettier jest
	@echo "$(GREEN)Development dependencies installed$(NC)"

# Build targets
build: ## Build all Docker images
	@echo "$(BLUE)Building all Docker images...$(NC)"
	$(DOCKER_COMPOSE) build
	@echo "$(GREEN)All images built successfully$(NC)"

build-llm: ## Build LLM service image
	@echo "$(BLUE)Building LLM service...$(NC)"
	$(DOCKER_COMPOSE) build llm-service

build-worker: ## Build Worker service image
	@echo "$(BLUE)Building Worker service...$(NC)"
	$(DOCKER_COMPOSE) build worker

build-backend: ## Build Approval backend image
	@echo "$(BLUE)Building Approval backend...$(NC)"
	$(DOCKER_COMPOSE) build approval-backend

build-frontend: ## Build Approval frontend image
	@echo "$(BLUE)Building Approval frontend...$(NC)"
	$(DOCKER_COMPOSE) build approval-frontend

build-no-cache: ## Build all images without cache
	@echo "$(BLUE)Building all images without cache...$(NC)"
	$(DOCKER_COMPOSE) build --no-cache

# Docker Compose management
start: ## Start all services
	@echo "$(BLUE)Starting all services...$(NC)"
	$(DOCKER_COMPOSE) up -d
	@echo "$(GREEN)All services started$(NC)"
	@make ps

stop: ## Stop all services
	@echo "$(BLUE)Stopping all services...$(NC)"
	$(DOCKER_COMPOSE) stop
	@echo "$(GREEN)All services stopped$(NC)"

restart: ## Restart all services
	@echo "$(BLUE)Restarting all services...$(NC)"
	$(DOCKER_COMPOSE) restart
	@echo "$(GREEN)All services restarted$(NC)"

down: ## Stop and remove all containers, networks, and volumes
	@echo "$(YELLOW)Stopping and removing all containers...$(NC)"
	$(DOCKER_COMPOSE) down -v
	@echo "$(GREEN)All containers removed$(NC)"

up: ## Start services in foreground
	@echo "$(BLUE)Starting services in foreground...$(NC)"
	$(DOCKER_COMPOSE) up

ps: ## Show running containers
	@$(DOCKER_COMPOSE) ps

logs: ## Show logs for all services
	$(DOCKER_COMPOSE) logs -f

logs-llm: ## Show LLM service logs
	$(DOCKER_COMPOSE) logs -f llm-service

logs-worker: ## Show Worker service logs
	$(DOCKER_COMPOSE) logs -f worker

logs-backend: ## Show Approval backend logs
	$(DOCKER_COMPOSE) logs -f approval-backend

logs-frontend: ## Show Approval frontend logs
	$(DOCKER_COMPOSE) logs -f approval-frontend

logs-postgres: ## Show PostgreSQL logs
	$(DOCKER_COMPOSE) logs -f postgres

logs-rabbitmq: ## Show RabbitMQ logs
	$(DOCKER_COMPOSE) logs -f rabbitmq

# Health checks
health: ## Check health of all services
	@echo "$(BLUE)Checking service health...$(NC)"
	@curl -f http://localhost:8000/health || echo "$(RED)LLM Service: DOWN$(NC)"
	@curl -f http://localhost:3000/health || echo "$(RED)Approval Backend: DOWN$(NC)"
	@curl -f http://localhost:3001 || echo "$(RED)Approval Frontend: DOWN$(NC)"
	@echo "$(GREEN)Health check complete$(NC)"

# Testing targets
test: test-python test-node ## Run all tests
	@echo "$(GREEN)All tests completed$(NC)"

test-python: ## Run Python tests
	@echo "$(BLUE)Running Python tests...$(NC)"
	cd services/llm-service && $(PYTHON) -m pytest tests/ -v --cov
	cd services/worker && $(PYTHON) -m pytest tests/ -v --cov

test-node: ## Run Node.js tests
	@echo "$(BLUE)Running Node.js tests...$(NC)"
	cd services/approval-backend && $(NPM) test
	cd services/approval-frontend && $(NPM) test

test-integration: ## Run integration tests
	@echo "$(BLUE)Running integration tests...$(NC)"
	$(PYTHON) -m pytest tests/integration/ -v

test-e2e: ## Run end-to-end tests
	@echo "$(BLUE)Running E2E tests...$(NC)"
	cd services/approval-frontend && $(NPM) run test:e2e

test-coverage: ## Generate test coverage report
	@echo "$(BLUE)Generating coverage report...$(NC)"
	cd services/llm-service && $(PYTHON) -m pytest --cov --cov-report=html
	cd services/worker && $(PYTHON) -m pytest --cov --cov-report=html
	cd services/approval-backend && $(NPM) run test:coverage

# Linting and formatting
lint: lint-python lint-node ## Run all linters
	@echo "$(GREEN)Linting complete$(NC)"

lint-python: ## Lint Python code
	@echo "$(BLUE)Linting Python code...$(NC)"
	cd services/llm-service && flake8 src/
	cd services/worker && flake8 src/
	cd services/llm-service && pylint src/
	cd services/worker && pylint src/
	cd services/llm-service && mypy src/
	cd services/worker && mypy src/

lint-node: ## Lint Node.js code
	@echo "$(BLUE)Linting Node.js code...$(NC)"
	cd services/approval-backend && $(NPM) run lint
	cd services/approval-frontend && $(NPM) run lint

format: format-python format-node ## Format all code
	@echo "$(GREEN)Code formatting complete$(NC)"

format-python: ## Format Python code with Black
	@echo "$(BLUE)Formatting Python code...$(NC)"
	cd services/llm-service && black src/
	cd services/worker && black src/

format-node: ## Format Node.js code with Prettier
	@echo "$(BLUE)Formatting Node.js code...$(NC)"
	cd services/approval-backend && $(NPM) run format
	cd services/approval-frontend && $(NPM) run format

# Database management
db-migrate: ## Run database migrations
	@echo "$(BLUE)Running database migrations...$(NC)"
	$(DOCKER_COMPOSE) exec approval-backend npm run migrate

db-seed: ## Seed database with sample data
	@echo "$(BLUE)Seeding database...$(NC)"
	$(DOCKER_COMPOSE) exec approval-backend npm run seed

db-reset: ## Reset database (drop and recreate)
	@echo "$(YELLOW)Resetting database...$(NC)"
	$(DOCKER_COMPOSE) exec postgres psql -U devops -d devops_db -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
	@make db-migrate
	@echo "$(GREEN)Database reset complete$(NC)"

db-backup: ## Backup database
	@echo "$(BLUE)Backing up database...$(NC)"
	$(DOCKER_COMPOSE) exec -T postgres pg_dump -U devops devops_db > backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)Database backup created$(NC)"

db-restore: ## Restore database from backup (Usage: make db-restore FILE=backup.sql)
	@echo "$(BLUE)Restoring database from $(FILE)...$(NC)"
	$(DOCKER_COMPOSE) exec -T postgres psql -U devops devops_db < $(FILE)
	@echo "$(GREEN)Database restored$(NC)"

# Kubernetes deployment
k8s-deploy: ## Deploy to Kubernetes
	@echo "$(BLUE)Deploying to Kubernetes...$(NC)"
	$(KUBECTL) apply -f k8s/namespace.yaml
	$(KUBECTL) apply -f k8s/configmap.yaml
	$(KUBECTL) apply -f k8s/secrets.yaml
	$(KUBECTL) apply -f k8s/postgres/
	$(KUBECTL) apply -f k8s/redis/
	$(KUBECTL) apply -f k8s/rabbitmq/
	$(KUBECTL) apply -f k8s/qdrant/
	$(KUBECTL) apply -f k8s/services/
	$(KUBECTL) apply -f k8s/ingress.yaml
	@echo "$(GREEN)Kubernetes deployment complete$(NC)"

k8s-delete: ## Delete Kubernetes deployment
	@echo "$(YELLOW)Deleting Kubernetes resources...$(NC)"
	$(KUBECTL) delete -f k8s/ --recursive
	@echo "$(GREEN)Kubernetes resources deleted$(NC)"

k8s-status: ## Show Kubernetes deployment status
	@echo "$(BLUE)Kubernetes deployment status:$(NC)"
	$(KUBECTL) get all -n devops

k8s-logs: ## Show Kubernetes pod logs (Usage: make k8s-logs POD=pod-name)
	$(KUBECTL) logs -f $(POD) -n devops

# Monitoring
monitor: ## Open monitoring dashboards
	@echo "$(BLUE)Opening monitoring dashboards...$(NC)"
	@echo "Prometheus: http://localhost:9090"
	@echo "Grafana: http://localhost:3002 (admin/admin)"
	@echo "RabbitMQ: http://localhost:15672 (devops/devops123)"

# Cleaning targets
clean: ## Clean all build artifacts and caches
	@echo "$(BLUE)Cleaning build artifacts...$(NC)"
	@make clean-python
	@make clean-node
	@make clean-docker
	@echo "$(GREEN)Cleanup complete$(NC)"

clean-python: ## Clean Python artifacts
	@echo "$(BLUE)Cleaning Python artifacts...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true

clean-node: ## Clean Node.js artifacts
	@echo "$(BLUE)Cleaning Node.js artifacts...$(NC)"
	find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".next" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "build" -exec rm -rf {} + 2>/dev/null || true

clean-docker: ## Clean Docker resources
	@echo "$(BLUE)Cleaning Docker resources...$(NC)"
	$(DOCKER) system prune -f
	$(DOCKER) volume prune -f

clean-all: down clean ## Stop services and clean everything
	@echo "$(GREEN)Complete cleanup finished$(NC)"

# Development helpers
dev-llm: ## Run LLM service in development mode
	cd services/llm-service && $(PYTHON) -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

dev-worker: ## Run Worker service in development mode
	cd services/worker && $(PYTHON) -m src.main

dev-backend: ## Run Approval backend in development mode
	cd services/approval-backend && $(NPM) run dev

dev-frontend: ## Run Approval frontend in development mode
	cd services/approval-frontend && $(NPM) run dev

shell-llm: ## Open shell in LLM service container
	$(DOCKER_COMPOSE) exec llm-service /bin/bash

shell-worker: ## Open shell in Worker container
	$(DOCKER_COMPOSE) exec worker /bin/bash

shell-backend: ## Open shell in Approval backend container
	$(DOCKER_COMPOSE) exec approval-backend /bin/sh

shell-postgres: ## Open PostgreSQL shell
	$(DOCKER_COMPOSE) exec postgres psql -U devops -d devops_db

shell-redis: ## Open Redis CLI
	$(DOCKER_COMPOSE) exec redis redis-cli -a devops123

# CI/CD targets
ci: install lint test ## Run CI pipeline locally
	@echo "$(GREEN)CI pipeline completed successfully$(NC)"

cd-staging: ## Deploy to staging environment
	@echo "$(BLUE)Deploying to staging...$(NC)"
	./ci-cd/scripts/deploy.sh staging

cd-production: ## Deploy to production environment
	@echo "$(YELLOW)Deploying to production...$(NC)"
	./ci-cd/scripts/deploy.sh production

# Documentation
docs: ## Generate documentation
	@echo "$(BLUE)Generating documentation...$(NC)"
	cd docs && $(MAKE) html
	@echo "$(GREEN)Documentation generated$(NC)"

docs-serve: ## Serve documentation locally
	cd docs/_build/html && $(PYTHON) -m http.server 8080

# Version management
version: ## Show current version
	@cat VERSION 2>/dev/null || echo "Version file not found"

bump-patch: ## Bump patch version
	@echo "$(BLUE)Bumping patch version...$(NC)"
	./ci-cd/scripts/bump-version.sh patch

bump-minor: ## Bump minor version
	@echo "$(BLUE)Bumping minor version...$(NC)"
	./ci-cd/scripts/bump-version.sh minor

bump-major: ## Bump major version
	@echo "$(BLUE)Bumping major version...$(NC)"
	./ci-cd/scripts/bump-version.sh major

# Security
security-scan: ## Run security vulnerability scan
	@echo "$(BLUE)Running security scan...$(NC)"
	cd services/llm-service && $(PIP) install safety && safety check
	cd services/worker && safety check
	cd services/approval-backend && $(NPM) audit
	cd services/approval-frontend && $(NPM) audit

# Performance
perf-test: ## Run performance tests
	@echo "$(BLUE)Running performance tests...$(NC)"
	cd tests/performance && $(PYTHON) -m locust -f locustfile.py

# Environment management
env-copy: ## Copy .env.example to .env
	@echo "$(BLUE)Copying environment template...$(NC)"
	cp .env.example .env
	@echo "$(GREEN).env file created. Please update with your values.$(NC)"

env-validate: ## Validate environment variables
	@echo "$(BLUE)Validating environment variables...$(NC)"
	@test -f .env || (echo "$(RED).env file not found$(NC)" && exit 1)
	@echo "$(GREEN)Environment variables validated$(NC)"

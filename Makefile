# AeroRisk AI - Root Makefile

.PHONY: help build test lint clean docker-up docker-down seed-db bench-engine bench-ai

# Default target
help:
	@echo "AeroRisk AI - Available Commands"
	@echo "================================"
	@echo "  make build          - Build all services"
	@echo "  make test           - Run all tests"
	@echo "  make lint           - Run linters"
	@echo "  make clean          - Clean build artifacts"
	@echo "  make docker-up      - Start all Docker containers"
	@echo "  make docker-down    - Stop all Docker containers"
	@echo "  make seed-db        - Seed databases with initial data"
	@echo "  make bench-engine   - Run engine benchmarks"
	@echo "  make bench-ai       - Run AI pipeline benchmarks"
	@echo "  make dev            - Start development environment"

# Build all services
build: build-engine build-ai

build-engine:
	@echo "Building Go Engine..."
	cd engine && go build -o bin/gateway ./cmd/gateway
	cd engine && go build -o bin/engine ./cmd/engine
	cd engine && go build -o bin/admin ./cmd/admin

build-ai:
	@echo "Building AI Guardrail..."
	cd ai_guardrail && poetry install

# Run all tests
test: test-engine test-ai

test-engine:
	@echo "Running Go Engine tests..."
	cd engine && go test -race -coverprofile=coverage.out ./...

test-ai:
	@echo "Running AI Guardrail tests..."
	cd ai_guardrail && poetry run pytest tests/ -v --cov=aerorisk

# Run linters
lint: lint-engine lint-ai

lint-engine:
	@echo "Linting Go code..."
	cd engine && golangci-lint run

lint-ai:
	@echo "Linting Python code..."
	cd ai_guardrail && poetry run ruff check . && poetry run mypy .

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	rm -rf engine/bin
	rm -rf engine/coverage.out
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Docker commands
docker-up:
	@echo "Starting Docker containers..."
	docker-compose up -d

docker-down:
	@echo "Stopping Docker containers..."
	docker-compose down

docker-logs:
	docker-compose logs -f

# Database seeding
seed-db:
	@echo "Seeding databases..."
	cd data/scripts && python seed_qdrant.py
	cd data/scripts && python seed_postgres.py

# Benchmarks
bench-engine:
	@echo "Running Go Engine benchmarks..."
	cd engine && go test -bench=. -benchmem ./internal/...

bench-ai:
	@echo "Running AI Guardrail benchmarks..."
	cd ai_guardrail && poetry run pytest tests/load/locustfile.py --headless -u http://localhost:8000 -t 60s

# Development environment
dev:
	@echo "Starting development environment..."
	docker-compose -f docker-compose.dev.yml up

# Kubernetes deployment (requires kubectl and cluster)
k8s-deploy:
	@echo "Deploying to Kubernetes..."
	kubectl apply -f infra/k8s/namespace.yaml
	kubectl apply -f infra/k8s/

# Monitoring stack
monitoring-up:
	@echo "Starting monitoring stack..."
	docker-compose -f infra/monitoring/docker-compose.yml up -d

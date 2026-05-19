# Local Setup Runbook

## Prerequisites

- Docker 24.0+
- Docker Compose 2.20+
- Go 1.21+
- Python 3.11+
- Poetry 1.7+
- Make 4.0+
- Git

## Quick Start

### 1. Clone and Configure

```bash
cd /workspace
cp .env.example .env
```

Edit `.env` with your configuration:

```bash
# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=aerorisk_secret

# Kafka/Redpanda
KAFKA_BROKERS=localhost:9092

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=aerorisk
POSTGRES_PASSWORD=aerorisk_secret
POSTGRES_DB=aerorisk

# LLM (local)
LLM_MODEL_PATH=/models/mixtral-8x7b-instruct-v0.1
```

### 2. Start Infrastructure

```bash
# Start all services
make up

# Or start individual services
docker-compose -f docker-compose.dev.yml up redis kafka qdrant postgres
```

### 3. Seed Data

```bash
# Seed compliance rules into Qdrant
make seed-qdrant

# Seed PostgreSQL with initial schema
make seed-postgres

# Generate synthetic test data
make generate-synthetic
```

### 4. Build Services

```bash
# Build Go engine
make build-engine

# Build AI guardrail
make build-ai
```

### 5. Run Services

```bash
# Run in development mode
make dev

# Or run individually
# Terminal 1: Engine
cd engine && go run cmd/gateway/main.go

# Terminal 2: AI Guardrail
cd ai_guardrail && poetry run python aerorisk/main.py
```

### 6. Verify Setup

```bash
# Check service health
curl http://localhost:8080/health

# Check metrics
curl http://localhost:9090/metrics

# Test gRPC endpoint
grpcurl -plaintext localhost:50051 list
```

## Service Endpoints

| Service | Port | Protocol | URL |
|---------|------|----------|-----|
| Gateway | 50051 | gRPC | localhost:50051 |
| Gateway WS | 8081 | WebSocket | ws://localhost:8081/ws |
| Admin API | 8080 | HTTP | http://localhost:8080 |
| Prometheus | 9090 | HTTP | http://localhost:9090 |
| Grafana | 3000 | HTTP | http://localhost:3000 |
| Qdrant | 6333 | HTTP | http://localhost:6333 |
| Redis | 6379 | TCP | localhost:6379 |
| Kafka | 9092 | TCP | localhost:9092 |
| PostgreSQL | 5432 | TCP | localhost:5432 |

## Development Workflow

### Running Tests

```bash
# All tests
make test

# Go tests only
make test-go

# Python tests only
make test-python

# With coverage
make coverage
```

### Running Benchmarks

```bash
# Go benchmarks
make bench-go

# Python benchmarks
make bench-python

# Load tests
make load-test
```

### Code Quality

```bash
# Lint Go code
make lint-go

# Lint Python code
make lint-python

# Format code
make format
```

### Hot Reload

```bash
# Install air for Go hot reload
go install github.com/air-verse/air@latest

# Run with hot reload
make dev-hot
```

## Debugging

### Enable Debug Logging

Set in `.env`:

```bash
LOG_LEVEL=debug
OTEL_EXPORTER_CONSOLE_ENABLED=true
```

### Access Logs

```bash
# View all logs
docker-compose -f docker-compose.dev.yml logs -f

# View specific service
docker-compose -f docker-compose.dev.yml logs -f engine
docker-compose -f docker-compose.dev.yml logs -f ai-guardrail
```

### Connect to Databases

```bash
# Redis CLI
docker exec -it aerorisk-redis redis-cli -a aerorisk_secret

# PostgreSQL
docker exec -it aerorisk-postgres psql -U aerorisk -d aerorisk

# Qdrant Dashboard
open http://localhost:6333/dashboard
```

### Kafka Topics

```bash
# List topics
docker exec -it aerorisk-kafka kafka-topics --bootstrap-server localhost:9092 --list

# Consume messages
docker exec -it aerorisk-kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic aerorisk.orders \
  --from-beginning
```

## Common Issues

### Issue: Port already in use

```bash
# Find process using port
lsof -i :8080

# Kill process
kill -9 <PID>

# Or change port in .env
```

### Issue: Go module errors

```bash
cd engine
go clean -modcache
go mod tidy
go mod download
```

### Issue: Poetry lock errors

```bash
cd ai_guardrail
poetry cache clear pypi --all
poetry lock --no-update
poetry install
```

### Issue: Qdrant connection refused

```bash
# Check if Qdrant is running
docker ps | grep qdrant

# Restart Qdrant
docker-compose -f docker-compose.dev.yml restart qdrant

# Check logs
docker-compose -f docker-compose.dev.yml logs qdrant
```

### Issue: Kafka broker not available

```bash
# Wait for Kafka to initialize (can take 30-60 seconds)
docker-compose -f docker-compose.dev.yml logs -f kafka

# Restart Kafka
docker-compose -f docker-compose.dev.yml restart kafka
```

## Performance Tuning

### Go Engine

```bash
# Set GOMAXPROCS
export GOMAXPROCS=8

# Adjust ring buffer size in config
RING_BUFFER_SIZE=65536

# Tune GC
export GOGC=50
```

### Python AI Guardrail

```bash
# Increase async worker count
AI_WORKER_COUNT=8

# Adjust batch size
KAFKA_BATCH_SIZE=1000

# Tune LLM inference
LLM_BATCH_SIZE=4
```

### Database Tuning

```bash
# Redis maxmemory
redis-cli CONFIG SET maxmemory 2gb

# PostgreSQL shared_buffers
docker exec -it aerorisk-postgres psql -U aerorisk -c \
  "ALTER SYSTEM SET shared_buffers = '256MB';"
```

## Monitoring

### Grafana Dashboards

Access at http://localhost:3000

**Default credentials:**
- Username: `admin`
- Password: `admin`

**Imported Dashboards:**
- Engine Performance
- AI Guardrail Metrics
- System Health

### Key Metrics to Watch

**Engine:**
- `engine_order_latency_ns` - Order processing latency
- `engine_tps` - Transactions per second
- `engine_errors_total` - Error count

**AI Guardrail:**
- `agent_processing_latency_seconds` - Agent pipeline latency
- `anomalies_detected_total` - Anomaly count
- `risk_decisions_total` - Decision breakdown

**Infrastructure:**
- `redis_memory_used_bytes` - Redis memory
- `kafka_consumer_lag` - Consumer lag
- `qdrant_search_duration_seconds` - Vector search latency

### Setting Up Alerts

1. Navigate to Alerting → Alert Rules
2. Create new rule
3. Select metric
4. Set threshold
5. Configure notification channel

## Backup & Restore

### Backup Redis

```bash
docker exec aerorisk-redis redis-cli BGSAVE
docker cp aerorisk-redis:/data/dump.rdb ./backups/redis-dump-$(date +%Y%m%d).rdb
```

### Backup PostgreSQL

```bash
docker exec aerorisk-postgres pg_dump -U aerorisk aerorisk > \
  ./backups/postgres-backup-$(date +%Y%m%d).sql
```

### Restore Redis

```bash
docker cp ./backups/redis-dump.rdb aerorisk-redis:/data/dump.rdb
docker-compose -f docker-compose.dev.yml restart redis
```

### Restore PostgreSQL

```bash
cat ./backups/postgres-backup.sql | \
  docker exec -i aerorisk-postgres psql -U aerorisk -d aerorisk
```

## Next Steps

1. Review [System Design](../architecture/system_design.md)
2. Read [API Reference](../api/grpc_reference.md)
3. Study [Agent Designs](../agents/)
4. Run [Performance Tests](./performance_tuning.md)

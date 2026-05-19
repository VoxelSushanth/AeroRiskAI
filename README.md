# AeroRisk AI

Low-Latency Distributed Transaction Engine with Multi-Agent AI Risk Orchestration

## Overview

AeroRisk AI is a production-grade distributed financial transaction platform capable of:
- >100k TPS
- <1ms matching latency
- Async AI fraud/compliance orchestration
- Real-time circuit-breaker enforcement
- Full observability + auditability

## Architecture

### Fast Path (Go)
- Gateway Layer
- LMAX Disruptor Ring Buffer
- Matching Engine
- Ledger Engine
- Kafka/Redpanda Publisher
- Redis Circuit Breakers

### AI Path (Python)
- LangGraph Multi-Agent Pipeline
  - Agent 1 → Anomaly Detection
  - Agent 2 → RAG + Compliance Retrieval
  - Agent 3 → LLM Decision Orchestrator

### Data Stores
- Redis → account state + circuit breakers
- Qdrant → vector search + compliance retrieval
- PostgreSQL → incident reports
- S3/Parquet → audit logs

### Observability
- Prometheus
- Grafana
- OpenTelemetry

## Quick Start

```bash
# Start all services
docker-compose up -d

# Run tests
make test

# Run benchmarks
make bench
```

## Project Structure

```
aerorisk-ai/
├── engine/          # Go matching engine
├── ai_guardrail/    # Python AI pipeline
├── data/            # Seed data and scripts
├── infra/           # Docker, K8s, monitoring
└── docs/            # Documentation
```

## Performance Targets

- Matching Engine: >100k TPS, <1ms p99 latency
- AI Pipeline: <200ms latency
- Vector Search: <10ms retrieval

## License

MIT

# AeroRisk AI System Design

## Overview

AeroRisk AI is a production-grade distributed financial transaction platform designed for ultra-low latency processing with integrated AI-powered risk management.

## Architecture Principles

1. **Separation of Concerns**: Fast path (Go) vs AI path (Python)
2. **Zero Allocation on Hot Path**: Pre-allocated buffers, object pooling
3. **Lock-Free Design**: LMAX Disruptor pattern for concurrent access
4. **Async Everywhere**: Non-blocking I/O outside execution core
5. **Deterministic AI**: Reproducible decisions with full audit trail
6. **Fail-Open Execution**: Circuit breakers protect without blocking

## Core Components

### 1. Go Engine (Fast Path)

#### Gateway Layer
- gRPC server for order submission
- WebSocket server for real-time updates
- Authentication & rate limiting
- Request validation

#### LMAX Disruptor Ring Buffer
- Single-writer principle
- Cache-line padding to avoid false sharing
- Wait strategies: BusySpin, Yield, Blocking
- Batch processing for throughput

#### Matching Engine
- Price-time priority algorithm
- Red-black tree for order book levels
- O(log n) order insertion/cancellation
- Fixed-point arithmetic (int64)

#### Ledger Engine
- Double-entry bookkeeping
- Atomic settlement
- Balance validation
- Transaction journaling

#### Kafka Publisher
- Async event publishing
- Topic partitioning by symbol
- Exactly-once semantics

#### Redis Cache
- Account state caching
- Circuit breaker state
- Sub-millisecond access

### 2. Python AI Guardrail (AI Path)

#### Kafka Consumer
- Async batch consumption
- Event parsing & validation
- Backpressure handling

#### Agent 1: Anomaly Detection
- Velocity checks (orders/sec, volume)
- VWAP deviation monitoring
- Wash trade detection
- Spoofing detection (HMM-based)
- Embedding similarity search

#### Agent 2: RAG + Compliance
- Vector search in Qdrant
- Compliance rule retrieval
- News sentiment analysis
- User profile lookup
- Sanctions screening (OFAC)

#### Agent 3: Decision Orchestrator
- Local LLM inference
- Risk scoring (0.0 - 1.0)
- Decision: ALLOW/FLAG/BLOCK/ADJUST_LIMIT
- Incident report generation
- Redis circuit breaker updates

### 3. Data Stores

| Store | Purpose | Latency Target |
|-------|---------|----------------|
| Redis | Account state, circuit breakers | <1ms |
| Qdrant | Vector embeddings, compliance | <10ms |
| PostgreSQL | Incident reports, audit | <50ms |
| S3/Parquet | Historical audit logs | N/A |

### 4. Observability Stack

- **Prometheus**: Metrics collection
- **Grafana**: Dashboards & visualization
- **Jaeger**: Distributed tracing
- **OpenTelemetry**: Unified instrumentation

## Data Flow

### Happy Path (Low Risk)
```
Client → Gateway → Ring Buffer → Matching Engine → Ledger → Kafka → Client ACK
                                    ↓
                              (Async) AI Pipeline → Redis (no action)
```

### Flagged Transaction
```
Client → Gateway → Ring Buffer → Matching Engine → Ledger → Kafka → Client ACK
                                    ↓
                              AI Pipeline → Risk Score: 0.6
                                    ↓
                              Redis Circuit Breaker: FLAG
                                    ↓
                              Incident Report → PostgreSQL
```

### Blocked Transaction
```
Client → Gateway → Risk Check → BLOCKED
                    ↓
              Sanctions Match = True
                    ↓
              Incident Report → PostgreSQL
              Alert → Operations Team
```

## Performance Targets

| Component | Metric | Target |
|-----------|--------|--------|
| Matching Engine | Throughput | >100k TPS |
| Matching Engine | P99 Latency | <1ms |
| AI Pipeline | P95 Latency | <200ms |
| Vector Search | P95 Latency | <10ms |
| Redis Access | P99 Latency | <1ms |
| Kafka Publish | P99 Latency | <10ms |

## Scalability Strategy

1. **Horizontal Scaling**: Stateless engine pods
2. **Partitioning**: Order books by symbol
3. **Sharding**: Redis cluster for account state
4. **Replication**: Kafka topics with multiple partitions
5. **Auto-scaling**: HPA based on latency metrics

## Fault Tolerance

1. **Circuit Breakers**: Prevent cascade failures
2. **Retry Logic**: Exponential backoff with jitter
3. **Dead Letter Queues**: Failed event handling
4. **Health Checks**: Kubernetes liveness/readiness
5. **Graceful Shutdown**: Drain connections before termination

## Security

1. **Authentication**: JWT-based API access
2. **Authorization**: Role-based permissions
3. **Encryption**: TLS for all network traffic
4. **Audit Logging**: Immutable transaction records
5. **Sanctions Screening**: Real-time OFAC checks

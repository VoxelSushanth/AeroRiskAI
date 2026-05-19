# ADR-002: Redpanda over Apache Kafka

## Status
Accepted

## Context
The event streaming layer requires high throughput (>100k messages/sec), low latency (<10ms p99), and operational simplicity for a financial transaction platform.

## Decision
We will use Redpanda instead of Apache Kafka because:

### Advantages
- **No JVM**: Eliminates GC pauses, reduces memory footprint
- **C++ Implementation**: Sub-millisecond tail latencies
- **Kafka Protocol Compatible**: Drop-in replacement, existing tooling works
- **Simplified Operations**: No ZooKeeper dependency
- **Better Performance**: 10x throughput on same hardware

### Configuration
```yaml
# Redpanda tuning for low latency
redpanda:
  enable_idempotence: true
  transaction_coordinator_replication: 3
  default_topic_partitions: 12
  kafka_batch_max_bytes: 1048576
  
# Producer settings
producer:
  acks: all
  retries: 3
  retry_backoff_ms: 100
  linger_ms: 5
  batch_size: 32768
```

## Consequences

### Positive
- Reduced operational complexity
- Better latency characteristics
- Lower resource requirements
- Easier debugging (no JVM)

### Negative
- Smaller community than Kafka
- Fewer third-party integrations
- Less battle-tested at extreme scale

## Topics Structure
| Topic | Partitions | Retention | Purpose |
|-------|------------|-----------|---------|
| orders | 12 per symbol | 7 days | Order submissions |
| trades | 12 per symbol | 30 days | Executed trades |
| events | 24 | 7 days | System events |
| risk_decisions | 12 | 30 days | AI risk assessments |

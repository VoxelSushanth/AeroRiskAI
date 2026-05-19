# System Design Interview Answers

## Question 1: Design a High-Frequency Trading Platform

**Answer:**

### Requirements
- **Throughput**: >100k TPS
- **Latency**: <1ms p99 for order matching
- **Availability**: 99.99%
- **Consistency**: Strong consistency for ledger, eventual for analytics

### Architecture Overview

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Gateway   │────▶│  Disruptor   │────▶│  Matching   │
│   (gRPC)    │     │ Ring Buffer  │     │   Engine    │
└─────────────┘     └──────────────┘     └─────────────┘
                           │                    │
                           ▼                    ▼
                    ┌──────────────┐     ┌─────────────┐
                    │ Kafka/Redpanda│    │   Ledger    │
                    │   (Async)     │    │   Engine    │
                    └──────────────┘     └─────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ AI Guardrail │
                    │ (Fraud/Risk) │
                    └──────────────┘
```

### Key Design Decisions

1. **LMAX Disruptor Pattern**
   - Lock-free ring buffer for order ingestion
   - Eliminates lock contention on hot path
   - Cache-line padding to prevent false sharing
   - Achieves <100μs latency for order ingestion

2. **Separation of Concerns**
   - **Fast Path**: Gateway → Disruptor → Matching → Ledger (synchronous)
   - **Slow Path**: Kafka → AI Guardrail → Circuit Breakers (asynchronous)
   - AI never blocks order execution

3. **Data Stores**
   - **Redis**: Account state, circuit breakers (<1ms access)
   - **PostgreSQL**: Audit logs, incident reports (ACID compliance)
   - **Qdrant**: Vector search for fraud patterns (<10ms retrieval)
   - **Kafka**: Event streaming, decoupling

4. **Fixed-Point Arithmetic**
   - All monetary values as int64 (8 decimal places)
   - Avoids floating-point precision issues
   - Deterministic calculations across systems

5. **Circuit Breaker Pattern**
   - Automatic fail-open design
   - Redis-backed state for fast access
   - Prevents cascade failures

### Scaling Strategy

- **Horizontal**: Multiple gateway instances behind load balancer
- **Vertical**: Single matching engine instance (stateful, ordered processing)
- **Sharding**: By symbol if needed (AAPL on shard 1, GOOGL on shard 2)

### Trade-offs Discussed

| Decision | Benefit | Trade-off |
|----------|---------|-----------|
| Lock-free ring buffer | Low latency | Complex implementation |
| Async AI pipeline | No blocking | Eventual fraud detection |
| Fixed-point math | Deterministic | Less intuitive than decimals |
| Single matching engine | Simple ordering | Vertical scaling limit |

---

## Question 2: Design a Real-Time Fraud Detection System

**Answer:**

### Requirements
- **Latency**: <200ms for risk decision
- **Accuracy**: >95% true positive, <5% false positive
- **Scalability**: Handle 100k events/sec
- **Auditability**: Full audit trail for regulatory compliance

### Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Kafka     │────▶│   Agent 1    │────▶│   Agent 2   │
│   Events    │     │   Anomaly    │     │   RAG       │
└─────────────┘     └──────────────┘     └─────────────┘
                                              │
                                              ▼
                                       ┌─────────────┐
                                       │   Agent 3   │
                                       │  Decision   │
                                       └─────────────┘
                                              │
                   ┌──────────────────────────┼──────────────────────────┐
                   ▼                          ▼                          ▼
            ┌─────────────┐           ┌─────────────┐           ┌─────────────┐
            │   Redis     │           │ PostgreSQL  │           │   Qdrant    │
            │  Circuits   │           │  Reports    │           │  Vectors    │
            └─────────────┘           └─────────────┘           └─────────────┘
```

### Components

1. **Agent 1: Anomaly Detection**
   - Velocity checks (orders/sec, notional value)
   - VWAP deviation monitoring
   - Wash trade detection (graph analysis)
   - Spoofing detection (HMM models)
   - Embedding similarity search

2. **Agent 2: Contextual RAG**
   - Compliance rule retrieval (MiFID II, FINRA)
   - User profile lookup
   - Sanctions screening (OFAC, UN, EU lists)
   - News sentiment analysis
   - Circuit breaker status

3. **Agent 3: Decision Orchestrator**
   - Local LLM inference (Mixtral-8x7B)
   - Risk scoring (weighted factors)
   - Deterministic JSON output
   - Incident report generation

### Key Design Decisions

1. **Multi-Agent Pipeline**
   - Parallel execution where possible
   - LangGraph for state management
   - Each agent has single responsibility

2. **Mandatory Blocking Rules**
   - Sanctions match → ALWAYS BLOCK
   - Circuit breaker open → ALWAYS BLOCK
   - High-confidence fraud → ALWAYS BLOCK
   - Rule-based decisions bypass LLM for speed

3. **Vector Search Optimization**
   - HNSW indexing for fast similarity search
   - Scalar quantization (INT8) for memory efficiency
   - Cached embeddings for common queries

4. **Local LLM Inference**
   - Data privacy (no external API calls)
   - Low latency (<100ms with quantization)
   - Deterministic outputs (low temperature)

### Trade-offs

| Decision | Benefit | Trade-off |
|----------|---------|-----------|
| Multi-agent pipeline | Modularity, testability | Increased complexity |
| Local LLM | Privacy, latency | Hardware requirements |
| RAG architecture | Up-to-date context | Vector DB dependency |
| Mandatory rules | Fast decisions | Less nuanced |

---

## Question 3: How Do You Ensure Data Consistency in a Distributed System?

**Answer:**

### Consistency Model

AeroRisk uses **mixed consistency**:
- **Strong consistency**: Ledger, account balances (ACID)
- **Eventual consistency**: Analytics, fraud patterns, circuit breakers

### Implementation Strategies

1. **Single Writer Principle**
   - Matching engine is single-threaded per symbol
   - All orders for AAPL processed by same instance
   - Guarantees ordering without distributed locks

2. **Event Sourcing**
   - All state changes captured as immutable events
   - Ledger reconstructed from event stream
   - Audit trail built-in

3. **Two-Phase Commit (for critical operations)**
   ```go
   func SettleTrade(trade *Trade) error {
       // Phase 1: Prepare
       if err := ledger.PrepareDebit(trade.Buyer); err != nil {
           return err
       }
       if err := ledger.PrepareCredit(trade.Seller); err != nil {
           ledger.RollbackPrepare(trade.Buyer)
           return err
       }
       
       // Phase 2: Commit
       ledger.CommitDebit(trade.Buyer)
       ledger.CommitCredit(trade.Seller)
   }
   ```

4. **Idempotent Operations**
   - Every request has unique ID
   - Duplicate requests detected and ignored
   - Safe retry mechanism

5. **Saga Pattern (for cross-service transactions)**
   ```python
   async def process_order_saga(order):
       try:
           await validate_order(order)
           await check_risk(order)
           await match_order(order)
           await settle_trade(order)
       except Exception as e:
           await compensate(order, e)
   ```

### Reconciliation

- **Real-time**: Redis counters vs PostgreSQL ledger
- **Batch**: Daily reconciliation jobs
- **Alerting**: Automated alerts on mismatch > threshold

### Trade-offs

| Approach | Use Case | Trade-off |
|----------|----------|-----------|
| Strong consistency | Ledger | Higher latency |
| Eventual consistency | Circuit breakers | Temporary inconsistency |
| Event sourcing | Audit trail | Storage overhead |
| Saga pattern | Cross-service | Complexity |

---

## Question 4: How Would You Scale This System to 1 Million TPS?

**Answer:**

### Current Bottlenecks

1. **Matching Engine**: Single-threaded, ~100k TPS limit
2. **Network**: gRPC serialization overhead
3. **Database**: PostgreSQL write throughput
4. **AI Pipeline**: LLM inference latency

### Scaling Strategies

1. **Horizontal Sharding**
   ```
   Symbol → Hash → Shard
   AAPL → hash("AAPL") % 10 → Shard 3
   GOOGL → hash("GOOGL") % 10 → Shard 7
   ```
   - 10 shards = 1M TPS theoretical
   - Cross-shard trades require coordination

2. **Order Book Partitioning**
   - Separate books by price range
   - Retail orders (<100 shares) on separate book
   - Institutional orders on separate book

3. **Specialized Hardware**
   - FPGA for matching logic
   - RDMA networking for sub-microsecond latency
   - GPU for LLM inference batching

4. **Read/Write Separation**
   - Primary: Order matching, ledger writes
   - Replicas: Balance queries, analytics
   - Async replication with conflict resolution

5. **Caching Layers**
   - L1: In-memory account state (per instance)
   - L2: Redis cluster (shared state)
   - L3: Database (source of truth)

6. **AI Pipeline Optimization**
   - Batch LLM inference (32x throughput)
   - Model distillation (smaller, faster model)
   - Early exit rules (bypass LLM for clear cases)

### Architecture at Scale

```
┌─────────┐    ┌─────────┐    ┌─────────┐
│   LB    │───▶│Gateway 1│    │Gateway N│
└─────────┘    └─────────┘    └─────────┘
                    │              │
                    ▼              ▼
              ┌─────────────────────────┐
              │   Consistent Hash Ring  │
              └─────────────────────────┘
                    │              │
                    ▼              ▼
              ┌─────────┐    ┌─────────┐
              │Shard 1  │    │Shard 10 │
              │(100k)   │    │(100k)   │
              └─────────┘    └─────────┘
```

### Trade-offs at Scale

| Scaling Technique | Benefit | Cost |
|-------------------|---------|------|
| Sharding | Linear scale | Cross-shard complexity |
| FPGA | 10x throughput | Development cost |
| Batching | Better utilization | Increased latency |
| Caching | Faster reads | Consistency challenges |

---

## Question 5: How Do You Handle Failures in a Financial System?

**Answer:**

### Failure Modes

1. **Hardware Failure**: Server crash, network partition
2. **Software Bug**: Memory leak, deadlock
3. **Data Corruption**: Bit rot, bug-induced corruption
4. **External Dependency**: Redis down, Kafka unavailable

### Mitigation Strategies

1. **Redundancy**
   - Active-passive for matching engine
   - Multi-AZ deployment
   - Hot standby with state replication

2. **Circuit Breakers**
   ```go
   type CircuitBreaker struct {
       state      State  // CLOSED, OPEN, HALF_OPEN
       failureCnt int
       lastFail   time.Time
   }
   
   func (cb *CircuitBreaker) Execute(fn func() error) error {
       if cb.state == OPEN {
           if time.Since(cb.lastFail) > cb.timeout {
               cb.state = HALF_OPEN
           } else {
               return ErrCircuitOpen
           }
       }
       
       err := fn()
       if err != nil {
           cb.recordFailure()
       } else {
           cb.recordSuccess()
       }
       return err
   }
   ```

3. **Graceful Degradation**
   - AI unavailable → Allow trades with higher limits
   - Redis unavailable → Fall back to database
   - Kafka unavailable → Buffer in memory

4. **Automated Recovery**
   - Kubernetes auto-restart
   - State reconstruction from event log
   - Checkpoint/restore for long-running processes

5. **Manual Intervention**
   - Runbooks for each failure mode
   - Emergency shutdown procedures
   - Data recovery tools

### Disaster Recovery

- **RPO (Recovery Point Objective)**: <1 second (event log)
- **RTO (Recovery Time Objective)**: <5 minutes
- **Regular DR drills**: Quarterly failover tests

### Example: Matching Engine Crash

1. **Detection** (5 seconds)
   - Health check fails
   - Prometheus alert fires
   - PagerDuty notification

2. **Failover** (30 seconds)
   - Standby promoted to primary
   - DNS updated
   - State reconstructed from event log

3. **Recovery** (2 minutes)
   - Crashed instance restarted
   - Catch up on missed events
   - Return to standby pool

4. **Post-Mortem** (within 48 hours)
   - Root cause analysis
   - Action items created
   - Runbook updated

### Trade-offs

| Strategy | Benefit | Cost |
|----------|---------|------|
| Active-passive | Fast failover | 2x infrastructure |
| Graceful degradation | Partial availability | Complex logic |
| Event reconstruction | No data loss | Recovery time |
| Regular drills | Tested procedures | Engineering time |

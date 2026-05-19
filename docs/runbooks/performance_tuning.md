# Performance Tuning Guide

## Overview

This guide covers performance optimization techniques for AeroRisk AI to achieve:
- **>100k TPS** on the matching engine
- **<1ms p99 latency** for order processing
- **<200ms latency** for AI pipeline
- **<10ms** vector search retrieval

## Go Engine Optimization

### 1. Memory Management

#### Zero-Allocation Hot Path

```go
// BAD: Allocates on every call
func ProcessOrder(order *Order) {
    data := make([]byte, 1024)  // Allocation!
    // ...
}

// GOOD: Use sync.Pool
var bufferPool = sync.Pool{
    New: func() interface{} {
        return make([]byte, 1024)
    },
}

func ProcessOrder(order *Order) {
    data := bufferPool.Get().([]byte)
    defer bufferPool.Put(data)
    // ...
}
```

#### Pre-allocate Slices

```go
// BAD: Grows dynamically
results := []Result{}
for i := 0; i < 1000; i++ {
    results = append(results, process(i))
}

// GOOD: Pre-allocate capacity
results := make([]Result, 0, 1000)
for i := 0; i < 1000; i++ {
    results = append(results, process(i))
}
```

#### Avoid Interface Conversion

```go
// BAD: Interface conversion overhead
func Process(item interface{}) {
    v := item.(Value)
    // ...
}

// GOOD: Concrete types
func Process(v Value) {
    // ...
}
```

### 2. Concurrency Patterns

#### Lock-Free Ring Buffer

```go
type RingBuffer struct {
    buffer []EventSlot
    head   atomic.Uint64
    tail   atomic.Uint64
}

func (rb *RingBuffer) Publish(event Event) uint64 {
    seq := rb.head.Add(1) - 1
    slot := &rb.buffer[seq%uint64(len(rb.buffer))]
    
    // Cache-line padded write
    slot.event = event
    slot.sequence.Store(seq, atomic.Release)
    
    return seq
}
```

#### Worker Pool Pattern

```go
type WorkerPool struct {
    workers int
    jobs    chan Job
    wg      sync.WaitGroup
}

func NewWorkerPool(workers int) *WorkerPool {
    wp := &WorkerPool{
        workers: workers,
        jobs:    make(chan Job, 10000),
    }
    
    for i := 0; i < workers; i++ {
        go wp.worker()
    }
    
    return wp
}

func (wp *WorkerPool) worker() {
    for job := range wp.jobs {
        job.Process()
    }
}
```

### 3. GC Tuning

```bash
# Reduce GC frequency
export GOGC=50  # Default is 100

# Set memory limit (Go 1.19+)
export GOMEMLIMIT=4GiB

# Pin goroutines to CPUs
export GOMAXPROCS=8
```

```go
// In main.go
import _ "go.uber.org/automaxprocs"

func init() {
    // Automatically set GOMAXPROCS to match container CPU limit
    maxprocs.Set()
}
```

### 4. Network Optimization

#### Reuse Connections

```go
// BAD: New connection per request
func SendMessage(msg Message) {
    conn, _ := net.Dial("tcp", addr)
    conn.Write(msg.Bytes())
    conn.Close()
}

// GOOD: Connection pool
var connPool = &ConnPool{
    connections: make(chan net.Conn, 100),
}

func SendMessage(msg Message) {
    conn := <-connPool.connections
    conn.Write(msg.Bytes())
    connPool.connections <- conn
}
```

#### Batch Messages

```go
// BAD: One message at a time
for _, order := range orders {
    publisher.Publish(order)
}

// GOOD: Batch publish
batch := make([]Message, len(orders))
for i, order := range orders {
    batch[i] = order.ToMessage()
}
publisher.PublishBatch(batch)
```

### 5. Benchmarking

```bash
# Run benchmarks
cd engine
go test -bench=. -benchmem ./...

# Profile CPU
go test -bench=BenchmarkMatching -cpuprofile=cpu.prof

# Profile Memory
go test -bench=BenchmarkMatching -memprofile=mem.prof

# Analyze profiles
go tool pprof cpu.prof
go tool pprof mem.prof
```

**Key Metrics:**
- `ns/op` - Nanoseconds per operation (target: <10,000)
- `allocs/op` - Allocations per operation (target: 0-2)
- `B/op` - Bytes allocated per operation (target: <100)

## Python AI Guardrail Optimization

### 1. Async Optimization

#### Use asyncio.gather for Parallel Execution

```python
# BAD: Sequential
async def process_event(event):
    anomaly_result = await check_anomaly(event)
    context = await get_context(event)
    decision = await make_decision(anomaly_result, context)
    return decision

# GOOD: Parallel
async def process_event(event):
    anomaly_result, context = await asyncio.gather(
        check_anomaly(event),
        get_context(event)
    )
    decision = await make_decision(anomaly_result, context)
    return decision
```

#### Semaphore for Concurrency Control

```python
from asyncio import Semaphore

class RateLimitedProcessor:
    def __init__(self, max_concurrent=100):
        self.semaphore = Semaphore(max_concurrent)
    
    async def process(self, event):
        async with self.semaphore:
            return await self._process_internal(event)
```

### 2. LLM Inference Optimization

#### Batch Inference

```python
# BAD: One at a time
for event in events:
    decision = await llm.generate(event)

# GOOD: Batch
decisions = await llm.generate_batch(events, batch_size=32)
```

#### Model Quantization

```python
from transformers import AutoModelForCausalLM

# Load quantized model (4-bit)
model = AutoModelForCausalLM.from_pretrained(
    "mistralai/Mixtral-8x7B-Instruct-v0.1",
    load_in_4bit=True,
    device_map="auto",
    torch_dtype=torch.float16
)
```

#### CUDA Graphs

```python
import torch

# Enable CUDA graphs for faster inference
torch.set_float32_matmul_precision('high')
torch.backends.cuda.matmul.allow_tf32 = True
```

### 3. Vector Search Optimization

#### HNSW Index Tuning

```python
from qdrant_client import models

collection_config = models.VectorParams(
    size=768,
    distance=models.Distance.COSINE,
    hnsw_config=models.HnswConfig(
        m=16,           # Number of connections
        ef_construct=100,  # Build-time efficiency
        full_scan_threshold=10000
    ),
    quantization_config=models.ScalarQuantization(
        scalar=models.ScalarQuantizationConfig(
            type=models.ScalarType.INT8,
            quantile=0.99,
            always_ram=True
        )
    )
)
```

#### Caching Embeddings

```python
from functools import lru_cache

@lru_cache(maxsize=10000)
def get_embedding(text: str) -> Tuple[float]:
    embedding = model.encode(text)
    return tuple(embedding.tolist())
```

### 4. Kafka Consumer Tuning

```python
from aiokafka import AIOKafkaConsumer

consumer = AIOKafkaConsumer(
    'aerorisk.orders',
    bootstrap_servers='localhost:9092',
    group_id='ai-guardrail',
    
    # Batch settings
    fetch_min_bytes=1,
    fetch_max_bytes=52428800,  # 50MB
    fetch_max_wait_ms=500,
    
    # Concurrency
    max_poll_records=1000,
    max_partition_fetch_bytes=1048576,
    
    # Session management
    session_timeout_ms=30000,
    heartbeat_interval_ms=10000,
    
    # Enable auto-commit
    enable_auto_commit=True,
    auto_commit_interval_ms=5000
)
```

### 5. Profiling

```bash
# Install profiling tools
poetry add py-spy memory-profiler

# CPU profile
py-spy record -o profile.svg -- python aerorisk/main.py

# Memory profile
python -m memory_profiler aerorisk/main.py

# Async profiling
poetry add aiosignal-profiler
```

## Infrastructure Optimization

### Redis Tuning

```bash
# redis.conf optimizations
maxmemory 4gb
maxmemory-policy allkeys-lru

# Disable persistence for cache
save ""
appendonly no

# Increase client connections
maxclients 10000

# TCP keepalive
tcp-keepalive 300
```

### Kafka/Redpanda Tuning

```yaml
# docker-compose.yml
environment:
  # Producer settings
  KAFKA_NUM_NETWORK_THREADS: 8
  KAFKA_NUM_IO_THREADS: 16
  
  # Log settings
  KAFKA_LOG_SEGMENT_BYTES: 1073741824  # 1GB
  KAFKA_LOG_RETENTION_MS: 86400000  # 24 hours
  
  # Memory
  KAFKA_HEAP_OPTS: "-Xmx4G -Xms4G"
  
  # Batch settings
  KAFKA_BATCH_SIZE: 16384
  KAFKA_LINGER_MS: 5
```

### Qdrant Tuning

```yaml
# qdrant.yaml
storage:
  performance:
    optimizers:
      default_segment_number: 10
      max_segment_size: 1000000
      
    indexer:
      max_indexing_threads: 4
    
  grpc:
    max_message_size: 67108864  # 64MB
```

## Monitoring & Alerting

### Key Metrics to Track

**Go Engine:**
```promql
# Latency percentiles
histogram_quantile(0.99, rate(engine_order_latency_ns_bucket[5m]))

# Throughput
rate(engine_orders_processed_total[5m])

# Error rate
rate(engine_errors_total[5m]) / rate(engine_orders_processed_total[5m])

# Memory usage
go_memstats_heap_inuse_bytes
```

**AI Guardrail:**
```promql
# Pipeline latency
histogram_quantile(0.99, rate(agent_processing_latency_seconds_bucket[5m]))

# Queue depth
kafka_consumer_group_lag{group="ai-guardrail"}

# LLM inference time
histogram_quantile(0.99, rate(llm_inference_duration_seconds_bucket[5m]))
```

### Alert Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| Order Latency p99 | >500μs | >1ms |
| AI Pipeline Latency p99 | >150ms | >200ms |
| Error Rate | >0.1% | >1% |
| Kafka Consumer Lag | >1000 | >10000 |
| Memory Usage | >80% | >90% |
| CPU Usage | >70% | >90% |

## Load Testing

### Using k6

```javascript
// load_test.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '1m', target: 1000 },   // Ramp to 1000 RPS
    { duration: '5m', target: 1000 },   // Stay at 1000 RPS
    { duration: '1m', target: 10000 },  // Ramp to 10000 RPS
    { duration: '10m', target: 10000 }, // Stress test
  ],
  thresholds: {
    http_req_duration: ['p(99)<1'],     // 99% under 1ms
  },
};

export default function () {
  const payload = JSON.stringify({
    symbol: 'AAPL',
    side: 'BUY',
    quantity: 100,
    price: 17550,
  });
  
  const res = http.post('http://localhost:8080/orders', payload, {
    headers: { 'Content-Type': 'application/json' },
  });
  
  check(res, {
    'status is 200': (r) => r.status === 200,
  });
  
  sleep(0.001);
}
```

```bash
# Run load test
k6 run load_test.js
```

## Troubleshooting

### High Latency

1. Check GC pauses: `go tool trace trace.out`
2. Profile CPU: `go tool pprof cpu.prof`
3. Check lock contention: `go tool pprof -mutex mutex.prof`
4. Monitor network: `iftop`, `nethogs`

### Memory Issues

1. Check heap: `go tool pprof heap.prof`
2. Look for leaks: `goleak` package
3. Monitor RSS: `ps aux | grep engine`

### Throughput Problems

1. Check CPU saturation: `top`, `htop`
2. Verify batching is working
3. Check network bandwidth
4. Review Kafka consumer lag

## Continuous Optimization

1. **Weekly**: Review benchmark results
2. **Monthly**: Run full load tests
3. **Quarterly**: Profile production traffic
4. **Always**: Monitor key metrics and alert on regressions

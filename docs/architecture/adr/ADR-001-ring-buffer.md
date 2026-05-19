# ADR-001: LMAX Disruptor Ring Buffer

## Status
Accepted

## Context
The matching engine requires ultra-low latency (<1ms p99) for order processing while handling >100k TPS. Traditional queue-based architectures introduce lock contention and GC pressure that violate these requirements.

## Decision
We will implement the LMAX Disruptor pattern using a ring buffer with:
- Pre-allocated event slots (no runtime allocation)
- Single-writer principle (no locks for producers)
- Cache-line padding to prevent false sharing
- configurable wait strategies (BusySpin for production)
- Batch processing for consumer throughput

### Implementation Details
```go
type RingBuffer struct {
    buffer []EventSlot  // Pre-allocated
    size   int64        // Power of 2 for modulo optimization
    cursor *atomic.Int64 // Write position
}

type EventSlot struct {
    sequence int64
    event    OrderEvent
    // 48 bytes padding for 64-byte cache line
    _ [48]byte
}
```

## Consequences

### Positive
- Zero allocations on hot path after initialization
- Lock-free producer operations
- Predictable latency profile
- Cache-friendly memory access patterns

### Negative
- Fixed buffer size (requires capacity planning)
- More complex implementation than standard channels
- Requires careful sequence number management

### Risks
- Buffer overflow if consumers fall behind
- Mitigation: Multiple wait strategies, monitoring, auto-scaling

## Compliance
This architecture supports audit requirements by maintaining ordered event sequences with guaranteed delivery semantics.

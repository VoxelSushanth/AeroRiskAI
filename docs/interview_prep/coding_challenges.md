# Coding Challenges

## Challenge 1: Lock-Free Ring Buffer Implementation

**Difficulty**: Hard  
**Time Limit**: 60 minutes

### Problem

Implement a lock-free ring buffer for the AeroRisk trading engine. The ring buffer must support:
- Single producer, multiple consumer pattern
- Cache-line padding to prevent false sharing
- Atomic sequence numbers for ordering
- Wait strategies (busy spin, yield, blocking)

### Requirements

```go
type RingBuffer struct {
    // Your implementation here
}

func NewRingBuffer(size int64) *RingBuffer
func (rb *RingBuffer) Publish(event Event) int64
func (rb *RingBuffer) Read(sequence int64) Event
func (rb *RingBuffer) AvailableToRead() int64
```

### Constraints

- Must be lock-free (use atomics only)
- Size must be power of 2
- Cache-line aligned (64 bytes on x86)
- Support at least 1M operations/second

### Test Cases

```go
// Test 1: Basic publish/read
func TestBasicPublishRead(t *testing.T) {
    rb := NewRingBuffer(1024)
    seq := rb.Publish(Event{ID: 1})
    event := rb.Read(seq)
    assert.Equal(t, int64(1), event.ID)
}

// Test 2: Wraparound
func TestWraparound(t *testing.T) {
    rb := NewRingBuffer(4)
    for i := 0; i < 100; i++ {
        seq := rb.Publish(Event{ID: int64(i)})
        event := rb.Read(seq)
        assert.Equal(t, int64(i), event.ID)
    }
}

// Test 3: Concurrent readers
func TestConcurrentReaders(t *testing.T) {
    rb := NewRingBuffer(1024)
    
    go func() {
        for i := 0; i < 1000; i++ {
            rb.Publish(Event{ID: int64(i)})
        }
    }()
    
    var wg sync.WaitGroup
    for i := 0; i < 4; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            // Read events
        }()
    }
    wg.Wait()
}

// Test 4: Performance benchmark
func BenchmarkRingBuffer(b *testing.B) {
    rb := NewRingBuffer(65536)
    b.ResetTimer()
    for i := 0; i < b.N; i++ {
        seq := rb.Publish(Event{ID: int64(i)})
        _ = rb.Read(seq)
    }
    // Target: >1M ops/sec
}
```

### Evaluation Criteria

1. **Correctness**: All tests pass
2. **Performance**: >1M ops/sec in benchmark
3. **Code Quality**: Clean, well-documented code
4. **Edge Cases**: Handles wraparound, concurrent access

---

## Challenge 2: Order Matching Engine

**Difficulty**: Medium-Hard  
**Time Limit**: 90 minutes

### Problem

Implement a limit order book matching engine with price-time priority.

### Requirements

```go
type OrderBook struct {
    // Your implementation
}

type Order struct {
    ID       string
    Symbol   string
    Side     Side  // BUY or SELL
    Price    int64 // Fixed-point (8 decimals)
    Quantity int64
    Timestamp int64
}

type Trade struct {
    BuyOrderID  string
    SellOrderID string
    Price       int64
    Quantity    int64
    Timestamp   int64
}

func NewOrderBook(symbol string) *OrderBook
func (ob *OrderBook) SubmitOrder(order *Order) ([]*Trade, error)
func (ob *OrderBook) CancelOrder(orderID string) error
func (ob *OrderBook) GetBestBid() (price int64, quantity int64)
func (ob *OrderBook) GetBestAsk() (price int64, quantity int64)
```

### Matching Rules

1. **Price Priority**: Best price executes first
2. **Time Priority**: Same price, earlier order executes first
3. **Pro-Rata**: Optional mode for equal time priority orders

### Example

```
Order Book State:
Bids: [(175.50, 100), (175.40, 200)]
Asks: [(175.60, 150), (175.70, 300)]

New Order: SELL 120 @ 175.50
Result: 
  - Match 100 @ 175.50 with best bid
  - Remaining 20 added to asks at 175.50
```

### Test Cases

```go
// Test 1: Basic match
func TestBasicMatch(t *testing.T) {
    ob := NewOrderBook("AAPL")
    ob.SubmitOrder(&Order{Side: BUY, Price: 17550, Quantity: 100})
    trades, _ := ob.SubmitOrder(&Order{Side: SELL, Price: 17550, Quantity: 100})
    assert.Len(t, trades, 1)
    assert.Equal(t, int64(100), trades[0].Quantity)
}

// Test 2: Partial match
func TestPartialMatch(t *testing.T) {
    ob := NewOrderBook("AAPL")
    ob.SubmitOrder(&Order{Side: BUY, Price: 17550, Quantity: 100})
    trades, _ := ob.SubmitOrder(&Order{Side: SELL, Price: 17550, Quantity: 150})
    assert.Len(t, trades, 1)
    assert.Equal(t, int64(100), trades[0].Quantity)
    bestBid, qty := ob.GetBestBid()
    assert.Equal(t, int64(0), qty) // No more bids
}

// Test 3: Price-time priority
func TestPriceTimePriority(t *testing.T) {
    ob := NewOrderBook("AAPL")
    ob.SubmitOrder(&Order{ID: "1", Side: BUY, Price: 17550, Quantity: 100})
    ob.SubmitOrder(&Order{ID: "2", Side: BUY, Price: 17550, Quantity: 100})
    trades, _ := ob.SubmitOrder(&Order{Side: SELL, Price: 17550, Quantity: 150})
    // Order 1 should be matched first (time priority)
    assert.Equal(t, "1", trades[0].BuyOrderID)
}
```

### Evaluation Criteria

1. **Correctness**: Matching logic is accurate
2. **Data Structures**: Efficient implementation (heaps, trees)
3. **Complexity**: O(log n) for insert/cancel
4. **Testing**: Comprehensive test coverage

---

## Challenge 3: Anomaly Detection Algorithm

**Difficulty**: Medium  
**Time Limit**: 45 minutes

### Problem

Implement a velocity-based anomaly detector for trading patterns.

### Requirements

```python
class VelocityChecker:
    def __init__(self, window_sizes: List[int], thresholds: Dict):
        pass
    
    def check(self, events: List[TradingEvent]) -> AnomalyResult:
        """
        Detect unusual trading velocity.
        
        Returns AnomalyResult with:
        - risk_score: 0-100
        - anomaly_type: "VELOCITY"
        - details: {window_stats, threshold_breaches}
        """
        pass
```

### Detection Logic

Track these metrics over sliding windows:
1. Orders per second (1s, 5s, 60s windows)
2. Notional value per minute
3. Cancel/replace ratio
4. Order modification frequency

### Scoring

```python
def calculate_risk_score(metrics: Dict) -> int:
    score = 0
    
    # Orders per second
    if metrics['ops_1s'] > 500:
        score += 40
    elif metrics['ops_1s'] > 100:
        score += 20
    
    # Notional value
    if metrics['notional_per_min'] > 50_000_000:
        score += 30
    elif metrics['notional_per_min'] > 10_000_000:
        score += 15
    
    # Cancel ratio
    if metrics['cancel_ratio'] > 0.95:
        score += 30
    elif metrics['cancel_ratio'] > 0.8:
        score += 15
    
    return min(score, 100)
```

### Test Cases

```python
def test_normal_trading():
    checker = VelocityChecker(...)
    events = generate_normal_events(count=100, duration_seconds=60)
    result = checker.check(events)
    assert result.risk_score < 30

def test_high_velocity():
    checker = VelocityChecker(...)
    events = generate_high_velocity_events(count=1000, duration_seconds=1)
    result = checker.check(events)
    assert result.risk_score > 60
    assert result.anomaly_type == "VELOCITY"

def test_wash_trade_pattern():
    checker = VelocityChecker(...)
    events = generate_wash_trade_pattern()
    result = checker.check(events)
    assert result.details['cancel_ratio'] > 0.9
```

### Evaluation Criteria

1. **Algorithm Efficiency**: O(n) time complexity
2. **Accuracy**: Correctly identifies anomalies
3. **Code Quality**: Clean, Pythonic code
4. **Edge Cases**: Empty input, single event, etc.

---

## Challenge 4: Circuit Breaker Implementation

**Difficulty**: Easy-Medium  
**Time Limit**: 30 minutes

### Problem

Implement a circuit breaker pattern for system resilience.

### Requirements

```go
type CircuitBreaker struct {
    state         State
    failureCount  int
    lastFailure   time.Time
    successCount  int
}

type State int

const (
    StateClosed State = iota
    StateOpen
    StateHalfOpen
)

func (cb *CircuitBreaker) Execute(fn func() error) error
func (cb *CircuitBreaker) RecordSuccess()
func (cb *CircuitBreaker) RecordFailure()
func (cb *CircuitBreaker) Allow() bool
```

### State Machine

```
CLOSED → (failures >= threshold) → OPEN
OPEN → (timeout elapsed) → HALF_OPEN
HALF_OPEN → (success) → CLOSED
HALF_OPEN → (failure) → OPEN
```

### Configuration

```go
type Config struct {
    FailureThreshold int           // Failures before opening
    SuccessThreshold int           // Successes in half-open to close
    Timeout          time.Duration // Time in open state
}
```

### Test Cases

```go
func TestCircuitOpensAfterFailures(t *testing.T) {
    cb := NewCircuitBreaker(Config{FailureThreshold: 3})
    for i := 0; i < 3; i++ {
        cb.RecordFailure()
    }
    assert.False(t, cb.Allow()) // Should be open
}

func TestCircuitTransitionsToHalfOpen(t *testing.T) {
    cb := NewCircuitBreaker(Config{Timeout: 100 * time.Millisecond})
    // Open the circuit
    for i := 0; i < 3; i++ {
        cb.RecordFailure()
    }
    // Wait for timeout
    time.Sleep(150 * time.Millisecond)
    assert.True(t, cb.Allow()) // Should be half-open
}

func TestCircuitClosesAfterSuccesses(t *testing.T) {
    cb := NewCircuitBreaker(Config{SuccessThreshold: 2})
    // Get to half-open state
    // ...
    // Record successes
    cb.RecordSuccess()
    cb.RecordSuccess()
    assert.Equal(t, StateClosed, cb.state)
}
```

### Evaluation Criteria

1. **State Machine**: Correct transitions
2. **Thread Safety**: Safe for concurrent use
3. **Testing**: Covers all state transitions
4. **Code Clarity**: Easy to understand

---

## Bonus Challenge: Distributed Ledger

**Difficulty**: Very Hard  
**Time Limit**: Take-home (1 week)

### Problem

Design and implement a distributed ledger that maintains consistency across multiple nodes.

### Requirements

- ACID transactions
- Event sourcing architecture
- Conflict resolution
- Audit trail
- Recovery from node failures

### Deliverables

1. Working implementation
2. Design document explaining trade-offs
3. Load test results
4. Failure scenario testing

---

## Submission Guidelines

1. **Repository**: Create a private GitHub repo and invite reviewers
2. **README**: Include setup instructions and design decisions
3. **Tests**: All code must have unit tests
4. **Documentation**: Comment complex logic
5. **Performance**: Include benchmarks where applicable

## Evaluation Rubric

| Category | Weight | Criteria |
|----------|--------|----------|
| Correctness | 40% | All tests pass, handles edge cases |
| Performance | 25% | Meets latency/throughput targets |
| Code Quality | 20% | Clean, maintainable, well-documented |
| Testing | 15% | Comprehensive test coverage |

## Tips for Success

1. **Start Simple**: Get a working solution first, optimize later
2. **Test Early**: Write tests as you develop
3. **Document Decisions**: Explain why you chose certain approaches
4. **Consider Edge Cases**: Empty inputs, concurrent access, failures
5. **Benchmark**: Prove your solution meets performance requirements

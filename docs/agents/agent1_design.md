# Agent 1: Anomaly Detection Design

## Overview

Agent 1 is responsible for real-time anomaly detection in trading patterns. It analyzes order flow, execution patterns, and market behavior to identify potential fraud, manipulation, or abnormal trading activity.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent 1: Anomaly Detection               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Velocity   │  │    VWAP      │  │    Wash      │      │
│  │    Check     │  │   Monitor    │  │   Trade      │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐                         │
│  │   Spoofing   │  │  Embedding   │                         │
│  │     HMM      │  │  Similarity  │                         │
│  └──────────────┘  └──────────────┘                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. Velocity Check (`velocity_check.py`)

**Purpose**: Detect unusual trading velocity that may indicate:
- Algorithmic runaway
- Fat-finger errors
- Intentional market manipulation
- Account takeover

**Metrics Tracked**:
- Orders per second (rolling 1s, 5s, 60s windows)
- Notional value per minute
- Cancel/replace ratio
- Order modification frequency

**Thresholds**:
```python
VELOCITY_LIMITS = {
    "orders_per_second": {
        "warning": 100,
        "critical": 500,
        "block": 1000
    },
    "notional_per_minute": {
        "warning": 10_000_000,  # $10M
        "critical": 50_000_000,  # $50M
        "block": 100_000_000  # $100M
    },
    "cancel_ratio": {
        "warning": 0.8,  # 80% cancellation
        "critical": 0.95,  # 95% cancellation
        "block": 0.99  # 99% cancellation
    }
}
```

**Algorithm**:
```python
def check_velocity(event, account_state):
    window_1s = count_orders(account_id, last_1_second)
    window_5s = count_orders(account_id, last_5_seconds)
    window_60s = count_orders(account_id, last_60_seconds)
    
    notional = calculate_notional_value(event)
    cancel_ratio = calculate_cancel_ratio(account_id)
    
    risk_score = 0
    if window_1s > VELOCITY_LIMITS["orders_per_second"]["critical"]:
        risk_score += 40
    elif window_1s > VELOCITY_LIMITS["orders_per_second"]["warning"]:
        risk_score += 20
    
    # ... additional checks
    
    return AnomalyResult(
        anomaly_type="VELOCITY",
        risk_score=risk_score,
        details={...}
    )
```

### 2. VWAP Monitor (`vwap_monitor.py`)

**Purpose**: Detect trades executed at prices significantly deviating from Volume-Weighted Average Price (VWAP), which may indicate:
- Front-running
- Manipulation
- Poor execution quality
- Insider trading

**Calculation**:
```python
VWAP = Σ(Price × Quantity) / Σ(Quantity)
```

**Deviation Detection**:
```python
def check_vwap_deviation(trade, symbol):
    vwap = get_vwap(symbol, lookback_minutes=30)
    deviation = abs(trade.price - vwap) / vwap
    
    if deviation > 0.05:  # 5% deviation
        return AnomalyResult(
            anomaly_type="VWAP_DEVIATION",
            risk_score=min(int(deviation * 100), 100),
            details={
                "trade_price": trade.price,
                "vwap": vwap,
                "deviation_pct": deviation * 100
            }
        )
```

### 3. Wash Trade Detection (`wash_trade.py`)

**Purpose**: Identify wash trading patterns where the same entity buys and sells the same security without changing beneficial ownership.

**Detection Patterns**:
1. **Same Account**: Buy and sell from same account within short timeframe
2. **Related Accounts**: Trades between accounts with common ownership
3. **Circular Trading**: A→B→C→A pattern

**Algorithm**:
```python
def detect_wash_trade(event, account_graph):
    # Check for matching buy/sell within time window
    matching_trades = find_matching_trades(
        account_id=event.account_id,
        symbol=event.symbol,
        quantity=event.quantity,
        time_window_ms=5000
    )
    
    if matching_trades:
        # Check for opposite side
        for trade in matching_trades:
            if trade.side != event.side and trade.quantity == event.quantity:
                # Potential wash trade
                if are_related_accounts(event.account_id, trade.account_id):
                    return AnomalyResult(
                        anomaly_type="WASH_TRADE",
                        risk_score=90,
                        confidence=0.95,
                        details={...}
                    )
```

**Graph Analysis**:
- Build account relationship graph
- Detect circular ownership patterns
- Flag related account clusters

### 4. Spoofing Detection with HMM (`spoofing_hmm.py`)

**Purpose**: Detect spoofing/layering manipulation using Hidden Markov Models (HMM).

**Spoofing Pattern**:
1. Place large orders on one side of book
2. Execute small trades on opposite side
3. Cancel large orders before execution

**HMM States**:
- `NORMAL`: Legitimate trading
- `BUILDING`: Accumulating orders (potential spoof setup)
- `EXECUTING`: Small trades on opposite side
- `CANCELING`: Rapid order cancellations

**Model Training**:
```python
class SpoofingHMM:
    def __init__(self):
        self.n_states = 4
        self.n_features = 6  # order_size, cancel_rate, etc.
        
        # Initialize HMM parameters
        self.model = GaussianHMM(
            n_components=4,
            covariance_type="full",
            n_iter=100
        )
    
    def train(self, historical_data):
        features = extract_features(historical_data)
        self.model.fit(features)
    
    def predict_spoofing_probability(self, order_flow):
        features = extract_features(order_flow)
        log_prob = self.model.score(features)
        state_sequence = self.model.predict(features)
        
        # Calculate spoofing probability
        spoofing_states = [1, 2, 3]  # BUILDING, EXECUTING, CANCELING
        prob = sum(1 for s in state_sequence if s in spoofing_states) / len(state_sequence)
        
        return prob
```

**Features**:
1. Order size imbalance (bid vs ask)
2. Cancel-to-execution ratio
3. Order lifetime distribution
4. Price impact after cancellation
5. Order book depth changes
6. Trade direction consistency

### 5. Embedding Similarity Search (`embedding.py`)

**Purpose**: Use vector embeddings to find similar historical fraud patterns.

**Embedding Generation**:
```python
def generate_event_embedding(event_sequence):
    # Extract features
    features = {
        "order_frequency": calculate_frequency(event_sequence),
        "price_pattern": extract_price_pattern(event_sequence),
        "volume_profile": extract_volume_profile(event_sequence),
        "timing_pattern": extract_timing_pattern(event_sequence),
        "cancellation_behavior": extract_cancellation_stats(event_sequence)
    }
    
    # Generate embedding using pre-trained model
    embedding = fraud_embedding_model.encode(features)
    
    return embedding
```

**Similarity Search**:
```python
def find_similar_fraud_patterns(current_embedding, top_k=5):
    results = qdrant_client.search(
        collection_name="fraud_patterns",
        query_vector=current_embedding.tolist(),
        limit=top_k
    )
    
    similar_patterns = []
    for result in results:
        if result.score > 0.7:  # Similarity threshold
            similar_patterns.append({
                "pattern_id": result.payload["id"],
                "fraud_type": result.payload["fraud_type"],
                "similarity_score": result.score,
                "historical_outcome": result.payload["outcome"]
            })
    
    return similar_patterns
```

## Output Schema

```python
@dataclass
class AnomalyResult:
    anomaly_type: str  # VELOCITY, VWAP_DEVIATION, WASH_TRADE, SPOOFING, SIMILAR_PATTERN
    risk_score: int  # 0-100
    confidence: float  # 0.0-1.0
    timestamp: int  # Unix nanos
    account_id: str
    symbol: Optional[str]
    details: Dict[str, Any]
    recommended_action: str  # ALLOW, FLAG, BLOCK, INVESTIGATE
    evidence: List[Dict]  # Supporting data points
```

## Performance Requirements

| Metric | Target | Measurement |
|--------|--------|-------------|
| Processing Latency | <10ms p99 | Per event |
| Throughput | >100k events/sec | Aggregate |
| False Positive Rate | <5% | Weekly average |
| True Positive Rate | >95% | Known fraud cases |
| Memory Usage | <1GB | Per instance |

## Integration with LangGraph

```python
from langgraph.graph import StateGraph

def agent1_node(state: GraphState) -> GraphState:
    event = state["current_event"]
    
    # Run all detectors in parallel
    results = await asyncio.gather(
        check_velocity(event),
        check_vwap(event),
        detect_wash_trade(event),
        detect_spoofing(event),
        find_similar_patterns(event)
    )
    
    # Aggregate results
    max_risk_score = max(r.risk_score for r in results)
    anomaly_types = [r.anomaly_type for r in results if r.risk_score > 50]
    
    state["anomaly_results"] = results
    state["anomaly_risk_score"] = max_risk_score
    state["detected_anomalies"] = anomaly_types
    
    return state
```

## Monitoring & Alerting

**Prometheus Metrics**:
```python
anomaly_detection_latency = Histogram(
    'agent1_detection_latency_seconds',
    'Time to detect anomalies'
)

anomaly_count = Counter(
    'agent1_anomalies_total',
    'Total anomalies detected',
    ['type', 'severity']
)

false_positive_rate = Gauge(
    'agent1_false_positive_rate',
    'Current false positive rate'
)
```

**Alerts**:
- Spike in anomaly detections (>10x baseline)
- High false positive rate (>10%)
- Processing latency >50ms p99
- Memory usage >80%

## Testing Strategy

1. **Unit Tests**: Test each detector independently
2. **Integration Tests**: Test full pipeline with synthetic data
3. **Load Tests**: Verify performance under load
4. **Chaos Tests**: Inject anomalous patterns randomly
5. **Backtesting**: Run against historical fraud cases

## Continuous Improvement

1. **Feedback Loop**: Incorporate investigator decisions
2. **Model Retraining**: Weekly HMM retraining
3. **Threshold Tuning**: Monthly review based on FP/FN rates
4. **Pattern Discovery**: Clustering analysis for new patterns

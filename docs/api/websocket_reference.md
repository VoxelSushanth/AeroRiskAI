# WebSocket API Reference

## Overview

AeroRisk AI provides a real-time WebSocket API for streaming market data, trade notifications, and account updates. The WebSocket interface complements the gRPC API by offering push-based updates with sub-millisecond latency.

## Connection

**Endpoint:** `wss://api.aerorisk.ai/v1/ws`

### Connection Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `token` | string | Yes | JWT authentication token |
| `client_id` | string | Yes | Client identifier |
| `protocols` | array | No | Requested protocols: `["orders", "trades", "quotes", "account"]` |

### Example Connection

```javascript
const ws = new WebSocket(
  'wss://api.aerorisk.ai/v1/ws?token=eyJhbG...&client_id=client_123'
);
```

## Message Format

All messages follow this structure:

```json
{
  "type": "message_type",
  "sequence": 1234567890,
  "timestamp": 1703001234567890123,
  "data": { ... }
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Message type identifier |
| `sequence` | int64 | Monotonically increasing sequence number |
| `timestamp` | int64 | Server timestamp (Unix nanoseconds) |
| `data` | object | Message-specific payload |

## Subscription Messages

### Subscribe to Order Updates

```json
{
  "type": "subscribe",
  "channel": "orders",
  "filters": {
    "symbols": ["AAPL", "GOOGL"],
    "account_id": "acc_123"
  }
}
```

### Subscribe to Trade Stream

```json
{
  "type": "subscribe",
  "channel": "trades",
  "filters": {
    "symbols": ["BTCUSD"]
  }
}
```

### Subscribe to Quotes (Order Book)

```json
{
  "type": "subscribe",
  "channel": "quotes",
  "filters": {
    "symbols": ["AAPL"],
    "depth": 20
  }
}
```

### Subscribe to Account Updates

```json
{
  "type": "subscribe",
  "channel": "account",
  "filters": {
    "account_id": "acc_123"
  }
}
```

## Message Types

### Order Status Update

```json
{
  "type": "order_update",
  "sequence": 1001,
  "timestamp": 1703001234567890123,
  "data": {
    "order_id": "ord_abc123",
    "client_order_id": "client_xyz789",
    "symbol": "AAPL",
    "side": "BUY",
    "order_type": "LIMIT",
    "price": 17550000000,
    "quantity": 100000000,
    "filled_quantity": 50000000,
    "remaining_quantity": 50000000,
    "status": "PARTIALLY_FILLED",
    "risk_decision": "ALLOW",
    "created_at": 1703001234000000000,
    "updated_at": 1703001234567890123
  }
}
```

### Trade Execution

```json
{
  "type": "trade",
  "sequence": 1002,
  "timestamp": 1703001234567890456,
  "data": {
    "trade_id": "trd_def456",
    "order_id": "ord_abc123",
    "symbol": "AAPL",
    "side": "BUY",
    "price": 17550000000,
    "quantity": 25000000,
    "liquidity": "TAKER",
    "fee": 4387500,
    "counterparty_order_id": "ord_ghi789"
  }
}
```

### Order Book Snapshot

```json
{
  "type": "orderbook_snapshot",
  "sequence": 1003,
  "timestamp": 1703001234567890789,
  "data": {
    "symbol": "AAPL",
    "bids": [
      {"price": 17540000000, "quantity": 500000000, "order_count": 15},
      {"price": 17530000000, "quantity": 750000000, "order_count": 23}
    ],
    "asks": [
      {"price": 17560000000, "quantity": 400000000, "order_count": 12},
      {"price": 17570000000, "quantity": 600000000, "order_count": 18}
    ]
  }
}
```

### Order Book Update (Delta)

```json
{
  "type": "orderbook_update",
  "sequence": 1004,
  "timestamp": 1703001234567891012,
  "data": {
    "symbol": "AAPL",
    "bids": [
      {"price": 17540000000, "quantity": 450000000, "order_count": 14}
    ],
    "asks": [],
    "is_delta": true
  }
}
```

### Balance Update

```json
{
  "type": "balance_update",
  "sequence": 1005,
  "timestamp": 1703001234567891345,
  "data": {
    "account_id": "acc_123",
    "symbol": "USD",
    "available": 99562500000,
    "locked": 17550000000,
    "total": 117112500000
  }
}
```

### Risk Alert

```json
{
  "type": "risk_alert",
  "sequence": 1006,
  "timestamp": 1703001234567891678,
  "data": {
    "account_id": "acc_123",
    "alert_type": "VELOCITY_LIMIT",
    "severity": "WARNING",
    "message": "Trading velocity approaching daily limit",
    "current_value": 85000000000,
    "threshold": 100000000000,
    "action": "MONITORING"
  }
}
```

### Circuit Breaker Event

```json
{
  "type": "circuit_breaker",
  "sequence": 1007,
  "timestamp": 1703001234567892001,
  "data": {
    "symbol": "AAPL",
    "state": "OPEN",
    "reason": "PRICE_VOLATILITY",
    "trigger_price": 18000000000,
    "reference_price": 17500000000,
    "cooldown_seconds": 300,
    "resumes_at": 1703001534567892001
  }
}
```

## Control Messages

### Heartbeat (Ping/Pong)

Server sends ping every 30 seconds:

```json
{
  "type": "ping",
  "timestamp": 1703001234567892334
}
```

Client must respond within 10 seconds:

```json
{
  "type": "pong",
  "timestamp": 1703001234567892445
}
```

### Error Response

```json
{
  "type": "error",
  "code": "INVALID_SUBSCRIPTION",
  "message": "Unknown channel: 'invalid_channel'",
  "details": {
    "valid_channels": ["orders", "trades", "quotes", "account"]
  }
}
```

### Rate Limit Warning

```json
{
  "type": "rate_limit_warning",
  "limit": 1000,
  "window_seconds": 60,
  "current_rate": 950,
  "reset_at": 1703001294567892556
}
```

## Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_SUBSCRIPTION` | 400 | Invalid subscription parameters |
| `UNAUTHORIZED` | 401 | Authentication failed |
| `FORBIDDEN` | 403 | Access denied to resource |
| `NOT_FOUND` | 404 | Symbol or account not found |
| `RATE_LIMITED` | 429 | Rate limit exceeded |
| `INTERNAL_ERROR` | 500 | Internal server error |

## Reconnection Strategy

Implement exponential backoff for reconnections:

```javascript
let reconnectDelay = 1000; // Start with 1 second
const maxDelay = 30000; // Max 30 seconds

ws.onclose = () => {
  setTimeout(() => {
    connect();
    reconnectDelay = Math.min(reconnectDelay * 2, maxDelay);
  }, reconnectDelay);
};

ws.onopen = () => {
  reconnectDelay = 1000; // Reset on successful connection
};
```

## Sequence Number Handling

- Sequence numbers are monotonically increasing per channel
- Detect gaps to identify missed messages
- Request historical replay if gap detected:

```json
{
  "type": "replay_request",
  "channel": "orders",
  "from_sequence": 1000,
  "to_sequence": 1050
}
```

## Performance Characteristics

- **Message Latency**: <500μs p99
- **Throughput**: >500k messages/second
- **Connection Limit**: 100 concurrent connections per account
- **Message Size**: Typically <1KB, max 64KB

## Best Practices

1. **Handle disconnections gracefully** - Always implement reconnection logic
2. **Monitor sequence numbers** - Detect and handle gaps
3. **Respond to heartbeats** - Avoid timeout disconnections
4. **Use filters** - Subscribe only to needed symbols/channels
5. **Buffer messages** - Process messages asynchronously to avoid blocking
6. **Log sequence numbers** - For debugging and audit trails

## Fixed-Point Arithmetic

All monetary values use fixed-point arithmetic with 8 decimal places:

```javascript
// Price: 17550000000 = $175.50
// Quantity: 100000000 = 1.0 shares
// Value: 17550000000 * 100000000 / 10^16 = $175.50
```

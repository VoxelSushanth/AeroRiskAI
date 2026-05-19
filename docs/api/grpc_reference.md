# gRPC API Reference

## Overview

AeroRisk AI exposes a high-performance gRPC API for order management, market data, and account operations. The API is designed for ultra-low latency (<1ms p99) and supports >100k TPS.

## Service Definition

```protobuf
service AeroRiskService {
  // Order Management
  rpc SubmitOrder(SubmitOrderRequest) returns (SubmitOrderResponse);
  rpc CancelOrder(CancelOrderRequest) returns (CancelOrderResponse);
  rpc ModifyOrder(ModifyOrderRequest) returns (ModifyOrderResponse);
  
  // Market Data
  rpc GetOrderBook(OrderBookRequest) returns (OrderBookResponse);
  rpc StreamTrades(TradeStreamRequest) returns (stream TradeEvent);
  rpc StreamQuotes(QuoteStreamRequest) returns (stream QuoteEvent);
  
  // Account Operations
  rpc GetBalance(BalanceRequest) returns (BalanceResponse);
  rpc GetAccountStatus(AccountStatusRequest) returns (AccountStatusResponse);
}
```

## Messages

### SubmitOrderRequest

| Field | Type | Description |
|-------|------|-------------|
| `client_order_id` | string | Unique client-generated order ID (max 64 chars) |
| `symbol` | string | Trading pair symbol (e.g., "AAPL", "BTCUSD") |
| `side` | Side | BUY or SELL |
| `order_type` | OrderType | MARKET, LIMIT, STOP, STOP_LIMIT |
| `quantity` | int64 | Order quantity in base currency (fixed-point, 8 decimals) |
| `price` | int64 | Limit price in quote currency (fixed-point, 8 decimals) |
| `stop_price` | int64 | Stop trigger price (for STOP orders) |
| `time_in_force` | TimeInForce | GTC, IOC, FOK, GTD |
| `expire_at` | int64 | Expiration timestamp (Unix nanos, for GTD orders) |
| `account_id` | string | Account identifier |
| `metadata` | map<string,string> | Optional key-value metadata |

### SubmitOrderResponse

| Field | Type | Description |
|-------|------|-------------|
| `order_id` | string | Server-generated order ID |
| `status` | OrderStatus | PENDING, ACCEPTED, REJECTED, FILLED, CANCELLED |
| `timestamp` | int64 | Server timestamp (Unix nanos) |
| `latency_ns` | int64 | Processing latency in nanoseconds |
| `risk_decision` | RiskDecision | ALLOW, FLAG, BLOCK, ADJUST_LIMIT |
| `message` | string | Status message or error description |

### CancelOrderRequest

| Field | Type | Description |
|-------|------|-------------|
| `order_id` | string | Order ID to cancel |
| `account_id` | string | Account identifier |
| `reason` | string | Cancellation reason (optional) |

### CancelOrderResponse

| Field | Type | Description |
|-------|------|-------------|
| `success` | bool | Cancellation success flag |
| `order_id` | string | Cancelled order ID |
| `cancelled_quantity` | int64 | Quantity that was cancelled |
| `filled_quantity` | int64 | Quantity that was already filled |
| `timestamp` | int64 | Cancellation timestamp (Unix nanos) |

### OrderBookRequest

| Field | Type | Description |
|-------|------|-------------|
| `symbol` | string | Trading pair symbol |
| `depth` | int32 | Number of price levels (max 100) |

### OrderBookResponse

| Field | Type | Description |
|-------|------|-------------|
| `symbol` | string | Trading pair symbol |
| `bids` | repeated PriceLevel | Bid side (buy orders) |
| `asks` | repeated PriceLevel | Ask side (sell orders) |
| `timestamp` | int64 | Snapshot timestamp (Unix nanos) |
| `sequence_num` | int64 | Order book sequence number |

### PriceLevel

| Field | Type | Description |
|-------|------|-------------|
| `price` | int64 | Price level (fixed-point, 8 decimals) |
| `quantity` | int64 | Total quantity at this level |
| `order_count` | int32 | Number of orders at this level |

### BalanceRequest

| Field | Type | Description |
|-------|------|-------------|
| `account_id` | string | Account identifier |
| `symbol` | string | Asset symbol (optional, all if empty) |

### BalanceResponse

| Field | Type | Description |
|-------|------|-------------|
| `account_id` | string | Account identifier |
| `balances` | repeated AssetBalance | List of asset balances |
| `timestamp` | int64 | Balance snapshot timestamp |

### AssetBalance

| Field | Type | Description |
|-------|------|-------------|
| `symbol` | string | Asset symbol |
| `available` | int64 | Available balance (fixed-point, 8 decimals) |
| `locked` | int64 | Locked/in-order balance |
| `total` | int64 | Total balance (available + locked) |

## Enums

### Side

| Value | Number | Description |
|-------|--------|-------------|
| `SIDE_UNSPECIFIED` | 0 | Invalid/unknown side |
| `SIDE_BUY` | 1 | Buy order |
| `SIDE_SELL` | 2 | Sell order |

### OrderType

| Value | Number | Description |
|-------|--------|-------------|
| `ORDER_TYPE_UNSPECIFIED` | 0 | Invalid/unknown type |
| `ORDER_TYPE_MARKET` | 1 | Market order |
| `ORDER_TYPE_LIMIT` | 2 | Limit order |
| `ORDER_TYPE_STOP` | 3 | Stop market order |
| `ORDER_TYPE_STOP_LIMIT` | 4 | Stop limit order |

### TimeInForce

| Value | Number | Description |
|-------|--------|-------------|
| `TIME_IN_FORCE_UNSPECIFIED` | 0 | Invalid/unknown TIF |
| `TIME_IN_FORCE_GTC` | 1 | Good til cancelled |
| `TIME_IN_FORCE_IOC` | 2 | Immediate or cancel |
| `TIME_IN_FORCE_FOK` | 3 | Fill or kill |
| `TIME_IN_FORCE_GTD` | 4 | Good til date |

### OrderStatus

| Value | Number | Description |
|-------|--------|-------------|
| `ORDER_STATUS_UNSPECIFIED` | 0 | Invalid/unknown status |
| `ORDER_STATUS_PENDING` | 1 | Awaiting processing |
| `ORDER_STATUS_ACCEPTED` | 2 | Accepted by engine |
| `ORDER_STATUS_REJECTED` | 3 | Rejected (risk/validation) |
| `ORDER_STATUS_PARTIALLY_FILLED` | 4 | Partially executed |
| `ORDER_STATUS_FILLED` | 5 | Fully executed |
| `ORDER_STATUS_CANCELLED` | 6 | Cancelled by user/system |
| `ORDER_STATUS_EXPIRED` | 7 | Expired (GTD orders) |

### RiskDecision

| Value | Number | Description |
|-------|--------|-------------|
| `RISK_DECISION_UNSPECIFIED` | 0 | Invalid/unknown decision |
| `RISK_DECISION_ALLOW` | 1 | Order allowed to proceed |
| `RISK_DECISION_FLAG` | 2 | Order flagged for review |
| `RISK_DECISION_BLOCK` | 3 | Order blocked by risk system |
| `RISK_DECISION_ADJUST_LIMIT` | 4 | Order size adjusted due to limits |

## Error Codes

| Code | HTTP Mapping | Description |
|------|--------------|-------------|
| `INVALID_ARGUMENT` | 400 | Invalid request parameters |
| `NOT_FOUND` | 404 | Order/account not found |
| `ALREADY_EXISTS` | 409 | Duplicate order ID |
| `RESOURCE_EXHAUSTED` | 429 | Rate limit exceeded |
| `FAILED_PRECONDITION` | 400 | Circuit breaker open / market closed |
| `INTERNAL` | 500 | Internal server error |

## Authentication

All gRPC requests must include authentication metadata:

```
Authorization: Bearer <JWT_TOKEN>
X-Client-ID: <CLIENT_ID>
X-Request-ID: <UNIQUE_REQUEST_ID>
```

## Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| SubmitOrder | 1000 req/s | per account |
| CancelOrder | 5000 req/s | per account |
| GetOrderBook | 100 req/s | per IP |
| StreamTrades | 10 streams | per account |

## Performance Characteristics

- **p50 Latency**: <500μs
- **p99 Latency**: <1ms
- **Throughput**: >100k TPS
- **Availability**: 99.99%

## Fixed-Point Arithmetic

All monetary values use fixed-point arithmetic with 8 decimal places:

```
Price: 1234567890 = $123.45678900
Quantity: 100000000 = 1.00000000
```

This ensures deterministic calculations and avoids floating-point precision issues.

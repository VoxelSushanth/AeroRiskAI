package event

import "time"

type Event struct {
ID        uint64    `json:"id"`
Type      EventType `json:"type"`
Timestamp time.Time `json:"timestamp"`
Payload   []byte    `json:"payload"`
}

func NewEvent(id uint64, t EventType, payload []byte) *Event {
return &Event{
ID:        id,
Type:      t,
Timestamp: time.Now(),
Payload:   payload,
}
}

type OrderEvent struct {
OrderID   string `json:"order_id"`
AccountID string `json:"account_id"`
Symbol    string `json:"symbol"`
Side      string `json:"side"`
Price     int64  `json:"price"`
Quantity  int64  `json:"quantity"`
Timestamp int64  `json:"timestamp"`
}

type TradeEvent struct {
TradeID    string `json:"trade_id"`
OrderID    string `json:"order_id"`
MatchID    string `json:"match_id"`
Symbol     string `json:"symbol"`
Price      int64  `json:"price"`
Quantity   int64  `json:"quantity"`
BuyerID    string `json:"buyer_id"`
SellerID   string `json:"seller_id"`
Timestamp  int64  `json:"timestamp"`
}

type RiskEvent struct {
EventID      string `json:"event_id"`
AccountID    string `json:"account_id"`
OrderID      string `json:"order_id,omitempty"`
Decision     string `json:"decision"`
RiskScore    float64 `json:"risk_score"`
Reason       string `json:"reason"`
CircuitBreak bool   `json:"circuit_break"`
Timestamp    int64  `json:"timestamp"`
}

type AuditEvent struct {
EventID   string `json:"event_id"`
UserID    string `json:"user_id"`
Action    string `json:"action"`
Resource  string `json:"resource"`
Details   string `json:"details,omitempty"`
Timestamp int64  `json:"timestamp"`
}

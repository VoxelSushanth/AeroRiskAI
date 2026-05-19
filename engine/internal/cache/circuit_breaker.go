package cache

import (
"context"
"encoding/json"
"time"
)

type CircuitBreakState int

const (
CircuitBreakClosed CircuitBreakState = iota
CircuitBreakOpen
CircuitBreakHalfOpen
)

func (s CircuitBreakState) String() string {
switch s {
case CircuitBreakClosed:
return "closed"
case CircuitBreakOpen:
return "open"
case CircuitBreakHalfOpen:
return "half_open"
default:
return "unknown"
}
}

type CircuitBreaker struct {
AccountID     string            `json:"account_id"`
State         CircuitBreakState `json:"state"`
FailureCount  int64             `json:"failure_count"`
LastFailure   int64             `json:"last_failure"`
OpenedAt      int64             `json:"opened_at,omitempty"`
Reason        string            `json:"reason,omitempty"`
RiskScore     float64           `json:"risk_score"`
Threshold     float64           `json:"threshold"`
CooldownMs    int64             `json:"cooldown_ms"`
LastUpdated   int64             `json:"last_updated"`
}

func NewCircuitBreaker(accountID string, threshold float64, cooldownMs int64) *CircuitBreaker {
return &CircuitBreaker{
AccountID:    accountID,
State:        CircuitBreakClosed,
FailureCount: 0,
Threshold:    threshold,
CooldownMs:   cooldownMs,
RiskScore:    0.0,
LastUpdated:  time.Now().UnixNano(),
}
}

func (cb *CircuitBreaker) IsOpen() bool {
if cb.State == CircuitBreakClosed {
return false
}

if cb.State == CircuitBreakOpen && cb.CooldownMs > 0 {
now := time.Now().UnixMilli()
if now-cb.OpenedAt >= cb.CooldownMs {
cb.State = CircuitBreakHalfOpen
return false
}
}

return cb.State == CircuitBreakOpen
}

func (cb *CircuitBreaker) RecordSuccess() {
cb.FailureCount = 0
cb.State = CircuitBreakClosed
cb.LastUpdated = time.Now().UnixNano()
}

func (cb *CircuitBreaker) RecordFailure(reason string, riskScore float64) {
cb.FailureCount++
cb.LastFailure = time.Now().UnixNano()
cb.RiskScore = riskScore
cb.Reason = reason

if cb.RiskScore >= cb.Threshold {
cb.State = CircuitBreakOpen
cb.OpenedAt = time.Now().UnixMilli()
}

cb.LastUpdated = time.Now().UnixNano()
}

func (cb *CircuitBreaker) Marshal() ([]byte, error) {
return json.Marshal(cb)
}

func UnmarshalCircuitBreaker(data []byte) (*CircuitBreaker, error) {
var cb CircuitBreaker
err := json.Unmarshal(data, &cb)
return &cb, err
}

type CircuitBreakerManager struct {
client *RedisClient
}

func NewCircuitBreakerManager(client *RedisClient) *CircuitBreakerManager {
return &CircuitBreakerManager{
client: client,
}
}

func (m *CircuitBreakerManager) Get(ctx context.Context, accountID string) (*CircuitBreaker, error) {
key := CircuitBreakKey(accountID)
data, err := m.client.Get(ctx, key)
if err != nil {
return nil, err
}
if data == nil {
return NewCircuitBreaker(accountID, 0.8, 60000), nil
}
return UnmarshalCircuitBreaker(data)
}

func (m *CircuitBreakerManager) Set(ctx context.Context, cb *CircuitBreaker, expiration time.Duration) error {
key := CircuitBreakKey(cb.AccountID)
data, err := cb.Marshal()
if err != nil {
return err
}
cb.LastUpdated = time.Now().UnixNano()
return m.client.Set(ctx, key, data, expiration)
}

func (m *CircuitBreakerManager) IsBlocked(ctx context.Context, accountID string) (bool, error) {
cb, err := m.Get(ctx, accountID)
if err != nil {
return false, err
}
return cb.IsOpen(), nil
}

func (m *CircuitBreakerManager) RecordRiskDecision(ctx context.Context, accountID string, allowed bool, riskScore float64, reason string) error {
cb, err := m.Get(ctx, accountID)
if err != nil {
return err
}

if allowed {
cb.RecordSuccess()
} else {
cb.RecordFailure(reason, riskScore)
}

return m.Set(ctx, cb, 24*time.Hour)
}

const (
DefaultRiskThreshold  = 0.8
DefaultCooldownMs     = 60000
DefaultExpiration     = 24 * time.Hour
)

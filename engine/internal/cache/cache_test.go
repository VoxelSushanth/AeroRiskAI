package cache

import (
"context"
"testing"
"time"
)

func TestAccountStateReserve(t *testing.T) {
state := NewAccountState("acc-123")
state.AvailableCash = 10000

if !state.ReserveForOrder("order-1", 5000) {
t.Error("expected reservation to succeed")
}

if state.ReserveForOrder("order-2", 6000) {
t.Error("expected reservation to fail - insufficient funds")
}

if state.AvailableCash != 5000 {
t.Errorf("expected available cash 5000, got %d", state.AvailableCash)
}
}

func TestAccountStateRelease(t *testing.T) {
state := NewAccountState("acc-123")
state.AvailableCash = 10000
state.ReserveForOrder("order-1", 5000)

state.ReleaseOrderReservation("order-1")

if state.AvailableCash != 10000 {
t.Errorf("expected available cash 10000 after release, got %d", state.AvailableCash)
}

if _, ok := state.PendingOrders["order-1"]; ok {
t.Error("expected order to be removed from pending")
}
}

func TestCircuitBreakerStateTransitions(t *testing.T) {
cb := NewCircuitBreaker("acc-123", 0.8, 60000)

if cb.IsOpen() {
t.Error("expected circuit breaker to start closed")
}

cb.RecordFailure("high_risk", 0.9)

if cb.State != CircuitBreakOpen {
t.Errorf("expected state open after high risk failure, got %v", cb.State)
}

if !cb.IsOpen() {
t.Error("expected circuit breaker to be open")
}
}

func TestCircuitBreakerCooldown(t *testing.T) {
cb := NewCircuitBreaker("acc-123", 0.8, 1)
cb.RecordFailure("high_risk", 0.9)

if !cb.IsOpen() {
t.Error("expected circuit breaker to be open initially")
}

time.Sleep(5 * time.Millisecond)

if cb.IsOpen() {
t.Error("expected circuit breaker to transition to half-open after cooldown")
}

if cb.State != CircuitBreakHalfOpen {
t.Errorf("expected state half_open, got %v", cb.State)
}
}

func TestCircuitBreakerRecovery(t *testing.T) {
cb := NewCircuitBreaker("acc-123", 0.8, 1)
cb.RecordFailure("high_risk", 0.9)
time.Sleep(5 * time.Millisecond)

cb.RecordSuccess()

if cb.State != CircuitBreakClosed {
t.Errorf("expected state closed after success, got %v", cb.State)
}

if cb.FailureCount != 0 {
t.Errorf("expected failure count 0, got %d", cb.FailureCount)
}
}

func TestKeyGeneration(t *testing.T) {
tests := []struct {
name     string
generate func() string
expected string
}{
{"account key", func() string { return AccountKey("acc-123") }, "acct:acc-123"},
{"circuit break key", func() string { return CircuitBreakKey("acc-123") }, "cb:acc-123"},
{"order key", func() string { return OrderKey("ord-456") }, "ord:ord-456"},
{"position key", func() string { return PositionKey("acc-123", "AAPL") }, "pos:acc-123:AAPL"},
}

for _, tt := range tests {
t.Run(tt.name, func(t *testing.T) {
if got := tt.generate(); got != tt.expected {
t.Errorf("expected %s, got %s", tt.expected, got)
}
})
}
}

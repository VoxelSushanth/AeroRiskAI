package cache

import (
"context"
"encoding/json"
"time"
)

type AccountState struct {
AccountID       string            `json:"account_id"`
CashBalance     int64             `json:"cash_balance"` // Fixed-point: cents
AvailableCash   int64             `json:"available_cash"`
PendingOrders   map[string]int64  `json:"pending_orders"` // order_id -> reserved amount
Positions       map[string]int64  `json:"positions"`      // symbol -> quantity
RiskLevel       string            `json:"risk_level"`
CircuitBroken   bool              `json:"circuit_broken"`
LastUpdated     int64             `json:"last_updated"`
}

func NewAccountState(accountID string) *AccountState {
return &AccountState{
AccountID:     accountID,
CashBalance:   0,
AvailableCash: 0,
PendingOrders: make(map[string]int64),
Positions:     make(map[string]int64),
RiskLevel:     "normal",
CircuitBroken: false,
LastUpdated:   time.Now().UnixNano(),
}
}

func (a *AccountState) ReserveForOrder(orderID string, amount int64) bool {
if amount > a.AvailableCash {
return false
}
a.AvailableCash -= amount
a.PendingOrders[orderID] = amount
return true
}

func (a *AccountState) ReleaseOrderReservation(orderID string) {
if amount, ok := a.PendingOrders[orderID]; ok {
a.AvailableCash += amount
delete(a.PendingOrders, orderID)
}
}

func (a *AccountState) UpdatePosition(symbol string, quantity int64) {
current := a.Positions[symbol]
a.Positions[symbol] = current + quantity
}

func (a *AccountState) Marshal() ([]byte, error) {
return json.Marshal(a)
}

func UnmarshalAccountState(data []byte) (*AccountState, error) {
var state AccountState
err := json.Unmarshal(data, &state)
return &state, err
}

type AccountStateManager struct {
client *RedisClient
}

func NewAccountStateManager(client *RedisClient) *AccountStateManager {
return &AccountStateManager{
client: client,
}
}

func (m *AccountStateManager) Get(ctx context.Context, accountID string) (*AccountState, error) {
key := AccountKey(accountID)
data, err := m.client.Get(ctx, key)
if err != nil {
return nil, err
}
if data == nil {
return NewAccountState(accountID), nil
}
return UnmarshalAccountState(data)
}

func (m *AccountStateManager) Set(ctx context.Context, state *AccountState, expiration time.Duration) error {
key := AccountKey(state.AccountID)
data, err := state.Marshal()
if err != nil {
return err
}
state.LastUpdated = time.Now().UnixNano()
return m.client.Set(ctx, key, data, expiration)
}

func (m *AccountStateManager) UpdateCash(ctx context.Context, accountID string, delta int64) error {
state, err := m.Get(ctx, accountID)
if err != nil {
return err
}
state.CashBalance += delta
state.AvailableCash += delta
return m.Set(ctx, state, 24*time.Hour)
}

package publisher

import (
"testing"
"time"

"github.com/aerorisk/engine/pkg/event"
)

func TestTopics(t *testing.T) {
topics := NewTopics()
if topics.Orders != TopicOrders {
t.Errorf("expected Orders topic %s, got %s", TopicOrders, topics.Orders)
}
if topics.Trades != TopicTrades {
t.Errorf("expected Trades topic %s, got %s", TopicTrades, topics.Trades)
}
if topics.RiskDecisions != TopicRiskDecision {
t.Errorf("expected RiskDecisions topic %s, got %s", TopicRiskDecision, topics.RiskDecisions)
}
if topics.AuditLog != TopicAuditLog {
t.Errorf("expected AuditLog topic %s, got %s", TopicAuditLog, topics.AuditLog)
}
}

func TestKafkaPublisherCreation(t *testing.T) {
t.Skip("requires kafka broker")
pub, err := NewKafkaPublisher([]string{"localhost:9092"})
if err != nil {
t.Fatalf("failed to create publisher: %v", err)
}
defer pub.Close()
}

func TestOrderEventPublish(t *testing.T) {
t.Skip("requires kafka broker")
pub, err := NewKafkaPublisher([]string{"localhost:9092"})
if err != nil {
t.Fatalf("failed to create publisher: %v", err)
}
defer pub.Close()

evt := &event.OrderEvent{
OrderID:   "order-123",
AccountID: "acc-456",
Symbol:    "AAPL",
Side:      "BUY",
Price:     15000,
Quantity:  100,
Timestamp: time.Now().UnixNano(),
}

err = pub.PublishOrderEvent(evt)
if err != nil {
t.Errorf("failed to publish order event: %v", err)
}
}

package publisher

import (
"context"
"encoding/json"
"fmt"
"time"

"github.com/IBM/sarama"
"github.com/aerorisk-ai/engine/pkg/event"
)

type KafkaPublisher struct {
producer sarama.AsyncProducer
topics   *Topics
}

func NewKafkaPublisher(brokers []string) (*KafkaPublisher, error) {
config := sarama.NewConfig()
config.Producer.Return.Successes = true
config.Producer.Return.Errors = true
config.Producer.RequiredAcks = sarama.WaitForLocal
config.Producer.Timeout = 5 * time.Second
config.Net.DialTimeout = 10 * time.Second
config.Net.WriteTimeout = 10 * time.Second
config.Net.ReadTimeout = 10 * time.Second
config.Metadata.Full = true
config.Metadata.Retry.Max = 3
config.Metadata.Retry.Backoff = 500 * time.Millisecond
config.ClientID = "aerorisk-engine"

producer, err := sarama.NewAsyncProducer(brokers, config)
if err != nil {
return nil, fmt.Errorf("failed to create kafka producer: %w", err)
}

go func() {
for range producer.Successes() {
// Track successful publishes if needed
}
}()

go func() {
for err := range producer.Errors() {
fmt.Printf("kafka publish error: %v\n", err)
}
}()

return &KafkaPublisher{
producer: producer,
topics:   NewTopics(),
}, nil
}

func (p *KafkaPublisher) PublishOrderEvent(evt *event.OrderEvent) error {
data, err := json.Marshal(evt)
if err != nil {
return fmt.Errorf("failed to marshal event: %w", err)
}

msg := &sarama.ProducerMessage{
Topic:     p.topics.Orders,
Key:       sarama.StringEncoder(evt.OrderID),
Value:     sarama.ByteEncoder(data),
Timestamp: time.Now().UTC(),
}

p.producer.Input() <- msg
return nil
}

func (p *KafkaPublisher) PublishTradeEvent(evt *event.TradeEvent) error {
data, err := json.Marshal(evt)
if err != nil {
return fmt.Errorf("failed to marshal event: %w", err)
}

msg := &sarama.ProducerMessage{
Topic:     p.topics.Trades,
Key:       sarama.StringEncoder(evt.TradeID),
Value:     sarama.ByteEncoder(data),
Timestamp: time.Now().UTC(),
}

p.producer.Input() <- msg
return nil
}

func (p *KafkaPublisher) PublishRiskEvent(evt *event.RiskEvent) error {
data, err := json.Marshal(evt)
if err != nil {
return fmt.Errorf("failed to marshal event: %w", err)
}

msg := &sarama.ProducerMessage{
Topic:     p.topics.RiskDecisions,
Key:       sarama.StringEncoder(evt.AccountID),
Value:     sarama.ByteEncoder(data),
Timestamp: time.Now().UTC(),
}

p.producer.Input() <- msg
return nil
}

func (p *KafkaPublisher) PublishAuditEvent(evt *event.AuditEvent) error {
data, err := json.Marshal(evt)
if err != nil {
return fmt.Errorf("failed to marshal event: %w", err)
}

msg := &sarama.ProducerMessage{
Topic:     p.topics.AuditLog,
Key:       sarama.StringEncoder(evt.EventID),
Value:     sarama.ByteEncoder(data),
Timestamp: time.Now().UTC(),
}

p.producer.Input() <- msg
return nil
}

func (p *KafkaPublisher) Close() error {
p.producer.AsyncClose()
return nil
}

func (p *KafkaPublisher) GetTopics() *Topics {
return p.topics
}

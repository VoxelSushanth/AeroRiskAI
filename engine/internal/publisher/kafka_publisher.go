package publisher

import (
	"context"
	"encoding/json"
	"fmt"

	"github.com/twmb/franz-go/pkg/kgo"
	"github.com/aerorisk/engine/pkg/event"
)

type KafkaPublisher struct {
	client *kgo.Client
	topics *Topics
}

func NewKafkaPublisher(brokers []string) (*KafkaPublisher, error) {
	client, err := kgo.NewClient(
		kgo.SeedBrokers(brokers...),
		kgo.ProducerBatchCompression(kgo.GzipCompression()),
		kgo.AllowAutoTopicCreation(),
		kgo.ClientID("aerorisk-engine"),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create kafka client: %w", err)
	}

	return &KafkaPublisher{
		client: client,
		topics: NewTopics(),
	}, nil
}

func (p *KafkaPublisher) PublishOrderEvent(evt *event.OrderEvent) error {
	data, err := json.Marshal(evt)
	if err != nil {
		return fmt.Errorf("failed to marshal event: %w", err)
	}

	record := &kgo.Record{
		Key:   []byte(evt.OrderID),
		Value: data,
		Topic: p.topics.Orders,
	}

	return p.client.ProduceSync(context.Background(), record).FirstErr()
}

func (p *KafkaPublisher) PublishTradeEvent(evt *event.TradeEvent) error {
	data, err := json.Marshal(evt)
	if err != nil {
		return fmt.Errorf("failed to marshal event: %w", err)
	}

	record := &kgo.Record{
		Key:   []byte(evt.TradeID),
		Value: data,
		Topic: p.topics.Trades,
	}

	return p.client.ProduceSync(context.Background(), record).FirstErr()
}

func (p *KafkaPublisher) PublishRiskEvent(evt *event.RiskEvent) error {
	data, err := json.Marshal(evt)
	if err != nil {
		return fmt.Errorf("failed to marshal event: %w", err)
	}

	record := &kgo.Record{
		Key:   []byte(evt.AccountID),
		Value: data,
		Topic: p.topics.RiskDecisions,
	}

	return p.client.ProduceSync(context.Background(), record).FirstErr()
}

func (p *KafkaPublisher) PublishAuditEvent(evt *event.AuditEvent) error {
	data, err := json.Marshal(evt)
	if err != nil {
		return fmt.Errorf("failed to marshal event: %w", err)
	}

	record := &kgo.Record{
		Key:   []byte(evt.EventID),
		Value: data,
		Topic: p.topics.AuditLog,
	}

	return p.client.ProduceSync(context.Background(), record).FirstErr()
}

func (p *KafkaPublisher) Close() error {
	p.client.Close()
	return nil
}

func (p *KafkaPublisher) GetTopics() *Topics {
	return p.topics
}

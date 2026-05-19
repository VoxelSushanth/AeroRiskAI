package publisher

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/twmb/franz-go/pkg/kgo"
	"github.com/twmb/franz-go/pkg/kmsg"
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

	msg := kmsg.Record{
		Key:   []byte(evt.OrderID),
		Value: data,
		Time:  time.Now().UTC(),
	}

	return p.client.Produce(context.Background(), p.topics.Orders, &msg)
}

func (p *KafkaPublisher) PublishTradeEvent(evt *event.TradeEvent) error {
	data, err := json.Marshal(evt)
	if err != nil {
		return fmt.Errorf("failed to marshal event: %w", err)
	}

	msg := kmsg.Record{
		Key:   []byte(evt.TradeID),
		Value: data,
		Time:  time.Now().UTC(),
	}

	return p.client.Produce(context.Background(), p.topics.Trades, &msg)
}

func (p *KafkaPublisher) PublishRiskEvent(evt *event.RiskEvent) error {
	data, err := json.Marshal(evt)
	if err != nil {
		return fmt.Errorf("failed to marshal event: %w", err)
	}

	msg := kmsg.Record{
		Key:   []byte(evt.AccountID),
		Value: data,
		Time:  time.Now().UTC(),
	}

	return p.client.Produce(context.Background(), p.topics.RiskDecisions, &msg)
}

func (p *KafkaPublisher) PublishAuditEvent(evt *event.AuditEvent) error {
	data, err := json.Marshal(evt)
	if err != nil {
		return fmt.Errorf("failed to marshal event: %w", err)
	}

	msg := kmsg.Record{
		Key:   []byte(evt.EventID),
		Value: data,
		Time:  time.Now().UTC(),
	}

	return p.client.Produce(context.Background(), p.topics.AuditLog, &msg)
}

func (p *KafkaPublisher) Close() error {
	p.client.Close()
	return nil
}

func (p *KafkaPublisher) GetTopics() *Topics {
	return p.topics
}

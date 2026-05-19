package main

import (
	"context"
	"log"
	"os"
	"os/signal"
	"syscall"

	"github.com/aerorisk/engine/internal/disruptor"
	"github.com/aerorisk/engine/internal/ledger"
	"github.com/aerorisk/engine/internal/metrics"
	"github.com/aerorisk/engine/internal/orderbook"
	"github.com/aerorisk/engine/internal/publisher"
	"github.com/aerorisk/engine/pkg/event"
)

func main() {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// Initialize metrics
	metrics.Init()

	// Initialize Kafka publisher
	kafkaBrokers := getEnv("KAFKA_BROKERS", "localhost:9092")
	pub, err := publisher.NewKafkaPublisher([]string{kafkaBrokers})
	if err != nil {
		log.Fatalf("failed to create kafka publisher: %v", err)
	}
	defer pub.Close()

	// Initialize Redis client for circuit breakers and account state
	redisAddr := getEnv("REDIS_ADDR", "localhost:6379")
	// cacheClient := cache.NewRedisClient(redisAddr)

	// Initialize LMAX Disruptor ring buffer
	bufferSize := 1 << 20 // 1M slots
	ringBuffer := disruptor.NewRingBuffer(bufferSize)
	sequencer := disruptor.NewSequencer()
	waitStrategy := disruptor.NewBlockingWaitStrategy()

	// Initialize matching engine
	matchingEngine := orderbook.NewMatchingEngine(ringBuffer, pub)

	// Initialize ledger
	ledgerEngine := ledger.NewLedger(pub)

	// Start batch processor
	batchProcessor := disruptor.NewBatchProcessor(
		ringBuffer,
		sequencer,
		waitStrategy,
		matchingEngine.ProcessBatch,
	)

	// Start consumer goroutine
	go func() {
		log.Printf("engine started with buffer size %d", bufferSize)
		batchProcessor.Start(ctx)
	}()

	// Graceful shutdown
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
	<-sigCh

	log.Println("shutting down engine...")
	cancel()
	batchProcessor.Stop()
	ledgerEngine.Close()
}

func getEnv(key, defaultVal string) string {
	if val := os.Getenv(key); val != "" {
		return val
	}
	return defaultVal
}

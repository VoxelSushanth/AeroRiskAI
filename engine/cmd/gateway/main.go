package main

import (
	"context"
	"fmt"
	"log"
	"net"
	"os"
	"os/signal"
	"syscall"

	"github.com/aerorisk/engine/internal/gateway"
	"github.com/aerorisk/engine/internal/publisher"
	"google.golang.org/grpc"
)

func main() {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// Initialize Kafka publisher
	kafkaBrokers := getEnv("KAFKA_BROKERS", "localhost:9092")
	pub, err := publisher.NewKafkaPublisher([]string{kafkaBrokers})
	if err != nil {
		log.Fatalf("failed to create kafka publisher: %v", err)
	}
	defer pub.Close()

	// Start gRPC server
	lis, err := net.Listen("tcp", ":50051")
	if err != nil {
		log.Fatalf("failed to listen: %v", err)
	}

	grpcServer := grpc.NewServer(
		grpc.MaxConcurrentStreams(10000),
		grpc.InitialWindowSize(1<<30),
		grpc.InitialConnWindowSize(1<<30),
	)

	// Register gateway service
	gatewaySvc := gateway.NewGRPCServer(pub)
	// Note: Register service once proto is compiled
	// pb.RegisterAeroRiskServiceServer(grpcServer, gatewaySvc)

	go func() {
		log.Printf("gateway listening on :50051")
		if err := grpcServer.Serve(lis); err != nil {
			log.Printf("server error: %v", err)
		}
	}()

	// Start WebSocket server
	wsServer := gateway.NewWSServer(":8080", pub)
	go func() {
		log.Printf("websocket listening on :8080")
		if err := wsServer.Start(); err != nil {
			log.Printf("ws server error: %v", err)
		}
	}()

	// Graceful shutdown
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
	<-sigCh

	log.Println("shutting down gateway...")
	cancel()
	grpcServer.GracefulStop()
	wsServer.Stop()
}

func getEnv(key, defaultVal string) string {
	if val := os.Getenv(key); val != "" {
		return val
	}
	return defaultVal
}

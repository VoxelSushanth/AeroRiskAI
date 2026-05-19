# Dockerfile for Go Engine
FROM golang:1.21-alpine AS builder

WORKDIR /app

# Install dependencies
RUN apk add --no-cache git ca-certificates

# Copy go mod files
COPY engine/go.mod engine/go.sum ./
RUN go mod download

# Copy source code
COPY engine/ ./

# Build the gateway
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o gateway ./cmd/gateway

# Build the engine
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o engine ./cmd/engine

# Build the admin service
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o admin ./cmd/admin

# Final stage
FROM alpine:latest

RUN apk --no-cache add ca-certificates tzdata

WORKDIR /root/

# Copy binaries from builder
COPY --from=builder /app/gateway .
COPY --from=builder /app/engine .
COPY --from=builder /app/admin .

# Copy configuration if needed
# COPY config/ ./config/

EXPOSE 8080 8081 9090 8082

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:8081/health || exit 1

# Run gateway by default, can be overridden
CMD ["./gateway"]

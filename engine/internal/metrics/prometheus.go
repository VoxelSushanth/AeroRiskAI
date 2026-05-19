package metrics

import (
"github.com/prometheus/client_golang/prometheus"
"github.com/prometheus/client_golang/prometheus/promauto"
)

var (
// Order metrics
OrdersReceived = promauto.NewCounterVec(
prometheus.CounterOpts{
Name: "aerorisk_orders_received_total",
Help: "Total number of orders received",
},
[]string{"symbol", "side"},
)

OrdersProcessed = promauto.NewCounterVec(
prometheus.CounterOpts{
Name: "aerorisk_orders_processed_total",
Help: "Total number of orders processed",
},
[]string{"symbol", "status"},
)

// Trade metrics
TradesExecuted = promauto.NewCounterVec(
prometheus.CounterOpts{
Name: "aerorisk_trades_executed_total",
Help: "Total number of trades executed",
},
[]string{"symbol"},
)

TradeVolume = promauto.NewCounterVec(
prometheus.CounterOpts{
Name: "aerorisk_trade_volume_total",
Help: "Total trade volume",
},
[]string{"symbol"},
)

// Latency metrics
OrderLatency = promauto.NewHistogramVec(
prometheus.HistogramOpts{
Name:    "aerorisk_order_latency_ms",
Help:    "Order processing latency in milliseconds",
Buckets: []float64{0.1, 0.25, 0.5, 1, 2.5, 5, 10},
},
[]string{"operation"},
)

MatchLatency = promauto.NewHistogramVec(
prometheus.HistogramOpts{
Name:    "aerorisk_match_latency_ms",
Help:    "Matching engine latency in milliseconds",
Buckets: []float64{0.05, 0.1, 0.25, 0.5, 1, 2.5},
},
[]string{"symbol"},
)

// Risk metrics
RiskDecisions = promauto.NewCounterVec(
prometheus.CounterOpts{
Name: "aerorisk_risk_decisions_total",
Help: "Total risk decisions by type",
},
[]string{"decision"},
)

CircuitBreaks = promauto.NewCounterVec(
prometheus.CounterOpts{
Name: "aerorisk_circuit_breaks_total",
Help: "Total circuit breaker triggers",
},
[]string{"account_id", "reason"},
)

// System metrics
BufferUtilization = promauto.NewGauge(
prometheus.GaugeOpts{
Name: "aerorisk_buffer_utilization",
Help: "Ring buffer utilization percentage",
},
)

ActiveConnections = promauto.NewGauge(
prometheus.GaugeOpts{
Name: "aerorisk_active_connections",
Help: "Number of active WebSocket connections",
},
)

// Error metrics
Errors = promauto.NewCounterVec(
prometheus.CounterOpts{
Name: "aerorisk_errors_total",
Help: "Total errors by type",
},
[]string{"type", "component"},
)
)

func Init() {
// Metrics are auto-registered with Prometheus
// This function can be used for additional setup if needed
}

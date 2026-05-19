"""
AeroRisk AI - Observability Module
Metrics, tracing, and logging configuration
"""

from aerorisk.observability.metrics import (
    ObservabilitySetup,
    get_observability,
    get_metrics_handler,
    timed_agent,
    timed_operation,
    TRANSACTIONS_PROCESSED,
    TRANSACTION_LATENCY,
    AI_PIPELINE_LATENCY,
    AGENT_EXECUTION_COUNT,
    AGENT_LATENCY,
    RISK_SCORE_GAUGE,
    CIRCUIT_BREAKER_STATE,
    VECTOR_SEARCH_LATENCY,
    VECTOR_SEARCH_RESULTS,
    ERRORS_TOTAL,
    SANCTIONS_MATCHES,
    FRAUD_DETECTED
)

from aerorisk.observability.tracing import (
    TracingSetup,
    get_tracer,
    init_tracing,
    shutdown_tracing
)

__all__ = [
    # Metrics
    "ObservabilitySetup",
    "get_observability",
    "get_metrics_handler",
    "timed_agent",
    "timed_operation",
    "TRANSACTIONS_PROCESSED",
    "TRANSACTION_LATENCY",
    "AI_PIPELINE_LATENCY",
    "AGENT_EXECUTION_COUNT",
    "AGENT_LATENCY",
    "RISK_SCORE_GAUGE",
    "CIRCUIT_BREAKER_STATE",
    "VECTOR_SEARCH_LATENCY",
    "VECTOR_SEARCH_RESULTS",
    "ERRORS_TOTAL",
    "SANCTIONS_MATCHES",
    "FRAUD_DETECTED",
    # Tracing
    "TracingSetup",
    "get_tracer",
    "init_tracing",
    "shutdown_tracing"
]

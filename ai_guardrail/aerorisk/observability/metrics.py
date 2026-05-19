"""
AeroRisk AI - Observability Module
Metrics and distributed tracing with OpenTelemetry
"""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
import time
from typing import Optional, Dict, Any
from contextlib import contextmanager

from aerorisk.config.settings import settings


# ============================================================================
# Prometheus Metrics
# ============================================================================

# Transaction processing metrics
TRANSACTIONS_PROCESSED = Counter(
    'aerorisk_transactions_processed_total',
    'Total number of transactions processed',
    ['decision_type', 'risk_level']
)

TRANSACTION_LATENCY = Histogram(
    'aerorisk_transaction_latency_seconds',
    'Transaction processing latency in seconds',
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

AI_PIPELINE_LATENCY = Histogram(
    'aerorisk_ai_pipeline_latency_seconds',
    'AI pipeline processing latency in seconds',
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

# Agent-specific metrics
AGENT_EXECUTION_COUNT = Counter(
    'aerorisk_agent_executions_total',
    'Total agent executions',
    ['agent_name', 'status']
)

AGENT_LATENCY = Histogram(
    'aerorisk_agent_latency_seconds',
    'Agent execution latency',
    ['agent_name'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

# Risk metrics
RISK_SCORE_GAUGE = Gauge(
    'aerorisk_risk_score',
    'Current risk score for accounts',
    ['account_id']
)

CIRCUIT_BREAKER_STATE = Gauge(
    'aerorisk_circuit_breaker_state',
    'Circuit breaker state (0=closed, 1=open)',
    ['account_id', 'breaker_type']
)

# Vector search metrics
VECTOR_SEARCH_LATENCY = Histogram(
    'aerorisk_vector_search_latency_seconds',
    'Vector search latency',
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1]
)

VECTOR_SEARCH_RESULTS = Histogram(
    'aerorisk_vector_search_results_count',
    'Number of results from vector search',
    buckets=[1, 2, 5, 10, 20, 50, 100]
)

# Error metrics
ERRORS_TOTAL = Counter(
    'aerorisk_errors_total',
    'Total errors by type',
    ['error_type', 'component']
)

SANCTIONS_MATCHES = Counter(
    'aerorisk_sanctions_matches_total',
    'Total sanctions matches'
)

FRAUD_DETECTED = Counter(
    'aerorisk_fraud_detected_total',
    'Total fraud detections by type',
    ['fraud_type']
)


# ============================================================================
# OpenTelemetry Tracing
# ============================================================================

class ObservabilitySetup:
    """
    Initialize and configure observability stack.
    
    Sets up:
    - OpenTelemetry tracing with OTLP exporter
    - Instrumentation for async HTTP, Redis, PostgreSQL
    - Prometheus metrics endpoints
    """
    
    def __init__(self):
        self.tracer_provider: Optional[TracerProvider] = None
        self.tracer: Optional[trace.Tracer] = None
        self._initialized = False
    
    def initialize(self):
        """Initialize tracing and instrumentation."""
        if self._initialized:
            return
        
        # Configure tracer provider
        self.tracer_provider = TracerProvider(
            service_name="aerorisk-ai-guardrail",
            resource_attributes={
                "service.version": settings.service_version,
                "deployment.environment": settings.environment
            }
        )
        
        # Add OTLP exporter if Jaeger/Tempo endpoint configured
        if settings.otel_exporter_endpoint:
            otlp_exporter = OTLPSpanExporter(
                endpoint=settings.otel_exporter_endpoint
            )
            span_processor = BatchSpanProcessor(otlp_exporter)
            self.tracer_provider.add_span_processor(span_processor)
        
        # Set global tracer provider
        trace.set_tracer_provider(self.tracer_provider)
        
        # Get tracer instance
        self.tracer = trace.get_tracer("aerorisk.ai.pipeline")
        
        # Instrument external libraries
        self._instrument_libraries()
        
        self._initialized = True
    
    def _instrument_libraries(self):
        """Enable auto-instrumentation for common libraries."""
        try:
            AioHttpClientInstrumentor().instrument()
        except Exception:
            pass
        
        try:
            RedisInstrumentor().instrument()
        except Exception:
            pass
        
        try:
            Psycopg2Instrumentor().instrument()
        except Exception:
            pass
    
    @contextmanager
    def trace_block(self, operation_name: str, attributes: Optional[Dict[str, Any]] = None):
        """
        Context manager for creating spans.
        
        Usage:
            with observability.trace_block("process_transaction", {"account_id": "123"}):
                # do work
                pass
        """
        if not self._initialized or not self.tracer:
            yield
            return
        
        with self.tracer.start_as_current_span(operation_name) as span:
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, value)
            
            try:
                yield span
            except Exception as e:
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                raise
    
    def record_metric_latency(
        self,
        metric: Histogram,
        start_time: float,
        labels: Optional[Dict[str, str]] = None
    ):
        """Record latency metric."""
        duration = time.time() - start_time
        if labels:
            metric.labels(**labels).observe(duration)
        else:
            metric.observe(duration)
    
    def increment_counter(
        self,
        counter: Counter,
        labels: Optional[Dict[str, str]] = None
    ):
        """Increment counter metric."""
        if labels:
            counter.labels(**labels).inc()
        else:
            counter.inc()
    
    def set_gauge(
        self,
        gauge: Gauge,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ):
        """Set gauge value."""
        if labels:
            gauge.labels(**labels).set(value)
        else:
            gauge.set(value)


# Global observability instance
observability = ObservabilitySetup()


def get_observability() -> ObservabilitySetup:
    """Get global observability instance."""
    if not observability._initialized:
        observability.initialize()
    return observability


def get_metrics_handler():
    """
    FastAPI/Flask handler for Prometheus metrics endpoint.
    
    Usage in FastAPI:
        @app.get("/metrics")
        def metrics():
            return Response(get_metrics_handler(), media_type=CONTENT_TYPE_LATEST)
    """
    return generate_latest()


# ============================================================================
# Convenience decorators and context managers
# ============================================================================

def timed_agent(agent_name: str):
    """
    Decorator to time agent execution and record metrics.
    
    Usage:
        @timed_agent("anomaly_detection")
        async def analyze(self, event):
            ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            obs = get_observability()
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                obs.increment_counter(AGENT_EXECUTION_COUNT, {
                    "agent_name": agent_name,
                    "status": "success"
                })
                return result
            except Exception as e:
                obs.increment_counter(AGENT_EXECUTION_COUNT, {
                    "agent_name": agent_name,
                    "status": "error"
                })
                obs.increment_counter(ERRORS_TOTAL, {
                    "error_type": type(e).__name__,
                    "component": f"agent.{agent_name}"
                })
                raise
            finally:
                obs.record_metric_latency(AGENT_LATENCY, start_time, {
                    "agent_name": agent_name
                })
        
        wrapper.__name__ = func.__name__
        return wrapper
    return decorator


@contextmanager
def timed_operation(operation_name: str, metric: Histogram):
    """
    Context manager to time operations.
    
    Usage:
        with timed_operation("vector_search", VECTOR_SEARCH_LATENCY):
            results = await search(...)
    """
    start_time = time.time()
    try:
        yield
    finally:
        obs = get_observability()
        obs.record_metric_latency(metric, start_time)

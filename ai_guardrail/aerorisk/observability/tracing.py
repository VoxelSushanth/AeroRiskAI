"""
AeroRisk AI - Observability Module
Distributed tracing configuration and utilities
"""

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.asyncio import AsyncioInstrumentor
import logging

from aerorisk.config.settings import settings


logger = logging.getLogger(__name__)


class TracingSetup:
    """
    Configure distributed tracing for the AI pipeline.
    
    Supports multiple exporters:
    - OTLP (Jaeger, Tempo, Honeycomb)
    - Console (development)
    """
    
    def __init__(self):
        self.tracer_provider = None
        self.tracer = None
    
    def setup(self) -> trace.Tracer:
        """Initialize tracing and return tracer instance."""
        
        # Create resource with service metadata
        resource = Resource.create({
            "service.name": "aerorisk-ai-guardrail",
            "service.version": settings.service_version,
            "deployment.environment": settings.environment,
            "service.instance.id": settings.instance_id
        })
        
        # Create tracer provider
        self.tracer_provider = TracerProvider(resource=resource)
        
        # Configure exporter based on settings
        if settings.otel_exporter_endpoint:
            # Production: OTLP exporter
            exporter = OTLPSpanExporter(
                endpoint=settings.otel_exporter_endpoint,
                insecure=settings.otel_insecure
            )
            logger.info(f"Configured OTLP tracing exporter: {settings.otel_exporter_endpoint}")
        else:
            # Development: Console exporter
            exporter = ConsoleSpanExporter()
            logger.info("Configured console tracing exporter (development mode)")
        
        # Add batch span processor
        processor = BatchSpanProcessor(
            exporter,
            max_queue_size=settings.otel_max_queue_size,
            scheduled_delay_millis=settings.otel_schedule_delay_millis,
            max_export_batch_size=settings.otel_max_batch_size
        )
        
        self.tracer_provider.add_span_processor(processor)
        
        # Set as global tracer provider
        trace.set_tracer_provider(self.tracer_provider)
        
        # Get tracer instance
        self.tracer = trace.get_tracer(
            "aerorisk.ai.pipeline",
            settings.service_version
        )
        
        # Instrument asyncio
        try:
            AsyncioInstrumentor().instrument()
        except Exception as e:
            logger.warning(f"Failed to instrument asyncio: {e}")
        
        logger.info("OpenTelemetry tracing initialized successfully")
        
        return self.tracer
    
    def get_tracer(self) -> trace.Tracer:
        """Get tracer instance, initializing if needed."""
        if not self.tracer:
            self.setup()
        return self.tracer
    
    def shutdown(self):
        """Gracefully shutdown tracing."""
        if self.tracer_provider:
            self.tracer_provider.shutdown()
            logger.info("Tracing provider shut down")


# Global tracing instance
tracing_setup = TracingSetup()


def get_tracer() -> trace.Tracer:
    """Get global tracer instance."""
    return tracing_setup.get_tracer()


def init_tracing() -> trace.Tracer:
    """Initialize and return tracer."""
    return tracing_setup.setup()


def shutdown_tracing():
    """Shutdown tracing gracefully."""
    tracing_setup.shutdown()

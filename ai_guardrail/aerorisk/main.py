"""
AeroRisk AI Guardrail - Main Entry Point
Multi-agent risk orchestration service
"""

import asyncio
import signal
import logging
from typing import Optional

from fastapi import FastAPI, BackgroundTasks
from contextlib import asynccontextmanager

from aerorisk.config.settings import settings
from aerorisk.consumer.kafka_consumer import KafkaEventConsumer
from aerorisk.graph.pipeline import RiskPipeline, create_pipeline
from aerorisk.observability import (
    get_observability,
    init_tracing,
    shutdown_tracing,
    get_metrics_handler,
    TRANSACTION_LATENCY,
    TRANSACTIONS_PROCESSED,
    ERRORS_TOTAL
)
from aerorisk.storage import get_postgres_client


logger = logging.getLogger(__name__)


# Global instances
consumer: Optional[KafkaEventConsumer] = None
pipeline: Optional[RiskPipeline] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global consumer, pipeline
    
    # Startup
    logger.info("Starting AeroRisk AI Guardrail...")
    
    # Initialize observability
    if settings.tracing_enabled:
        init_tracing()
    
    if settings.metrics_enabled:
        get_observability().initialize()
    
    # Initialize pipeline
    pipeline = create_pipeline()
    logger.info("Risk pipeline initialized")
    
    # Initialize consumer
    consumer = KafkaEventConsumer(
        bootstrap_servers=settings.kafka.bootstrap_servers,
        group_id=settings.kafka.consumer_group,
        topics=[settings.kafka.order_topic]
    )
    
    # Start consumer in background
    consumer_task = asyncio.create_task(consumer.start())
    logger.info(f"Kafka consumer started on topic: {settings.kafka.order_topic}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AeroRisk AI Guardrail...")
    
    if consumer:
        await consumer.stop()
    
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass
    
    if settings.tracing_enabled:
        shutdown_tracing()
    
    logger.info("Shutdown complete")


# FastAPI application
app = FastAPI(
    title="AeroRisk AI Guardrail",
    description="Multi-agent AI risk orchestration for financial transactions",
    version=settings.service_version,
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.service_name,
        "version": settings.service_version,
        "environment": settings.environment
    }


@app.get("/ready")
async def readiness_check():
    """Readiness check - verifies dependencies."""
    ready = True
    checks = {}
    
    # Check Kafka connection
    if consumer and consumer.is_running():
        checks["kafka"] = "connected"
    else:
        checks["kafka"] = "disconnected"
        ready = False
    
    # Check Redis connection
    try:
        from aerorisk.cache import get_redis_client
        redis_client = get_redis_client()
        await redis_client.ping()
        checks["redis"] = "connected"
    except Exception as e:
        checks["redis"] = f"error: {str(e)}"
        ready = False
    
    # Check Qdrant connection
    try:
        from aerorisk.storage import get_qdrant_client
        qdrant_client = get_qdrant_client()
        qdrant_client.client.get_collections()
        checks["qdrant"] = "connected"
    except Exception as e:
        checks["qdrant"] = f"error: {str(e)}"
        ready = False
    
    # Check PostgreSQL connection
    try:
        postgres_client = get_postgres_client()
        checks["postgres"] = "connected"
    except Exception as e:
        checks["postgres"] = f"error: {str(e)}"
        ready = False
    
    return {
        "ready": ready,
        "checks": checks
    }


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    from fastapi.responses import Response
    from prometheus_client import CONTENT_TYPE_LATEST
    
    return Response(
        content=get_metrics_handler(),
        media_type=CONTENT_TYPE_LATEST
    )


@app.post("/process-event")
async def process_event_direct(event: dict, background_tasks: BackgroundTasks):
    """
    Direct event processing endpoint (for testing/sync processing).
    
    This bypasses Kafka and processes events directly through the pipeline.
    """
    from aerorisk.models.event import TransactionEvent
    
    if not pipeline:
        return {"error": "Pipeline not initialized"}
    
    try:
        # Convert dict to TransactionEvent
        transaction_event = TransactionEvent(**event)
        
        # Process through pipeline
        result = await pipeline.process_event(transaction_event)
        
        # Record metrics
        obs = get_observability()
        obs.increment_counter(TRANSACTIONS_PROCESSED, {
            "decision_type": result["risk_decision"].decision_type.value,
            "risk_level": "high" if result["risk_decision"].confidence > 0.7 else "low"
        })
        
        return {
            "success": True,
            "decision": result["risk_decision"].dict(),
            "anomaly_flags": result["anomaly_flags"],
            "sanctions_match": result["sanctions_match"],
            "processing_complete": result["processing_complete"]
        }
    
    except Exception as e:
        logger.error(f"Error processing event: {e}")
        
        obs = get_observability()
        obs.increment_counter(ERRORS_TOTAL, {
            "error_type": type(e).__name__,
            "component": "api.process_event"
        })
        
        return {
            "success": False,
            "error": str(e)
        }


@app.get("/pipeline/status")
async def pipeline_status():
    """Get current pipeline status and statistics."""
    return {
        "pipeline_initialized": pipeline is not None,
        "consumer_running": consumer.is_running() if consumer else False,
        "consumer_topic": settings.kafka.order_topic,
        "environment": settings.environment,
        "tracing_enabled": settings.tracing_enabled,
        "metrics_enabled": settings.metrics_enabled
    }


def main():
    """Run the service with uvicorn."""
    import uvicorn
    
    uvicorn.run(
        "aerorisk.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "development",
        log_level=settings.log_level.lower()
    )


if __name__ == "__main__":
    main()

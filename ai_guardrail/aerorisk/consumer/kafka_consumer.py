"""Kafka consumer for AI guardrail event processing."""

import asyncio
import json
from typing import Optional, Callable, Awaitable
from aiokafka import AIOKafkaConsumer
from aerorisk.config.settings import settings
from aerorisk.models.event import TransactionEvent, EventType
from aerorisk.observability.metrics import metrics
from aerorisk.observability.tracing import tracer
from opentelemetry.trace import Status, StatusCode
import logging

logger = logging.getLogger(__name__)


class KafkaEventConsumer:
    """Async Kafka consumer for transaction events."""

    def __init__(
        self,
        topics: list[str],
        handler: Callable[[TransactionEvent], Awaitable[None]],
        group_id: str = "ai-guardrail-group",
    ):
        self.topics = topics
        self.handler = handler
        self.group_id = group_id
        self.consumer: Optional[AIOKafkaConsumer] = None
        self.running = False

    async def start(self) -> None:
        """Start the Kafka consumer."""
        self.consumer = AIOKafkaConsumer(
            *self.topics,
            bootstrap_servers=settings.kafka_bootstrap_servers,
            group_id=self.group_id,
            auto_offset_reset="latest",
            enable_auto_commit=True,
            max_poll_records=100,
            session_timeout_ms=30000,
            heartbeat_interval_ms=10000,
        )
        await self.consumer.start()
        self.running = True
        logger.info(f"Kafka consumer started, listening to: {self.topics}")

    async def stop(self) -> None:
        """Stop the Kafka consumer."""
        self.running = False
        if self.consumer:
            await self.consumer.stop()
            logger.info("Kafka consumer stopped")

    async def consume_loop(self) -> None:
        """Main consumption loop with error handling."""
        if not self.consumer:
            raise RuntimeError("Consumer not started")

        while self.running:
            try:
                msg = await asyncio.wait_for(
                    self.consumer.getone(), timeout=5.0
                )
                
                if msg is None:
                    continue

                # Parse event
                event_data = json.loads(msg.value.decode("utf-8"))
                event = TransactionEvent.model_validate(event_data)

                # Create tracing span
                with tracer.start_as_current_span(
                    "process_transaction_event",
                    attributes={
                        "event.type": event.event_type.value,
                        "event.id": event.event_id,
                        "event.user_id": event.user_id,
                    },
                ) as span:
                    try:
                        # Process event
                        await self.handler(event)
                        
                        # Record success metric
                        metrics.events_processed_total.labels(
                            event_type=event.event_type.value,
                            status="success",
                        ).inc()
                        
                        span.set_status(Status(StatusCode.OK))
                        
                    except Exception as e:
                        logger.error(f"Error processing event {event.event_id}: {e}")
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        metrics.events_processed_total.labels(
                            event_type=event.event_type.value,
                            status="error",
                        ).inc()
                        raise

            except asyncio.TimeoutError:
                # No message received, continue loop
                continue
            except Exception as e:
                logger.error(f"Consumer loop error: {e}")
                await asyncio.sleep(1.0)  # Backoff on error

    async def process_batch(self) -> list[TransactionEvent]:
        """Process a batch of events for higher throughput."""
        if not self.consumer:
            raise RuntimeError("Consumer not started")

        events = []
        try:
            msgs = await self.consumer.getmany(timeout_ms=100, max_records=100)
            
            for topic_partition, messages in msgs.items():
                for msg in messages:
                    event_data = json.loads(msg.value.decode("utf-8"))
                    event = TransactionEvent.model_validate(event_data)
                    events.append(event)
                    
            metrics.batch_size.observe(len(events))
            
        except Exception as e:
            logger.error(f"Batch processing error: {e}")
            
        return events

"""Event parser for validating and transforming Kafka messages."""

import json
from typing import Any, Optional
from pydantic import ValidationError
from aerorisk.models.event import TransactionEvent, EventType, OrderSide, OrderType
from aerorisk.models.anomaly_result import AnomalyFlag, AnomalyType
import logging

logger = logging.getLogger(__name__)


class EventParseError(Exception):
    """Custom exception for event parsing errors."""

    def __init__(self, message: str, raw_data: Any = None):
        super().__init__(message)
        self.raw_data = raw_data


class EventParser:
    """Parser for validating and transforming transaction events."""

    @staticmethod
    def parse_transaction_event(data: dict[str, Any]) -> TransactionEvent:
        """
        Parse raw dictionary data into a TransactionEvent.
        
        Args:
            data: Raw event data from Kafka
            
        Returns:
            Validated TransactionEvent
            
        Raises:
            EventParseError: If parsing fails
        """
        try:
            return TransactionEvent.model_validate(data)
        except ValidationError as e:
            logger.error(f"Validation error: {e}")
            raise EventParseError(f"Invalid event format: {e}", data)
        except Exception as e:
            logger.error(f"Unexpected parsing error: {e}")
            raise EventParseError(f"Failed to parse event: {e}", data)

    @staticmethod
    def parse_from_json(json_str: str) -> TransactionEvent:
        """
        Parse JSON string into TransactionEvent.
        
        Args:
            json_str: JSON encoded event
            
        Returns:
            Validated TransactionEvent
        """
        try:
            data = json.loads(json_str)
            return EventParser.parse_transaction_event(data)
        except json.JSONDecodeError as e:
            raise EventParseError(f"Invalid JSON: {e}", json_str)

    @staticmethod
    def validate_event_type(event: TransactionEvent, expected_types: list[EventType]) -> bool:
        """
        Validate that event is of expected type(s).
        
        Args:
            event: Event to validate
            expected_types: List of acceptable event types
            
        Returns:
            True if valid, False otherwise
        """
        return event.event_type in expected_types

    @staticmethod
    def extract_order_fields(event: TransactionEvent) -> Optional[dict[str, Any]]:
        """
        Extract order-specific fields from event.
        
        Args:
            event: Transaction event
            
        Returns:
            Dictionary with order fields or None if not an order event
        """
        if event.event_type not in [EventType.ORDER_NEW, EventType.ORDER_CANCEL, EventType.ORDER_MODIFY]:
            return None
            
        return {
            "order_id": event.order_id,
            "symbol": event.symbol,
            "side": event.side.value if event.side else None,
            "order_type": event.order_type.value if event.order_type else None,
            "price": event.price,
            "quantity": event.quantity,
            "user_id": event.user_id,
        }

    @staticmethod
    def create_anomaly_flag(
        anomaly_type: AnomalyType,
        confidence: float,
        details: str,
        event_id: Optional[str] = None,
    ) -> AnomalyFlag:
        """
        Create an anomaly flag result.
        
        Args:
            anomaly_type: Type of anomaly detected
            confidence: Confidence score (0.0-1.0)
            details: Human-readable description
            event_id: Related event ID
            
        Returns:
            AnomalyFlag instance
        """
        return AnomalyFlag(
            anomaly_type=anomaly_type,
            confidence=confidence,
            details=details,
            related_event_id=event_id,
        )

    @staticmethod
    def serialize_event(event: TransactionEvent) -> str:
        """
        Serialize event to JSON string for logging/storage.
        
        Args:
            event: Event to serialize
            
        Returns:
            JSON string representation
        """
        return event.model_dump_json()

    @staticmethod
    def enrich_event_with_metadata(
        event: TransactionEvent,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Add metadata to event for downstream processing.
        
        Args:
            event: Base event
            metadata: Additional metadata to include
            
        Returns:
            Enriched event dictionary
        """
        event_dict = event.model_dump()
        event_dict["metadata"] = metadata
        return event_dict

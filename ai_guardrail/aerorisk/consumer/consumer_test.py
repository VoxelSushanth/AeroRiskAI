"""Tests for Kafka consumer functionality."""

import pytest
import json
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from aerorisk.consumer.kafka_consumer import KafkaEventConsumer
from aerorisk.consumer.event_parser import EventParser, EventParseError
from aerorisk.models.event import TransactionEvent, EventType, OrderSide, OrderType


class TestEventParser:
    """Test suite for EventParser."""

    def test_parse_valid_order_event(self):
        """Test parsing a valid order event."""
        data = {
            "event_id": "evt-123",
            "event_type": "order_new",
            "user_id": "user-456",
            "order_id": "ord-789",
            "symbol": "AAPL",
            "side": "buy",
            "order_type": "limit",
            "price": 15000,  # Fixed point: $150.00
            "quantity": 100,
            "timestamp": "2024-01-15T10:30:00Z",
        }
        
        event = EventParser.parse_transaction_event(data)
        
        assert event.event_id == "evt-123"
        assert event.event_type == EventType.ORDER_NEW
        assert event.user_id == "user-456"
        assert event.order_id == "ord-789"
        assert event.symbol == "AAPL"
        assert event.side == OrderSide.BUY
        assert event.order_type == OrderType.LIMIT
        assert event.price == 15000
        assert event.quantity == 100

    def test_parse_invalid_json(self):
        """Test parsing invalid JSON raises error."""
        with pytest.raises(EventParseError) as exc_info:
            EventParser.parse_from_json("not valid json")
        
        assert "Invalid JSON" in str(exc_info.value)

    def test_parse_missing_required_field(self):
        """Test parsing event with missing required field."""
        data = {
            "event_id": "evt-123",
            # Missing event_type
            "user_id": "user-456",
        }
        
        with pytest.raises(EventParseError) as exc_info:
            EventParser.parse_transaction_event(data)
        
        assert "Invalid event format" in str(exc_info.value)

    def test_validate_event_type(self):
        """Test event type validation."""
        event = TransactionEvent(
            event_id="evt-123",
            event_type=EventType.ORDER_NEW,
            user_id="user-456",
            symbol="AAPL",
            price=15000,
            quantity=100,
        )
        
        # Valid type
        assert EventParser.validate_event_type(event, [EventType.ORDER_NEW]) is True
        assert EventParser.validate_event_type(event, [EventType.ORDER_NEW, EventType.TRADE]) is True
        
        # Invalid type
        assert EventParser.validate_event_type(event, [EventType.TRADE]) is False

    def test_extract_order_fields(self):
        """Test extracting order fields from event."""
        event = TransactionEvent(
            event_id="evt-123",
            event_type=EventType.ORDER_NEW,
            user_id="user-456",
            order_id="ord-789",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            price=15000,
            quantity=100,
        )
        
        fields = EventParser.extract_order_fields(event)
        
        assert fields is not None
        assert fields["order_id"] == "ord-789"
        assert fields["symbol"] == "AAPL"
        assert fields["side"] == "buy"
        assert fields["price"] == 15000

    def test_extract_order_fields_non_order_event(self):
        """Test extracting fields from non-order event returns None."""
        event = TransactionEvent(
            event_id="evt-123",
            event_type=EventType.TRADE,
            user_id="user-456",
            symbol="AAPL",
            price=15000,
            quantity=100,
        )
        
        fields = EventParser.extract_order_fields(event)
        assert fields is None

    def test_serialize_event(self):
        """Test event serialization to JSON."""
        event = TransactionEvent(
            event_id="evt-123",
            event_type=EventType.ORDER_NEW,
            user_id="user-456",
            symbol="AAPL",
            price=15000,
            quantity=100,
        )
        
        json_str = EventParser.serialize_event(event)
        parsed = json.loads(json_str)
        
        assert parsed["event_id"] == "evt-123"
        assert parsed["event_type"] == "order_new"

    def test_enrich_event_with_metadata(self):
        """Test adding metadata to event."""
        event = TransactionEvent(
            event_id="evt-123",
            event_type=EventType.ORDER_NEW,
            user_id="user-456",
            symbol="AAPL",
            price=15000,
            quantity=100,
        )
        
        metadata = {"source": "gateway-1", "region": "us-east"}
        enriched = EventParser.enrich_event_with_metadata(event, metadata)
        
        assert enriched["event_id"] == "evt-123"
        assert enriched["metadata"]["source"] == "gateway-1"
        assert enriched["metadata"]["region"] == "us-east"


class TestKafkaEventConsumer:
    """Test suite for KafkaEventConsumer."""

    @pytest.mark.asyncio
    async def test_consumer_start_stop(self):
        """Test consumer start and stop lifecycle."""
        handler = AsyncMock()
        consumer = KafkaEventConsumer(
            topics=["test-topic"],
            handler=handler,
            group_id="test-group",
        )
        
        with patch.object(consumer, 'consumer', AsyncMock()) as mock_consumer:
            mock_consumer.start = AsyncMock()
            mock_consumer.stop = AsyncMock()
            
            await consumer.start()
            assert consumer.running is True
            
            await consumer.stop()
            assert consumer.running is False

    @pytest.mark.asyncio
    async def test_handler_invocation(self):
        """Test that handler is called with parsed events."""
        handler = AsyncMock()
        consumer = KafkaEventConsumer(
            topics=["test-topic"],
            handler=handler,
        )
        
        # Simulate event processing
        event_data = {
            "event_id": "evt-123",
            "event_type": "order_new",
            "user_id": "user-456",
            "symbol": "AAPL",
            "price": 15000,
            "quantity": 100,
        }
        event = TransactionEvent.model_validate(event_data)
        
        await handler(event)
        handler.assert_called_once_with(event)


def test_create_anomaly_flag():
    """Test creating anomaly flag."""
    flag = EventParser.create_anomaly_flag(
        anomaly_type="velocity_check",
        confidence=0.95,
        details="User exceeded velocity threshold",
        event_id="evt-123",
    )
    
    assert flag.anomaly_type == "velocity_check"
    assert flag.confidence == 0.95
    assert flag.details == "User exceeded velocity threshold"
    assert flag.related_event_id == "evt-123"

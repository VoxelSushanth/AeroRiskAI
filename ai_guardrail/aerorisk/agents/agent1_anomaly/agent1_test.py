"""
Tests for Agent 1 Anomaly Detection.
"""

import asyncio
import pytest
from datetime import datetime

from aerorisk.models.event import OrderEvent, OrderSide, OrderAction
from aerorisk.agents.agent1_anomaly.velocity_check import VelocityChecker
from aerorisk.agents.agent1_anomaly.vwap_monitor import VWAPMonitor
from aerorisk.agents.agent1_anomaly.wash_trade import WashTradeDetector
from aerorisk.agents.agent1_anomaly.spoofing_hmm import SpoofingDetector


@pytest.fixture
def sample_order_event():
    """Create a sample order event for testing."""
    return OrderEvent(
        order_id="ORD-001",
        account_id="ACC-12345",
        symbol="AAPL",
        side=OrderSide.BUY,
        action=OrderAction.SUBMIT,
        price=1500000,  # $15.00 in fixed-point
        quantity=100,
        timestamp=datetime.utcnow().timestamp(),
    )


@pytest.mark.asyncio
async def test_velocity_checker_normal(sample_order_event):
    """Test velocity checker with normal order rate."""
    checker = VelocityChecker(max_orders_per_second=100)
    result = await checker.check(sample_order_event)

    assert result.is_anomalous is False
    assert result.severity_score == 0.0
    assert result.anomaly_type.value == "velocity_violation"


@pytest.mark.asyncio
async def test_vwap_monitor_insufficient_history(sample_order_event):
    """Test VWAP monitor with insufficient history."""
    monitor = VWAPMonitor()
    result = await monitor.check(sample_order_event)

    # First event should have insufficient history
    assert result.is_anomalous is False
    assert result.details.get("reason") == "insufficient_history"


@pytest.mark.asyncio
async def test_wash_trade_detector_single_event(sample_order_event):
    """Test wash trade detector with single event."""
    detector = WashTradeDetector()
    result = await detector.check(sample_order_event)

    # Single event cannot be wash trade
    assert result.is_anomalous is False


@pytest.mark.asyncio
async def test_spoofing_detector_submission(sample_order_event):
    """Test spoofing detector on order submission."""
    detector = SpoofingDetector()
    result = await detector.check(sample_order_event)

    # Submission alone is not anomalous
    assert result.is_anomalous is False
    assert result.details.get("reason") == "order_submission"


@pytest.mark.asyncio
async def test_velocity_checker_high_frequency():
    """Test velocity checker with high frequency orders."""
    checker = VelocityChecker(
        window_size=60,
        max_orders_per_second=10,  # Low threshold for testing
    )

    base_time = datetime.utcnow().timestamp()
    account_id = "ACC-HIGH-FREQ"

    # Submit many orders rapidly
    for i in range(50):
        event = OrderEvent(
            order_id=f"ORD-{i}",
            account_id=account_id,
            symbol="AAPL",
            side=OrderSide.BUY,
            action=OrderAction.SUBMIT,
            price=1500000,
            quantity=100,
            timestamp=base_time + (i * 0.01),  # 10ms apart
        )
        result = await checker.check(event)

    # Last result should show anomaly
    assert result.is_anomalous is True
    assert result.severity_score > 0.0


@pytest.mark.asyncio
async def test_embedding_generation():
    """Test embedding generation utility."""
    from aerorisk.agents.agent1_anomaly.embedding import EmbeddingGenerator

    generator = EmbeddingGenerator(embedding_dim=128)
    embedding = generator.generate_order_embedding(
        account_id="ACC-123",
        symbol="AAPL",
        side="BUY",
        price=1500000,
        quantity=100,
        timestamp=datetime.utcnow().timestamp(),
    )

    assert len(embedding) == 128
    assert all(0.0 <= e <= 1.0 for e in embedding)

    # Test similarity
    embedding2 = generator.generate_order_embedding(
        account_id="ACC-123",
        symbol="AAPL",
        side="BUY",
        price=1500000,
        quantity=100,
        timestamp=datetime.utcnow().timestamp(),
    )

    similarity = generator.cosine_similarity(embedding, embedding2)
    assert 0.0 <= similarity <= 1.0

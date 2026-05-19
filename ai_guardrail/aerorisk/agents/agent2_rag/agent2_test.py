"""Tests for Agent 2 - RAG and Compliance Retrieval."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from aerorisk.agents.agent2_rag.agent import RAGAgent
from aerorisk.agents.agent2_rag.vector_search import VectorSearchService
from aerorisk.agents.agent2_rag.compliance_loader import ComplianceLoader
from aerorisk.agents.agent2_rag.user_profile import UserProfileService
from aerorisk.agents.agent2_rag.sanctions import SanctionsScreener
from aerorisk.agents.agent2_rag.news_ingester import NewsIngester
from aerorisk.models.event import TransactionEvent, EventType, OrderSide
from aerorisk.models.context_bundle import ContextBundle, UserProfile, SanctionsMatch


class TestRAGAgent:
    """Test suite for RAGAgent."""

    @pytest.mark.asyncio
    async def test_retrieve_context(self):
        """Test context retrieval for an event."""
        agent = RAGAgent()
        
        # Mock dependencies
        agent.qdrant = AsyncMock()
        agent.postgres = AsyncMock()
        
        # Setup mock responses
        agent.qdrant.search_similar = AsyncMock(return_value=[])
        agent.postgres.get_user_profile = AsyncMock(return_value={
            "risk_tier": "standard",
            "account_type": "individual",
            "daily_limit": 1000000,
        })
        agent.postgres.get_user_details = AsyncMock(return_value=None)
        
        event = TransactionEvent(
            event_id="evt-123",
            event_type=EventType.ORDER_NEW,
            user_id="user-456",
            symbol="AAPL",
            price=15000,
            quantity=100,
        )
        
        context = await agent.retrieve_context(event)
        
        assert isinstance(context, ContextBundle)
        assert context.compliance_rules == []
        assert context.news_context == []

    @pytest.mark.asyncio
    async def test_sanctions_match_blocks(self):
        """Test that sanctions match is detected."""
        agent = RAGAgent()
        agent.qdrant = AsyncMock()
        agent.postgres = AsyncMock()
        
        # Mock sanctions match
        mock_result = MagicMock()
        mock_result.payload = {
            "name": "John Doe",
            "list_source": "OFAC",
            "entity_id": "sdn-123",
        }
        mock_result.score = 0.95
        
        agent.qdrant.search_similar = AsyncMock(return_value=[mock_result])
        agent.postgres.get_user_details = AsyncMock(return_value={
            "full_name": "John Doe",
        })
        
        is_blocked, match = await agent.screen_user("user-456")
        
        # Note: screen_user is in SanctionsScreener, testing via agent
        assert match is not None
        assert match.match_score == 0.95


class TestSanctionsScreener:
    """Test suite for SanctionsScreener."""

    @pytest.mark.asyncio
    async def test_screen_user_no_match(self):
        """Test screening user with no sanctions match."""
        screener = SanctionsScreener()
        screener.qdrant = AsyncMock()
        screener.postgres = AsyncMock()
        
        screener.qdrant.search_similar = AsyncMock(return_value=[])
        screener.postgres.get_user_details = AsyncMock(return_value={
            "full_name": "John Smith",
            "email": "john@example.com",
        })
        
        is_blocked, match = await screener.screen_user("user-123")
        
        assert is_blocked is False
        assert match is None

    @pytest.mark.asyncio
    async def test_screen_user_with_match(self):
        """Test screening user with sanctions match."""
        screener = SanctionsScreener()
        screener.qdrant = AsyncMock()
        screener.postgres = AsyncMock()
        
        mock_result = MagicMock()
        mock_result.payload = {
            "name": "Blocked Entity",
            "list_source": "OFAC_SDN",
            "entity_id": "sdn-999",
        }
        mock_result.score = 0.92
        
        screener.qdrant.search_similar = AsyncMock(return_value=[mock_result])
        screener.postgres.get_user_details = AsyncMock(return_value={
            "full_name": "Blocked Entity",
        })
        
        is_blocked, match = await screener.screen_user("user-456")
        
        assert is_blocked is True
        assert match is not None
        assert match.list_source == "OFAC_SDN"

    @pytest.mark.asyncio
    async def test_screen_entity(self):
        """Test entity screening."""
        screener = SanctionsScreener()
        screener.qdrant = AsyncMock()
        
        mock_result = MagicMock()
        mock_result.payload = {
            "name": "Sanctioned Corp",
            "list_source": "EU_SANCTIONS",
        }
        mock_result.score = 0.88
        
        screener.qdrant.search_similar = AsyncMock(return_value=[mock_result])
        
        match = await screener.screen_entity("Sanctioned Corp")
        
        assert match is not None
        assert match.matched_name == "Sanctioned Corp"


class TestUserProfileService:
    """Test suite for UserProfileService."""

    @pytest.mark.asyncio
    async def test_get_profile(self):
        """Test retrieving user profile."""
        service = UserProfileService()
        service.postgres = AsyncMock()
        
        service.postgres.get_user_profile = AsyncMock(return_value={
            "risk_tier": "elevated",
            "account_type": "institutional",
            "daily_limit": 10000000,
            "single_order_limit": 1000000,
            "max_orders_per_minute": 120,
            "kyc_status": "verified",
            "jurisdiction": "US",
        })
        
        profile = await service.get_profile("user-789")
        
        assert profile is not None
        assert profile.user_id == "user-789"
        assert profile.risk_tier == "elevated"
        assert profile.trading_limits["daily_limit"] == 10000000

    @pytest.mark.asyncio
    async def test_check_velocity_limits_allowed(self):
        """Test velocity limit check within limits."""
        service = UserProfileService()
        service.postgres = AsyncMock()
        
        service.postgres.get_user_profile = AsyncMock(return_value={
            "risk_tier": "standard",
            "max_orders_per_minute": 60,
        })
        service.postgres.count_recent_orders = AsyncMock(return_value=30)
        
        result = await service.check_velocity_limits("user-123")
        
        assert result["allowed"] is True
        assert result["remaining"] == 30

    @pytest.mark.asyncio
    async def test_check_velocity_limits_exceeded(self):
        """Test velocity limit check exceeded."""
        service = UserProfileService()
        service.postgres = AsyncMock()
        
        service.postgres.get_user_profile = AsyncMock(return_value={
            "risk_tier": "standard",
            "max_orders_per_minute": 60,
        })
        service.postgres.count_recent_orders = AsyncMock(return_value=65)
        
        result = await service.check_velocity_limits("user-123")
        
        assert result["allowed"] is False
        assert result["reason"] == "velocity_exceeded"

    @pytest.mark.asyncio
    async def test_get_risk_score(self):
        """Test risk score calculation."""
        service = UserProfileService()
        service.postgres = AsyncMock()
        
        service.postgres.get_user_profile = AsyncMock(return_value={
            "risk_tier": "high",
            "historical_flags": ["wash_trade", "spoofing"],
            "kyc_status": "pending",
        })
        
        score = await service.get_risk_score("user-456")
        
        # High tier (0.9 * 0.4 = 0.36) + flags (0.2) + unverified KYC (0.2) = 0.76
        assert 0.7 <= score <= 0.8


class TestNewsIngester:
    """Test suite for NewsIngester."""

    @pytest.mark.asyncio
    async def test_ingest_article(self):
        """Test news article ingestion."""
        ingester = NewsIngester()
        ingester.qdrant = AsyncMock()
        
        doc_id = await ingester.ingest_article(
            headline="AAPL Hits Record High",
            content="Apple stock reached new heights today...",
            source="Financial Times",
            published_at=datetime.now(),
            symbols=["AAPL"],
            sentiment="positive",
        )
        
        assert doc_id.startswith("news_")
        ingester.qdrant.upsert_document.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_sentiment_summary(self):
        """Test sentiment summary calculation."""
        ingester = NewsIngester()
        ingester.qdrant = AsyncMock()
        
        # Mock news results
        mock_result1 = MagicMock()
        mock_result1.payload = {
            "headline": "Good news",
            "sentiment": "positive",
            "published_at": datetime.now().isoformat(),
        }
        
        mock_result2 = MagicMock()
        mock_result2.payload = {
            "headline": "Bad news",
            "sentiment": "negative",
            "published_at": datetime.now().isoformat(),
        }
        
        ingester.qdrant.search_similar = AsyncMock(return_value=[
            mock_result1, mock_result2
        ])
        
        summary = await ingester.get_sentiment_summary("AAPL")
        
        assert summary["article_count"] == 2
        assert "breakdown" in summary


def test_compliance_loader_initialization():
    """Test ComplianceLoader initialization."""
    loader = ComplianceLoader()
    assert loader.rules_dir is not None

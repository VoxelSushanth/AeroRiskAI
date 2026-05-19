"""Agent 2 - RAG and Compliance Retrieval Agent."""

from typing import Optional, Any
from aerorisk.models.event import TransactionEvent
from aerorisk.models.context_bundle import ContextBundle, ComplianceRule, UserProfile, SanctionsMatch
from aerorisk.storage.qdrant_client import QdrantVectorClient
from aerorisk.storage.postgres_client import PostgresClient
from aerorisk.config.settings import settings
import logging

logger = logging.getLogger(__name__)


class RAGAgent:
    """Agent for retrieval-augmented generation with compliance data."""

    def __init__(
        self,
        qdrant_client: Optional[QdrantVectorClient] = None,
        postgres_client: Optional[PostgresClient] = None,
    ):
        self.qdrant = qdrant_client or QdrantVectorClient()
        self.postgres = postgres_client or PostgresClient()
        self.sanctions_cache: dict[str, SanctionsMatch] = {}

    async def retrieve_context(self, event: TransactionEvent) -> ContextBundle:
        """
        Retrieve all relevant context for a transaction event.
        
        Args:
            event: Transaction event to analyze
            
        Returns:
            ContextBundle with all retrieved information
        """
        logger.info(f"Retrieving context for event {event.event_id}, user {event.user_id}")
        
        # Parallel retrieval where possible
        compliance_rules, user_profile, sanctions_match, news_context = await asyncio.gather(
            self._retrieve_compliance_rules(event.symbol),
            self._retrieve_user_profile(event.user_id),
            self._check_sanctions(event.user_id),
            self._retrieve_news_context(event.symbol),
            return_exceptions=True,
        )
        
        # Handle exceptions gracefully
        if isinstance(compliance_rules, Exception):
            logger.error(f"Compliance retrieval failed: {compliance_rules}")
            compliance_rules = []
            
        if isinstance(user_profile, Exception):
            logger.error(f"User profile retrieval failed: {user_profile}")
            user_profile = None
            
        if isinstance(sanctions_match, Exception):
            logger.error(f"Sanctions check failed: {sanctions_match}")
            sanctions_match = None
            
        if isinstance(news_context, Exception):
            logger.error(f"News retrieval failed: {news_context}")
            news_context = []
        
        return ContextBundle(
            compliance_rules=compliance_rules or [],
            user_profile=user_profile,
            sanctions_match=sanctions_match,
            news_context=news_context or [],
        )

    async def _retrieve_compliance_rules(self, symbol: str) -> list[ComplianceRule]:
        """Retrieve compliance rules relevant to the symbol."""
        try:
            # Vector search for compliance rules
            query = f"trading rules for {symbol} equity securities"
            results = await self.qdrant.search_similar(
                collection_name="compliance_rules",
                query_text=query,
                limit=5,
            )
            
            rules = []
            for result in results:
                payload = result.payload
                rules.append(ComplianceRule(
                    rule_id=payload.get("rule_id", ""),
                    source=payload.get("source", ""),
                    content=payload.get("content", ""),
                    relevance_score=result.score,
                ))
            
            logger.debug(f"Retrieved {len(rules)} compliance rules for {symbol}")
            return rules
            
        except Exception as e:
            logger.error(f"Error retrieving compliance rules: {e}")
            return []

    async def _retrieve_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """Retrieve user profile from database."""
        try:
            profile_data = await self.postgres.get_user_profile(user_id)
            
            if not profile_data:
                logger.warning(f"No profile found for user {user_id}")
                return None
            
            return UserProfile(
                user_id=user_id,
                risk_tier=profile_data.get("risk_tier", "standard"),
                account_type=profile_data.get("account_type", "individual"),
                trading_limits={
                    "daily_limit": profile_data.get("daily_limit", 1000000),
                    "single_order_limit": profile_data.get("single_order_limit", 100000),
                    "max_orders_per_minute": profile_data.get("max_orders_per_minute", 60),
                },
                historical_flags=profile_data.get("historical_flags", []),
                kyc_status=profile_data.get("kyc_status", "verified"),
                jurisdiction=profile_data.get("jurisdiction", "US"),
            )
            
        except Exception as e:
            logger.error(f"Error retrieving user profile: {e}")
            return None

    async def _check_sanctions(self, user_id: str) -> Optional[SanctionsMatch]:
        """Check if user is on sanctions list."""
        try:
            # Check cache first
            if user_id in self.sanctions_cache:
                return self.sanctions_cache[user_id]
            
            # Get user details
            user_info = await self.postgres.get_user_details(user_id)
            if not user_info:
                return None
            
            # Search sanctions list
            name = user_info.get("full_name", "")
            if not name:
                return None
            
            # Vector search against OFAC SDN list
            results = await self.qdrant.search_similar(
                collection_name="sanctions_list",
                query_text=name,
                limit=3,
                score_threshold=0.85,  # High threshold for sanctions
            )
            
            if results:
                match = SanctionsMatch(
                    matched_name=results[0].payload.get("name", ""),
                    list_source=results[0].payload.get("list_source", "OFAC"),
                    match_score=results[0].score,
                    entity_id=results[0].payload.get("entity_id", ""),
                )
                self.sanctions_cache[user_id] = match
                logger.warning(f"SANCTIONS MATCH for user {user_id}: {match.matched_name}")
                return match
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking sanctions: {e}")
            return None

    async def _retrieve_news_context(self, symbol: str) -> list[dict[str, Any]]:
        """Retrieve recent news related to the symbol."""
        try:
            results = await self.qdrant.search_similar(
                collection_name="news_feed",
                query_text=f"market news {symbol}",
                limit=3,
            )
            
            news_items = []
            for result in results:
                payload = result.payload
                news_items.append({
                    "headline": payload.get("headline", ""),
                    "source": payload.get("source", ""),
                    "sentiment": payload.get("sentiment", "neutral"),
                    "timestamp": payload.get("timestamp", ""),
                    "relevance_score": result.score,
                })
            
            return news_items
            
        except Exception as e:
            logger.error(f"Error retrieving news: {e}")
            return []

    async def get_circuit_breaker_state(self, symbol: str) -> dict[str, Any]:
        """Get current circuit breaker state for a symbol."""
        try:
            # Query Redis via storage client
            state = await self.postgres.get_circuit_breaker_state(symbol)
            return state or {"status": "closed", "trigger_count": 0}
        except Exception as e:
            logger.error(f"Error getting circuit breaker state: {e}")
            return {"status": "closed", "trigger_count": 0}

    async def enrich_with_regulatory_context(self, event: TransactionEvent) -> dict[str, Any]:
        """
        Enrich event with regulatory context based on jurisdiction and trade type.
        
        Args:
            event: Transaction event
            
        Returns:
            Dictionary with regulatory context
        """
        context = {
            "applicable_regulations": [],
            "reporting_requirements": [],
            "restrictions": [],
        }
        
        try:
            user_profile = await self._retrieve_user_profile(event.user_id)
            
            if user_profile:
                jurisdiction = user_profile.jurisdiction
                
                # Add jurisdiction-specific regulations
                if jurisdiction == "US":
                    context["applicable_regulations"].extend([
                        "SEC Rule 10b-5",
                        "FINRA Rule 2010",
                        "Regulation SHO",
                    ])
                    context["reporting_requirements"].append("Form 4 (if insider)")
                    
                elif jurisdiction == "EU":
                    context["applicable_regulations"].extend([
                        "MiFID II",
                        "Market Abuse Regulation",
                    ])
                    context["reporting_requirements"].append("Transaction Reporting")
                
                # Check for pattern day trader rules
                if user_profile.account_type == "margin":
                    context["restrictions"].append("Pattern Day Trader rules apply")
                    
        except Exception as e:
            logger.error(f"Error enriching regulatory context: {e}")
        
        return context

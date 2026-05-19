"""User profile management for RAG agent."""

from typing import Optional, Any
from datetime import datetime, timedelta
from aerorisk.models.context_bundle import UserProfile
from aerorisk.storage.postgres_client import PostgresClient
from aerorisk.storage.qdrant_client import QdrantVectorClient
import logging

logger = logging.getLogger(__name__)


class UserProfileService:
    """Service for managing and retrieving user profiles."""

    def __init__(
        self,
        postgres_client: Optional[PostgresClient] = None,
        qdrant_client: Optional[QdrantVectorClient] = None,
    ):
        self.postgres = postgres_client or PostgresClient()
        self.qdrant = qdrant_client or QdrantVectorClient()
        self._profile_cache: dict[str, tuple[UserProfile, datetime]] = {}
        self._cache_ttl = timedelta(minutes=5)

    async def get_profile(self, user_id: str) -> Optional[UserProfile]:
        """Get user profile with caching."""
        # Check cache first
        if user_id in self._profile_cache:
            profile, cached_at = self._profile_cache[user_id]
            if datetime.now() - cached_at < self._cache_ttl:
                return profile
        
        # Fetch from database
        try:
            profile_data = await self.postgres.get_user_profile(user_id)
            
            if not profile_data:
                return None
            
            profile = UserProfile(
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
            
            # Cache the profile
            self._profile_cache[user_id] = (profile, datetime.now())
            
            return profile
            
        except Exception as e:
            logger.error(f"Error fetching profile for {user_id}: {e}")
            return None

    async def update_trading_history(
        self,
        user_id: str,
        trade_data: dict[str, Any],
    ) -> None:
        """Update user's trading history for behavioral analysis."""
        try:
            await self.postgres.insert_trade_history(user_id, trade_data)
            
            # Update vector embedding for behavioral similarity search
            await self._update_behavioral_embedding(user_id)
            
        except Exception as e:
            logger.error(f"Error updating trading history: {e}")

    async def _update_behavioral_embedding(self, user_id: str) -> None:
        """Update behavioral embedding for similarity search."""
        try:
            # Get recent trading patterns
            history = await self.postgres.get_recent_trades(user_id, limit=100)
            
            if not history:
                return
            
            # Create behavioral summary
            features = {
                "avg_order_size": sum(t.get("quantity", 0) for t in history) / len(history),
                "trade_frequency": len(history),
                "symbols_traded": list(set(t.get("symbol", "") for t in history)),
            }
            
            behavior_text = f"""
            User {user_id} trading behavior:
            - Average order size: {features['avg_order_size']}
            - Trade frequency: {features['trade_frequency']} trades
            - Symbols: {', '.join(features['symbols_traded'])}
            """
            
            await self.qdrant.upsert_document(
                collection_name="user_profiles",
                document_id=f"behavior_{user_id}",
                text=behavior_text,
                payload={
                    "user_id": user_id,
                    "features": features,
                    "updated_at": datetime.now().isoformat(),
                },
            )
            
        except Exception as e:
            logger.error(f"Error updating behavioral embedding: {e}")

    async def check_velocity_limits(
        self,
        user_id: str,
        window_minutes: int = 1,
    ) -> dict[str, Any]:
        """Check user's order velocity against limits."""
        try:
            profile = await self.get_profile(user_id)
            if not profile:
                return {"allowed": True, "reason": "profile_not_found"}
            
            max_orders = profile.trading_limits.get("max_orders_per_minute", 60)
            
            # Count recent orders
            recent_count = await self.postgres.count_recent_orders(
                user_id,
                minutes=window_minutes,
            )
            
            remaining = max_orders - recent_count
            
            return {
                "allowed": remaining > 0,
                "recent_orders": recent_count,
                "limit": max_orders,
                "remaining": max(0, remaining),
                "reason": "within_limits" if remaining > 0 else "velocity_exceeded",
            }
            
        except Exception as e:
            logger.error(f"Error checking velocity limits: {e}")
            return {"allowed": True, "reason": "error", "error": str(e)}

    async def get_risk_score(self, user_id: str) -> float:
        """Calculate user's current risk score (0.0-1.0)."""
        try:
            profile = await self.get_profile(user_id)
            if not profile:
                return 0.5  # Default medium risk
            
            score = 0.0
            
            # Risk tier contribution
            tier_scores = {
                "low": 0.1,
                "standard": 0.3,
                "elevated": 0.6,
                "high": 0.9,
            }
            score += tier_scores.get(profile.risk_tier, 0.3) * 0.4
            
            # Historical flags contribution
            flag_count = len(profile.historical_flags)
            score += min(flag_count * 0.1, 0.4)  # Cap at 0.4
            
            # KYC status contribution
            if profile.kyc_status != "verified":
                score += 0.2
            
            return min(score, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating risk score: {e}")
            return 0.5

    async def find_similar_users(
        self,
        user_id: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Find users with similar trading behavior."""
        try:
            results = await self.qdrant.search_similar(
                collection_name="user_profiles",
                query_text=f"user {user_id} trading behavior",
                limit=limit + 1,  # +1 to exclude self
            )
            
            similar = []
            for r in results:
                if r.payload.get("user_id") == user_id:
                    continue
                similar.append({
                    "user_id": r.payload.get("user_id"),
                    "score": r.score,
                })
            
            return similar[:limit]
            
        except Exception as e:
            logger.error(f"Error finding similar users: {e}")
            return []

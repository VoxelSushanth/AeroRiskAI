"""Sanctions screening module for compliance checks."""

from typing import Optional, Any
from aerorisk.models.context_bundle import SanctionsMatch
from aerorisk.storage.qdrant_client import QdrantVectorClient
from aerorisk.storage.postgres_client import PostgresClient
import logging

logger = logging.getLogger(__name__)


class SanctionsScreener:
    """Screen users and entities against sanctions lists."""

    # High confidence threshold for sanctions matching
    DEFAULT_THRESHOLD = 0.85
    
    # Supported sanctions lists
    SUPPORTED_LISTS = [
        "OFAC_SDN",      # US Treasury OFAC SDN List
        "UN_CONSOLIDATED", # UN Consolidated List
        "EU_SANCTIONS",   # EU Consolidated Sanctions List
        "HMT_UK",         # UK HM Treasury List
        "INTERPOL",       # Interpol Wanted List
    ]

    def __init__(
        self,
        qdrant_client: Optional[QdrantVectorClient] = None,
        postgres_client: Optional[PostgresClient] = None,
        threshold: float = DEFAULT_THRESHOLD,
    ):
        self.qdrant = qdrant_client or QdrantVectorClient()
        self.postgres = postgres_client or PostgresClient()
        self.threshold = threshold
        self._match_cache: dict[str, tuple[Optional[SanctionsMatch], bool]] = {}

    async def screen_user(self, user_id: str) -> tuple[bool, Optional[SanctionsMatch]]:
        """
        Screen a user against all sanctions lists.
        
        Returns:
            Tuple of (is_blocked, match_details)
            If is_blocked=True, transaction must be rejected
        """
        # Check cache first
        if user_id in self._match_cache:
            match, is_new_check = self._match_cache[user_id]
            if not is_new_check:  # Previous negative result
                return False, None
        
        try:
            # Get user details
            user_info = await self.postgres.get_user_details(user_id)
            if not user_info:
                return False, None
            
            # Screen all identifiers
            identifiers = [
                user_info.get("full_name"),
                user_info.get("email"),
                user_info.get("phone"),
                user_info.get("passport_number"),
                user_info.get("national_id"),
            ]
            
            # Remove None values
            identifiers = [i for i in identifiers if i]
            
            for identifier in identifiers:
                match = await self._screen_identifier(identifier, user_id)
                if match:
                    # Cache positive match
                    self._match_cache[user_id] = (match, True)
                    logger.warning(
                        f"SANCTIONS MATCH: user={user_id}, "
                        f"matched={match.matched_name}, "
                        f"list={match.list_source}, "
                        f"score={match.match_score}"
                    )
                    return True, match
            
            # Cache negative result
            self._match_cache[user_id] = (None, False)
            return False, None
            
        except Exception as e:
            logger.error(f"Sanctions screening error for {user_id}: {e}")
            # Fail open - allow but log error
            return False, None

    async def _screen_identifier(
        self,
        identifier: str,
        user_id: str,
    ) -> Optional[SanctionsMatch]:
        """Screen a single identifier against sanctions lists."""
        try:
            results = await self.qdrant.search_similar(
                collection_name="sanctions_list",
                query_text=identifier,
                limit=3,
                score_threshold=self.threshold,
            )
            
            if results:
                top_match = results[0]
                return SanctionsMatch(
                    matched_name=top_match.payload.get("name", ""),
                    list_source=top_match.payload.get("list_source", "UNKNOWN"),
                    match_score=top_match.score,
                    entity_id=top_match.payload.get("entity_id", ""),
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error screening identifier: {e}")
            return None

    async def screen_entity(
        self,
        entity_name: str,
        entity_type: str = "organization",
    ) -> Optional[SanctionsMatch]:
        """Screen an organization/entity name against sanctions lists."""
        try:
            results = await self.qdrant.search_similar(
                collection_name="sanctions_list",
                query_text=f"{entity_type} {entity_name}",
                limit=3,
                score_threshold=self.threshold,
            )
            
            if results:
                top_match = results[0]
                return SanctionsMatch(
                    matched_name=top_match.payload.get("name", ""),
                    list_source=top_match.payload.get("list_source", "UNKNOWN"),
                    match_score=top_match.score,
                    entity_id=top_match.payload.get("entity_id", ""),
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error screening entity {entity_name}: {e}")
            return None

    async def bulk_screen(
        self,
        user_ids: list[str],
    ) -> dict[str, tuple[bool, Optional[SanctionsMatch]]]:
        """Screen multiple users in batch."""
        results = {}
        
        # Process in parallel with concurrency limit
        import asyncio
        
        semaphore = asyncio.Semaphore(10)  # Max 10 concurrent screenings
        
        async def screen_with_semaphore(user_id: str):
            async with semaphore:
                result = await self.screen_user(user_id)
                return user_id, result
        
        tasks = [screen_with_semaphore(uid) for uid in user_ids]
        completed = await asyncio.gather(*tasks, return_exceptions=True)
        
        for item in completed:
            if isinstance(item, Exception):
                logger.error(f"Bulk screening error: {item}")
            else:
                user_id, result = item
                results[user_id] = result
        
        return results

    async def get_sanctions_metadata(
        self,
        entity_id: str,
    ) -> Optional[dict[str, Any]]:
        """Get detailed metadata about a sanctioned entity."""
        try:
            # Search for the entity
            results = await self.qdrant.get_document(
                collection_name="sanctions_list",
                document_id=entity_id,
            )
            
            if results:
                return results.payload
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting sanctions metadata: {e}")
            return None

    def clear_cache(self, user_id: Optional[str] = None) -> None:
        """Clear sanctions screening cache."""
        if user_id:
            self._match_cache.pop(user_id, None)
        else:
            self._match_cache.clear()
        logger.info("Sanctions cache cleared")

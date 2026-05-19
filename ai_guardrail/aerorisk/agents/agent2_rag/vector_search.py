"""Vector search utilities for RAG agent."""

from typing import Optional, Any
import numpy as np
from aerorisk.storage.qdrant_client import QdrantVectorClient
from aerorisk.agents.agent1_anomaly.embedding import EmbeddingService
import logging

logger = logging.getLogger(__name__)


class VectorSearchService:
    """Service for vector similarity searches across collections."""

    def __init__(
        self,
        qdrant_client: Optional[QdrantVectorClient] = None,
        embedding_service: Optional[EmbeddingService] = None,
    ):
        self.qdrant = qdrant_client or QdrantVectorClient()
        self.embeddings = embedding_service or EmbeddingService()

    async def search_compliance_rules(
        self,
        query: str,
        symbol: Optional[str] = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Search compliance rules by semantic similarity."""
        try:
            if symbol:
                query = f"{query} for {symbol} securities"
            
            results = await self.qdrant.search_similar(
                collection_name="compliance_rules",
                query_text=query,
                limit=limit,
            )
            
            return [
                {
                    "rule_id": r.payload.get("rule_id"),
                    "source": r.payload.get("source"),
                    "content": r.payload.get("content"),
                    "score": r.score,
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"Compliance search failed: {e}")
            return []

    async def search_sanctions(
        self,
        name: str,
        threshold: float = 0.85,
    ) -> list[dict[str, Any]]:
        """Search sanctions list for name matches."""
        try:
            results = await self.qdrant.search_similar(
                collection_name="sanctions_list",
                query_text=name,
                limit=5,
                score_threshold=threshold,
            )
            
            return [
                {
                    "entity_id": r.payload.get("entity_id"),
                    "name": r.payload.get("name"),
                    "list_source": r.payload.get("list_source"),
                    "score": r.score,
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"Sanctions search failed: {e}")
            return []

    async def search_user_profiles(
        self,
        query: str,
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        """Search user profiles by behavioral patterns."""
        try:
            results = await self.qdrant.search_similar(
                collection_name="user_profiles",
                query_text=query,
                limit=limit,
            )
            
            return [
                {
                    "user_id": r.payload.get("user_id"),
                    "risk_tier": r.payload.get("risk_tier"),
                    "score": r.score,
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"User profile search failed: {e}")
            return []

    async def search_news(
        self,
        query: str,
        hours: int = 24,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Search recent news articles."""
        try:
            results = await self.qdrant.search_similar(
                collection_name="news_feed",
                query_text=query,
                limit=limit,
            )
            
            return [
                {
                    "headline": r.payload.get("headline"),
                    "source": r.payload.get("source"),
                    "sentiment": r.payload.get("sentiment"),
                    "timestamp": r.payload.get("timestamp"),
                    "score": r.score,
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"News search failed: {e}")
            return []

    async def batch_search(
        self,
        queries: list[tuple[str, str]],  # (collection, query)
        limit: int = 3,
    ) -> dict[str, list[dict[str, Any]]]:
        """Perform batch searches across multiple collections."""
        import asyncio
        
        tasks = []
        for collection, query in queries:
            task = self.qdrant.search_similar(
                collection_name=collection,
                query_text=query,
                limit=limit,
            )
            tasks.append((collection, task))
        
        results = {}
        completed = await asyncio.gather(
            *[t[1] for t in tasks],
            return_exceptions=True,
        )
        
        for i, (collection, _) in enumerate(tasks):
            if isinstance(completed[i], Exception):
                logger.error(f"Batch search failed for {collection}: {completed[i]}")
                results[collection] = []
            else:
                results[collection] = [
                    {"payload": r.payload, "score": r.score}
                    for r in completed[i]
                ]
        
        return results

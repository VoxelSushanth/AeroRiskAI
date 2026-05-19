"""News ingestion and sentiment analysis for market context."""

from typing import Optional, Any
from datetime import datetime, timedelta
from aerorisk.storage.qdrant_client import QdrantVectorClient
import logging
import hashlib

logger = logging.getLogger(__name__)


class NewsIngester:
    """Ingest and index financial news for RAG retrieval."""

    def __init__(
        self,
        qdrant_client: Optional[QdrantVectorClient] = None,
    ):
        self.qdrant = qdrant_client or QdrantVectorClient()
        self._processed_hashes: set[str] = set()

    async def ingest_article(
        self,
        headline: str,
        content: str,
        source: str,
        published_at: datetime,
        symbols: Optional[list[str]] = None,
        sentiment: Optional[str] = None,
    ) -> str:
        """
        Ingest a news article into the vector store.
        
        Returns:
            Document ID of the ingested article
        """
        # Generate unique ID from content hash
        content_hash = hashlib.sha256(
            f"{headline}:{content}:{published_at.isoformat()}".encode()
        ).hexdigest()[:16]
        doc_id = f"news_{content_hash}"
        
        # Skip if already processed
        if doc_id in self._processed_hashes:
            return doc_id
        
        # Prepare document text for embedding
        doc_text = f"""
        Headline: {headline}
        Source: {source}
        Published: {published_at.isoformat()}
        Symbols: {', '.join(symbols) if symbols else 'N/A'}
        Content: {content}
        Sentiment: {sentiment or 'neutral'}
        """
        
        # Create payload
        payload = {
            "headline": headline,
            "content": content,
            "source": source,
            "published_at": published_at.isoformat(),
            "symbols": symbols or [],
            "sentiment": sentiment or "neutral",
            "ingested_at": datetime.now().isoformat(),
        }
        
        # Index in Qdrant
        await self.qdrant.upsert_document(
            collection_name="news_feed",
            document_id=doc_id,
            text=doc_text,
            payload=payload,
        )
        
        self._processed_hashes.add(doc_id)
        logger.debug(f"Ingested news article: {doc_id}")
        
        return doc_id

    async def ingest_batch(
        self,
        articles: list[dict[str, Any]],
    ) -> tuple[int, int]:
        """
        Ingest multiple articles in batch.
        
        Args:
            articles: List of article dicts with keys:
                - headline, content, source, published_at, symbols, sentiment
        
        Returns:
            Tuple of (successful_count, skipped_count)
        """
        successful = 0
        skipped = 0
        
        for article in articles:
            try:
                await self.ingest_article(
                    headline=article.get("headline", ""),
                    content=article.get("content", ""),
                    source=article.get("source", "unknown"),
                    published_at=(
                        article.get("published_at")
                        if isinstance(article.get("published_at"), datetime)
                        else datetime.fromisoformat(article.get("published_at", datetime.now().isoformat()))
                    ),
                    symbols=article.get("symbols"),
                    sentiment=article.get("sentiment"),
                )
                successful += 1
            except Exception as e:
                logger.error(f"Failed to ingest article: {e}")
                skipped += 1
        
        return successful, skipped

    async def get_recent_news(
        self,
        symbol: Optional[str] = None,
        hours: int = 24,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get recent news articles, optionally filtered by symbol."""
        try:
            if symbol:
                query = f"market news about {symbol} stock"
            else:
                query = "latest financial market news"
            
            results = await self.qdrant.search_similar(
                collection_name="news_feed",
                query_text=query,
                limit=limit * 2,  # Get more to filter by time
            )
            
            # Filter by time
            cutoff = datetime.now() - timedelta(hours=hours)
            filtered = []
            
            for r in results:
                published_str = r.payload.get("published_at")
                if published_str:
                    try:
                        published = datetime.fromisoformat(published_str)
                        if published >= cutoff:
                            filtered.append({
                                "headline": r.payload.get("headline"),
                                "source": r.payload.get("source"),
                                "sentiment": r.payload.get("sentiment"),
                                "published_at": published_str,
                                "symbols": r.payload.get("symbols", []),
                                "score": r.score,
                            })
                    except Exception:
                        continue
                
                if len(filtered) >= limit:
                    break
            
            return filtered
            
        except Exception as e:
            logger.error(f"Error getting recent news: {e}")
            return []

    async def get_sentiment_summary(
        self,
        symbol: str,
        hours: int = 24,
    ) -> dict[str, Any]:
        """Get sentiment summary for a symbol over time period."""
        try:
            news = await self.get_recent_news(symbol=symbol, hours=hours, limit=50)
            
            if not news:
                return {
                    "symbol": symbol,
                    "article_count": 0,
                    "sentiment": "unknown",
                }
            
            # Count sentiments
            sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
            
            for article in news:
                sent = article.get("sentiment", "neutral").lower()
                if sent in sentiment_counts:
                    sentiment_counts[sent] += 1
            
            total = len(news)
            
            # Determine overall sentiment
            if sentiment_counts["positive"] > sentiment_counts["negative"] * 1.5:
                overall = "positive"
            elif sentiment_counts["negative"] > sentiment_counts["positive"] * 1.5:
                overall = "negative"
            else:
                overall = "neutral"
            
            return {
                "symbol": symbol,
                "article_count": total,
                "sentiment": overall,
                "breakdown": sentiment_counts,
                "positive_ratio": sentiment_counts["positive"] / total,
                "negative_ratio": sentiment_counts["negative"] / total,
            }
            
        except Exception as e:
            logger.error(f"Error getting sentiment summary: {e}")
            return {"symbol": symbol, "article_count": 0, "sentiment": "error"}

    def clear_cache(self) -> None:
        """Clear processed article cache."""
        self._processed_hashes.clear()
        logger.info("News ingester cache cleared")

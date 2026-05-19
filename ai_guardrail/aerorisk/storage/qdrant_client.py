"""
AeroRisk AI - Storage Clients Module
Qdrant, PostgreSQL, and Audit Logging implementations
"""

import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
import json

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
import psycopg2
from psycopg2.extras import RealDictCursor

from aerorisk.config.settings import settings
from aerorisk.models.context_bundle import ComplianceRetrieval
from aerorisk.models.incident_report import IncidentReport


class QdrantStorageClient:
    """
    Client for Qdrant vector database.
    
    Used for:
    - Compliance rule embeddings
    - News article vectors
    - User profile similarity search
    - Historical pattern matching
    """
    
    def __init__(self):
        self.client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            timeout=10
        )
        
        self._ensure_collections()
    
    def _ensure_collections(self):
        """Create collections if they don't exist."""
        collections = {
            "compliance_rules": 768,  # embedding dimension
            "news_articles": 768,
            "user_profiles": 512,
            "historical_patterns": 512
        }
        
        for collection_name, vector_size in collections.items():
            try:
                self.client.get_collection(collection_name)
            except Exception:
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=vector_size,
                        distance=Distance.COSINE
                    )
                )
    
    async def search_compliance(
        self,
        query_vector: List[float],
        limit: int = 5
    ) -> List[ComplianceRetrieval]:
        """
        Search compliance rules by vector similarity.
        
        Args:
            query_vector: Embedding of the query text
            limit: Maximum number of results
            
        Returns:
            List of compliance retrievals with relevance scores
        """
        loop = asyncio.get_event_loop()
        
        def _search():
            results = self.client.search(
                collection_name="compliance_rules",
                query_vector=query_vector,
                limit=limit
            )
            
            retrievals = []
            for result in results:
                retrievals.append(ComplianceRetrieval(
                    rule_id=result.payload.get("rule_id", ""),
                    rule_text=result.payload.get("text", ""),
                    source=result.payload.get("source", ""),
                    relevance_score=result.score,
                    jurisdiction=result.payload.get("jurisdiction", "")
                ))
            
            return retrievals
        
        return await loop.run_in_executor(None, _search)
    
    async def search_similar_users(
        self,
        user_embedding: List[float],
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find users with similar trading patterns.
        
        Args:
            user_embedding: User behavior embedding
            user_id: Current user ID (to exclude from results)
            limit: Maximum results
            
        Returns:
            List of similar user profiles
        """
        loop = asyncio.get_event_loop()
        
        def _search():
            # Build filter to exclude current user
            query_filter = Filter(
                must_not=[
                    FieldCondition(
                        key="user_id",
                        match=MatchValue(value=user_id)
                    )
                ]
            )
            
            results = self.client.search(
                collection_name="user_profiles",
                query_vector=user_embedding,
                query_filter=query_filter,
                limit=limit
            )
            
            return [result.payload for result in results]
        
        return await loop.run_in_executor(None, _search)
    
    async def upsert_user_profile(
        self,
        user_id: str,
        embedding: List[float],
        metadata: Dict[str, Any]
    ):
        """
        Update or insert user profile vector.
        
        Args:
            user_id: Unique user identifier
            embedding: User behavior embedding
            metadata: Additional user metadata
        """
        loop = asyncio.get_event_loop()
        
        def _upsert():
            point = PointStruct(
                id=hash(user_id) % (2**63),  # Convert to int64
                vector=embedding,
                payload={
                    "user_id": user_id,
                    **metadata
                }
            )
            
            self.client.upsert(
                collection_name="user_profiles",
                points=[point]
            )
        
        await loop.run_in_executor(None, _upsert)
    
    async def add_news_article(
        self,
        article_id: str,
        embedding: List[float],
        title: str,
        content: str,
        sentiment: float,
        source: str
    ):
        """Add news article to vector store."""
        loop = asyncio.get_event_loop()
        
        def _add():
            point = PointStruct(
                id=hash(article_id) % (2**63),
                vector=embedding,
                payload={
                    "article_id": article_id,
                    "title": title,
                    "content": content,
                    "sentiment": sentiment,
                    "source": source,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            self.client.upsert(
                collection_name="news_articles",
                points=[point]
            )
        
        await loop.run_in_executor(None, _add)


class PostgresStorageClient:
    """
    Client for PostgreSQL database.
    
    Used for:
    - Incident reports
    - Audit logs
    - Compliance metadata
    - User account history
    """
    
    def __init__(self):
        self.conn = psycopg2.connect(
            host=settings.postgres_host,
            port=settings.postgres_port,
            database=settings.postgres_db,
            user=settings.postgres_user,
            password=settings.postgres_password,
            cursor_factory=RealDictCursor
        )
        
        self._initialize_schema()
    
    def _initialize_schema(self):
        """Create tables if they don't exist."""
        with self.conn.cursor() as cur:
            # Incident reports table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS incident_reports (
                    id BIGSERIAL PRIMARY KEY,
                    incident_id VARCHAR(64) UNIQUE NOT NULL,
                    event_id VARCHAR(64) NOT NULL,
                    account_id VARCHAR(64) NOT NULL,
                    decision_type VARCHAR(32) NOT NULL,
                    risk_score DECIMAL(5,4),
                    confidence DECIMAL(5,4),
                    reason TEXT,
                    requires_human_review BOOLEAN DEFAULT FALSE,
                    sanctions_triggered BOOLEAN DEFAULT FALSE,
                    pipeline_error BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    reviewed_at TIMESTAMP,
                    reviewer_id VARCHAR(64),
                    resolution_notes TEXT,
                    metadata JSONB
                )
            """)
            
            # Audit logs table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id BIGSERIAL PRIMARY KEY,
                    log_id VARCHAR(64) UNIQUE NOT NULL,
                    event_id VARCHAR(64),
                    account_id VARCHAR(64),
                    action_type VARCHAR(64) NOT NULL,
                    actor VARCHAR(64),
                    details JSONB,
                    ip_address INET,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_incident_account 
                ON incident_reports(account_id)
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_incident_created 
                ON incident_reports(created_at DESC)
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_account 
                ON audit_logs(account_id)
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_created 
                ON audit_logs(created_at DESC)
            """)
        
        self.conn.commit()
    
    async def save_incident_report(
        self,
        report: IncidentReport
    ) -> str:
        """
        Save incident report to database.
        
        Args:
            report: Incident report object
            
        Returns:
            Database record ID
        """
        loop = asyncio.get_event_loop()
        
        def _save():
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO incident_reports (
                        incident_id, event_id, account_id, decision_type,
                        risk_score, confidence, reason, requires_human_review,
                        sanctions_triggered, pipeline_error, metadata
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (incident_id) DO UPDATE SET
                        decision_type = EXCLUDED.decision_type,
                        risk_score = EXCLUDED.risk_score,
                        confidence = EXCLUDED.confidence,
                        reason = EXCLUDED.reason,
                        requires_human_review = EXCLUDED.requires_human_review,
                        sanctions_triggered = EXCLUDED.sanctions_triggered,
                        pipeline_error = EXCLUDED.pipeline_error,
                        metadata = EXCLUDED.metadata
                    RETURNING id
                """, (
                    report.incident_id,
                    report.event_id,
                    report.account_id,
                    report.decision.decision_type.value,
                    report.risk_score,
                    report.decision.confidence,
                    report.decision.reason,
                    report.decision.requires_human_review,
                    report.decision.sanctions_triggered,
                    report.decision.pipeline_error,
                    json.dumps(report.metadata) if report.metadata else None
                ))
                
                result = cur.fetchone()
                self.conn.commit()
                
                return result['id']
        
        return await loop.run_in_executor(None, _save)
    
    async def get_incident_history(
        self,
        account_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Retrieve incident history for an account.
        
        Args:
            account_id: Account identifier
            limit: Maximum number of records
            
        Returns:
            List of incident records
        """
        loop = asyncio.get_event_loop()
        
        def _query():
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT * FROM incident_reports
                    WHERE account_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (account_id, limit))
                
                return cur.fetchall()
        
        return await loop.run_in_executor(None, _query)
    
    async def log_audit_event(
        self,
        log_id: str,
        event_id: Optional[str],
        account_id: Optional[str],
        action_type: str,
        actor: str,
        details: Dict[str, Any],
        ip_address: Optional[str] = None
    ):
        """Log an audit event."""
        loop = asyncio.get_event_loop()
        
        def _log():
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO audit_logs (
                        log_id, event_id, account_id, action_type,
                        actor, details, ip_address
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (log_id) DO NOTHING
                """, (
                    log_id,
                    event_id,
                    account_id,
                    action_type,
                    actor,
                    json.dumps(details),
                    ip_address
                ))
                
                self.conn.commit()
        
        await loop.run_in_executor(None, _log)
    
    async def get_pending_reviews(
        self,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get incidents requiring human review."""
        loop = asyncio.get_event_loop()
        
        def _query():
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT * FROM incident_reports
                    WHERE requires_human_review = TRUE
                    AND reviewed_at IS NULL
                    ORDER BY created_at ASC
                    LIMIT %s
                """, (limit,))
                
                return cur.fetchall()
        
        return await loop.run_in_executor(None, _query)
    
    async def update_incident_review(
        self,
        incident_id: str,
        reviewer_id: str,
        resolution_notes: str
    ):
        """Mark incident as reviewed."""
        loop = asyncio.get_event_loop()
        
        def _update():
            with self.conn.cursor() as cur:
                cur.execute("""
                    UPDATE incident_reports
                    SET 
                        reviewed_at = CURRENT_TIMESTAMP,
                        reviewer_id = %s,
                        resolution_notes = %s
                    WHERE incident_id = %s
                """, (reviewer_id, resolution_notes, incident_id))
                
                self.conn.commit()
        
        await loop.run_in_executor(None, _update)


# Factory functions
def get_qdrant_client() -> QdrantStorageClient:
    """Get Qdrant client instance."""
    return QdrantStorageClient()


def get_postgres_client() -> PostgresStorageClient:
    """Get PostgreSQL client instance."""
    return PostgresStorageClient()

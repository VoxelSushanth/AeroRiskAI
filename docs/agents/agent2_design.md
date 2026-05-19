# Agent 2: Contextual RAG Design

## Overview

Agent 2 provides Retrieval-Augmented Generation (RAG) capabilities for contextual risk assessment. It retrieves relevant compliance rules, news sentiment, user profiles, and sanctions data to enrich the decision-making process.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent 2: Contextual RAG                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐      ┌──────────────────┐            │
│  │ Compliance Rules │      │   News/Sentiment │            │
│  │    (Qdrant)      │      │   (Real-time)    │            │
│  └──────────────────┘      └──────────────────┘            │
│                                                             │
│  ┌──────────────────┐      ┌──────────────────┐            │
│  │  User Profiles   │      │   Sanctions List │            │
│  │  (Redis + Qdrant)│      │    (OFAC/SDN)    │            │
│  └──────────────────┘      └──────────────────┘            │
│                                                             │
│  ┌──────────────────┐                                       │
│  │Circuit Breakers  │                                       │
│  │   (Redis)        │                                       │
│  └──────────────────┘                                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. Vector Search (`vector_search.py`)

**Purpose**: Perform semantic search across compliance documents, historical cases, and trading patterns.

**Collections**:
- `compliance_rules`: Regulatory text embeddings
- `historical_cases`: Past enforcement actions
- `trading_patterns`: Known manipulation patterns
- `user_behavior`: Behavioral embeddings

**Search Implementation**:
```python
class VectorSearch:
    def __init__(self, qdrant_client):
        self.client = qdrant_client
    
    async def search_compliance(
        self, 
        query: str, 
        top_k: int = 5,
        filters: Optional[Filter] = None
    ) -> List[ComplianceResult]:
        # Generate query embedding
        query_embedding = await self.embedder.encode(query)
        
        # Search Qdrant
        results = await self.client.search(
            collection_name="compliance_rules",
            query_vector=query_embedding.tolist(),
            limit=top_k,
            score_threshold=0.6,
            query_filter=filters
        )
        
        return [
            ComplianceResult(
                text=r.payload["text"],
                regulation=r.payload["regulation"],
                section=r.payload["section"],
                relevance_score=r.score,
                metadata=r.payload
            )
            for r in results
        ]
    
    async def search_similar_cases(
        self,
        event_features: Dict[str, Any],
        top_k: int = 3
    ) -> List[HistoricalCase]:
        embedding = await self.embedder.encode(json.dumps(event_features))
        
        results = await self.client.search(
            collection_name="historical_cases",
            query_vector=embedding.tolist(),
            limit=top_k,
            score_threshold=0.7
        )
        
        return [self._parse_case(r) for r in results]
```

### 2. Compliance Loader (`compliance_loader.py`)

**Purpose**: Load and index regulatory documents from multiple jurisdictions.

**Supported Regulations**:
- **MiFID II** (EU Markets in Financial Instruments Directive)
- **FINRA Rules** (US Financial Industry Regulatory Authority)
- **SOX Controls** (Sarbanes-Oxley Act)
- **SEC Regulations** (Securities and Exchange Commission)
- **FCA Handbook** (UK Financial Conduct Authority)

**Document Processing Pipeline**:
```python
class ComplianceLoader:
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50
        )
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
    
    async def load_and_index(self, document_path: str, regulation: str):
        # Read document
        with open(document_path, 'r') as f:
            text = f.read()
        
        # Split into chunks
        chunks = self.text_splitter.split_text(text)
        
        # Generate embeddings and metadata
        documents = []
        for i, chunk in enumerate(chunks):
            embedding = self.embedder.encode(chunk)
            
            # Extract metadata using regex
            metadata = self._extract_metadata(chunk, regulation)
            
            documents.append(
                PointStruct(
                    id=f"{regulation}_{i}",
                    vector=embedding.tolist(),
                    payload={
                        "text": chunk,
                        "regulation": regulation,
                        "section": metadata.get("section", ""),
                        "subsection": metadata.get("subsection", ""),
                        "effective_date": metadata.get("effective_date"),
                        "jurisdiction": self._get_jurisdiction(regulation)
                    }
                )
            )
        
        # Batch upload to Qdrant
        await self.qdrant_client.upsert(
            collection_name="compliance_rules",
            points=documents
        )
```

**Metadata Extraction**:
```python
def _extract_metadata(self, chunk: str, regulation: str) -> Dict:
    metadata = {}
    
    # Section pattern: "Section 1.2.3" or "Article 5"
    section_match = re.search(r'(?:Section|Article)\s+([\d.]+|\w+)', chunk)
    if section_match:
        metadata["section"] = section_match.group(1)
    
    # Subsection pattern: "(a)", "(b)", etc.
    subsection_match = re.search(r'\(([a-z])\)', chunk)
    if subsection_match:
        metadata["subsection"] = subsection_match.group(1)
    
    # Effective date pattern
    date_match = re.search(r'effective\s+(?:from\s+)?(\d{4}-\d{2}-\d{2})', chunk, re.I)
    if date_match:
        metadata["effective_date"] = date_match.group(1)
    
    return metadata
```

### 3. News Ingester (`news_ingester.py`)

**Purpose**: Real-time news ingestion and sentiment analysis for market-moving events.

**News Sources**:
- Reuters API
- Bloomberg Terminal
- Dow Jones Newswires
- SEC EDGAR filings
- Company press releases

**Sentiment Analysis**:
```python
class NewsIngester:
    def __init__(self):
        self.sentiment_model = pipeline(
            "sentiment-analysis",
            model="distilbert-base-uncased-finetuned-sst-2-english"
        )
        self.ner_model = pipeline(
            "ner",
            model="dslim/bert-base-NER"
        )
    
    async def process_news(self, article: NewsArticle) -> NewsContext:
        # Extract entities
        entities = self.ner_model(article.text)
        companies = self._extract_companies(entities)
        tickers = self._map_to_tickers(companies)
        
        # Analyze sentiment
        sentiment_result = self.sentiment_model(article.text[:512])[0]
        
        # Calculate market impact score
        impact_score = self._calculate_impact_score(
            sentiment=sentiment_result['score'],
            source_credibility=article.source_credibility,
            entity_count=len(tickers),
            urgency=article.urgency
        )
        
        return NewsContext(
            article_id=article.id,
            tickers=tickers,
            sentiment=sentiment_result['label'],
            sentiment_score=sentiment_result['score'],
            impact_score=impact_score,
            key_phrases=self._extract_key_phrases(article.text),
            timestamp=article.published_at,
            source=article.source
        )
    
    def _calculate_impact_score(
        self,
        sentiment: float,
        source_credibility: float,
        entity_count: int,
        urgency: str
    ) -> float:
        urgency_weights = {"CRITICAL": 1.0, "HIGH": 0.8, "MEDIUM": 0.5, "LOW": 0.2}
        
        score = (
            abs(sentiment) * 0.3 +
            source_credibility * 0.3 +
            min(entity_count / 10, 1.0) * 0.2 +
            urgency_weights.get(urgency, 0.5) * 0.2
        )
        
        return min(score, 1.0)
```

### 4. User Profile (`user_profile.py`)

**Purpose**: Maintain and retrieve comprehensive user trading profiles.

**Profile Data**:
```python
@dataclass
class UserProfile:
    account_id: str
    customer_type: str  # RETAIL, INSTITUTIONAL, MARKET_MAKER, HFT
    risk_tolerance: str  # LOW, MEDIUM, HIGH
    trading_experience_years: int
    typical_order_size: Decimal
    typical_daily_volume: Decimal
    preferred_symbols: List[str]
    trading_hours: Tuple[time, time]
    historical_violations: List[ViolationRecord]
    kyc_status: str  # VERIFIED, PENDING, FLAGGED
    jurisdiction: str
    created_at: datetime
    updated_at: datetime
    
    # Computed metrics
    velocity_score: float
    sophistication_score: float
    risk_score: float
```

**Profile Retrieval**:
```python
class UserProfileManager:
    def __init__(self, redis_client, qdrant_client):
        self.redis = redis_client
        self.qdrant = qdrant_client
    
    async def get_profile(self, account_id: str) -> UserProfile:
        # Try Redis cache first
        cached = await self.redis.get(f"profile:{account_id}")
        if cached:
            return UserProfile.from_json(cached)
        
        # Fall back to Qdrant
        result = await self.qdrant.retrieve(
            collection_name="user_profiles",
            ids=[account_id]
        )
        
        if result:
            profile = UserProfile.from_dict(result[0].payload)
            # Cache for next time
            await self.redis.setex(
                f"profile:{account_id}",
                300,  # 5 minutes
                profile.to_json()
            )
            return profile
        
        raise ProfileNotFoundError(account_id)
    
    async def update_profile(self, profile: UserProfile):
        # Update Qdrant
        await self.qdrant.upsert(
            collection_name="user_profiles",
            points=[profile.to_point()]
        )
        
        # Invalidate cache
        await self.redis.delete(f"profile:{profile.account_id}")
```

**Behavioral Embeddings**:
```python
async def generate_behavioral_embedding(self, profile: UserProfile) -> List[float]:
    features = {
        "customer_type": profile.customer_type,
        "avg_order_size": float(profile.typical_order_size),
        "avg_daily_volume": float(profile.typical_daily_volume),
        "trade_frequency": profile.trades_per_day,
        "cancel_ratio": profile.cancel_ratio,
        "holding_period": profile.avg_holding_period_hours,
        "symbols_concentration": profile.symbol_concentration,
        "time_of_day_pattern": profile.trading_time_distribution
    }
    
    embedding = self.embedder.encode(json.dumps(features, sort_keys=True))
    return embedding.tolist()
```

### 5. Sanctions Screening (`sanctions.py`)

**Purpose**: Screen counterparties against global sanctions lists.

**Sanctions Lists**:
- **OFAC SDN** (US Office of Foreign Assets Control - Specially Designated Nationals)
- **UN Consolidated List** (United Nations Security Council)
- **EU Consolidated List** (European Union)
- **HMT Consolidated List** (UK HM Treasury)
- **DFAT Consolidated List** (Australia)

**Screening Algorithm**:
```python
class SanctionsScreener:
    def __init__(self):
        self.fuzzy_matcher = FuzzyMatch(threshold=0.85)
        self.alias_expander = AliasExpander()
    
    async def screen_counterparty(
        self,
        name: str,
        country: str,
        date_of_birth: Optional[str] = None
    ) -> SanctionsResult:
        # Expand aliases and variations
        name_variations = self.alias_expander.expand(name)
        
        # Check each sanctions list
        matches = []
        for list_name in ["OFAC", "UN", "EU", "HMT", "DFAT"]:
            list_matches = await self._search_list(
                list_name=list_name,
                names=name_variations,
                country=country,
                dob=date_of_birth
            )
            matches.extend(list_matches)
        
        if matches:
            return SanctionsResult(
                is_sanctioned=True,
                matched_lists=[m.list_name for m in matches],
                match_details=matches,
                recommendation="BLOCK",
                confidence=max(m.confidence for m in matches)
            )
        
        return SanctionsResult(
            is_sanctioned=False,
            matched_lists=[],
            match_details=[],
            recommendation="ALLOW",
            confidence=1.0
        )
    
    async def _search_list(
        self,
        list_name: str,
        names: List[str],
        country: str,
        dob: Optional[str]
    ) -> List[SanctionsMatch]:
        matches = []
        
        for entry in self.sanctions_cache[list_name]:
            for name_variant in names:
                name_score = self.fuzzy_matcher.match(
                    name_variant,
                    entry.primary_name
                )
                
                # Also check aliases
                alias_scores = [
                    self.fuzzy_matcher.match(name_variant, alias)
                    for alias in entry.aliases
                ]
                best_alias_score = max(alias_scores) if alias_scores else 0
                
                best_name_score = max(name_score, best_alias_score)
                
                if best_name_score >= 0.85:
                    # Additional checks for country and DOB
                    country_match = entry.country == country
                    dob_match = dob is None or entry.dob == dob
                    
                    confidence = (
                        best_name_score * 0.6 +
                        (1.0 if country_match else 0.0) * 0.2 +
                        (1.0 if dob_match else 0.0) * 0.2
                    )
                    
                    if confidence >= 0.8:
                        matches.append(SanctionsMatch(
                            list_name=list_name,
                            entity_name=entry.primary_name,
                            confidence=confidence,
                            reasons=self._generate_reasons(name_score, country_match, dob_match)
                        ))
        
        return matches
```

## Output Schema

```python
@dataclass
class RAGContext:
    timestamp: int
    account_id: str
    symbol: Optional[str]
    
    # Compliance context
    relevant_rules: List[ComplianceResult]
    similar_cases: List[HistoricalCase]
    
    # News context
    recent_news: List[NewsContext]
    market_sentiment: str  # POSITIVE, NEGATIVE, NEUTRAL
    sentiment_score: float
    
    # User context
    user_profile: UserProfile
    behavioral_anomalies: List[str]
    
    # Sanctions context
    sanctions_result: SanctionsResult
    
    # Circuit breaker context
    circuit_breakers: List[CircuitBreakerStatus]
    
    # Aggregated risk indicators
    risk_indicators: List[RiskIndicator]
```

## Performance Requirements

| Metric | Target | Measurement |
|--------|--------|-------------|
| Vector Search Latency | <10ms p99 | Per query |
| Sanctions Check Latency | <50ms p99 | Full screening |
| Profile Retrieval Latency | <5ms p99 | Cached |
| News Processing Latency | <100ms | Per article |
| Throughput | >50k queries/sec | Aggregate |

## Integration with LangGraph

```python
def agent2_node(state: GraphState) -> GraphState:
    event = state["current_event"]
    
    # Parallel retrieval
    results = await asyncio.gather(
        vector_search.search_compliance(event.description),
        user_profile_manager.get_profile(event.account_id),
        sanctions_screener.screen(event.counterparty),
        news_ingester.get_relevant_news(event.symbol),
        circuit_breaker_manager.get_status(event.symbol)
    )
    
    state["rag_context"] = RAGContext(
        relevant_rules=results[0],
        user_profile=results[1],
        sanctions_result=results[2],
        recent_news=results[3],
        circuit_breakers=results[4]
    )
    
    return state
```

## Monitoring & Alerting

**Prometheus Metrics**:
```python
rag_retrieval_latency = Histogram(
    'agent2_retrieval_latency_seconds',
    'RAG retrieval latency',
    ['source']  # qdrant, redis, sanctions, news
)

sanctions_match_count = Counter(
    'agent2_sanctions_matches_total',
    'Total sanctions matches',
    ['list_name', 'confidence_bucket']
)

cache_hit_rate = Gauge(
    'agent2_cache_hit_rate',
    'Cache hit rate for profile lookups'
)
```

## Testing Strategy

1. **Unit Tests**: Test each retrieval component
2. **Integration Tests**: Test end-to-end RAG pipeline
3. **Accuracy Tests**: Validate sanctions matching accuracy
4. **Load Tests**: Verify performance under load
5. **Regression Tests**: Ensure no false negatives on known cases

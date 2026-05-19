# ADR-004: Qdrant for Vector Search

## Status
Accepted

## Context
The RAG pipeline requires sub-10ms vector similarity search for:
- Compliance document retrieval
- User profile matching
- Historical pattern detection
- Sanctions list screening

## Decision
We will use Qdrant instead of alternatives (Pinecone, Weaviate, Milvus) because:

### Advantages
- **Written in Rust**: Excellent performance, no GC pauses
- **HNSW Index**: O(log n) search with high recall
- **Filtering Support**: Pre-filter before search (critical for compliance)
- **Self-Hosted**: Full control over data, no vendor lock-in
- **gRPC + HTTP**: Multiple interface options
- **Quantization**: Reduced memory footprint with minimal accuracy loss

### Collection Design
```python
# Compliance documents collection
compliance_docs = VectorParams(
    size=768,  # BERT/embedding dimension
    distance=Distance.COSINE,
    hnsw_config=HnswConfig(
        m=16,
        ef_construct=100,
        full_scan_threshold=10000
    ),
    quantization_config=ScalarQuantization(
        type=ScalarType.INT8,
        quantile=0.99,
        always_ram=True
    )
)

# Payload schema
{
    "doc_id": str,
    "source": str,  # MiFID II, FINRA, SOX
    "section": str,
    "effective_date": datetime,
    "jurisdiction": List[str],
    "risk_category": str
}
```

## Consequences

### Positive
- Sub-5ms p95 latency for top-5 search
- Efficient filtering (e.g., "only EU regulations")
- Scalable to millions of vectors
- Low memory footprint with quantization

### Negative
- Additional infrastructure to manage
- Requires embedding pipeline maintenance
- Index building time for large datasets

## Performance Targets
| Metric | Target |
|--------|--------|
| Search Latency (p95) | <10ms |
| Search Latency (p99) | <20ms |
| Recall@10 | >0.95 |
| Index Build Time | <1 hour for 1M docs |

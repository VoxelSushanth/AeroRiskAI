#!/usr/bin/env python3
"""
Seed Qdrant with compliance documents and sanctions data.
"""

import os
import json
from typing import List, Dict, Any

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        VectorParams, Distance, PointStruct,
        HnswConfigDiff, ScalarQuantization, ScalarType, ScalarQuantizationConfig,
        Filter, FieldCondition, MatchValue
    )
except ImportError:
    print("qdrant-client not installed. Install with: pip install qdrant-client")
    exit(1)


def get_embedding(text: str) -> List[float]:
    """
    Generate embedding for text.
    In production, use a real embedding model (e.g., sentence-transformers).
    For seeding, return a deterministic pseudo-embedding.
    """
    # Simple hash-based pseudo-embedding for demonstration
    # Replace with actual embedding model in production
    import hashlib
    hash_bytes = hashlib.sha256(text.encode()).digest()
    # Convert to 768-dimensional vector
    embedding = []
    for i in range(768):
        byte_idx = i % len(hash_bytes)
        embedding.append((hash_bytes[byte_idx] - 128) / 128.0)
    return embedding


def load_compliance_docs(compliance_dir: str) -> List[Dict[str, Any]]:
    """Load compliance documents from directory."""
    docs = []
    
    for filename in os.listdir(compliance_dir):
        if not filename.endswith('.txt'):
            continue
            
        filepath = os.path.join(compliance_dir, filename)
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Parse document into sections
        source = filename.replace('.txt', '').upper()
        sections = content.split('## ')
        
        for section in sections[1:]:  # Skip header
            lines = section.strip().split('\n')
            if not lines:
                continue
                
            title = lines[0].strip()
            body = '\n'.join(lines[1:]).strip()
            
            docs.append({
                "doc_id": f"{source}-{title[:20].replace(' ', '_')}",
                "source": source,
                "section": title,
                "content": body,
                "full_text": f"{title}: {body}"
            })
    
    return docs


def load_sanctions(sanctions_file: str) -> List[Dict[str, Any]]:
    """Load sanctions list from CSV."""
    import csv
    entities = []
    
    with open(sanctions_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            entities.append({
                "entity_id": f"SDN-{row['entity_number']}",
                "name": row['name'],
                "type": row['type'],
                "programs": row['programs'],
                "remarks": row.get('remarks', ''),
                "full_text": f"{row['name']} - {row['type']} - {row['programs']} - {row.get('remarks', '')}"
            })
    
    return entities


def seed_qdrant():
    """Main seeding function."""
    # Configuration
    qdrant_host = os.getenv('QDRANT_HOST', 'localhost')
    qdrant_port = int(os.getenv('QDRANT_PORT', '6333'))
    compliance_dir = os.getenv('COMPLIANCE_RULES_PATH', '../seed/compliance_rules')
    sanctions_file = os.getenv('OFAC_SDN_FILE_PATH', '../seed/sanctions/ofac_sdn_sample.csv')
    
    # Initialize client
    print(f"Connecting to Qdrant at {qdrant_host}:{qdrant_port}...")
    client = QdrantClient(host=qdrant_host, port=qdrant_port)
    
    # Create compliance documents collection
    compliance_collection = "compliance_docs"
    print(f"Creating collection: {compliance_collection}")
    
    try:
        client.delete_collection(compliance_collection)
    except Exception:
        pass
    
    client.create_collection(
        collection_name=compliance_collection,
        vectors_config=VectorParams(
            size=768,
            distance=Distance.COSINE,
            hnsw_config=HnswConfigDiff(
                m=16,
                ef_construct=100,
            ),
            quantization_config=ScalarQuantization(
                scalar=ScalarQuantizationConfig(
                    type=ScalarType.INT8,
                    quantile=0.99,
                    always_ram=True
                )
            )
        )
    )
    
    # Load and index compliance documents
    print("Loading compliance documents...")
    docs = load_compliance_docs(compliance_dir)
    print(f"Loaded {len(docs)} document sections")
    
    points = []
    for doc in docs:
        embedding = get_embedding(doc['full_text'])
        points.append(PointStruct(
            id=hash(doc['doc_id']) % (2**63),
            vector=embedding,
            payload=doc
        ))
    
    print(f"Upserting {len(points)} compliance documents...")
    client.upsert(collection_name=compliance_collection, points=points)
    
    # Create sanctions collection
    sanctions_collection = "sanctions_list"
    print(f"Creating collection: {sanctions_collection}")
    
    try:
        client.delete_collection(sanctions_collection)
    except Exception:
        pass
    
    client.create_collection(
        collection_name=sanctions_collection,
        vectors_config=VectorParams(
            size=768,
            distance=Distance.COSINE
        )
    )
    
    # Load and index sanctions
    print("Loading sanctions list...")
    entities = load_sanctions(sanctions_file)
    print(f"Loaded {len(entities)} sanctioned entities")
    
    points = []
    for entity in entities:
        embedding = get_embedding(entity['full_text'])
        points.append(PointStruct(
            id=hash(entity['entity_id']) % (2**63),
            vector=embedding,
            payload=entity
        ))
    
    print(f"Upserting {len(points)} sanctioned entities...")
    client.upsert(collection_name=sanctions_collection, points=points)
    
    # Create user profiles collection
    profiles_collection = "user_profiles"
    print(f"Creating collection: {profiles_collection}")
    
    try:
        client.delete_collection(profiles_collection)
    except Exception:
        pass
    
    client.create_collection(
        collection_name=profiles_collection,
        vectors_config=VectorParams(
            size=768,
            distance=Distance.COSINE
        )
    )
    
    # Load user profiles
    profiles_file = os.getenv('USER_PROFILES_PATH', '../seed/user_profiles/synthetic_profiles.json')
    with open(profiles_file, 'r') as f:
        profiles_data = json.load(f)
    
    profiles = profiles_data.get('profiles', [])
    print(f"Loaded {len(profiles)} user profiles")
    
    points = []
    for profile in profiles:
        profile_text = f"{profile['name']} - {profile['type']} - {profile['risk_tolerance']} - {profile['investment_objectives']}"
        embedding = get_embedding(profile_text)
        points.append(PointStruct(
            id=hash(profile['user_id']) % (2**63),
            vector=embedding,
            payload=profile
        ))
    
    print(f"Upserting {len(points)} user profiles...")
    client.upsert(collection_name=profiles_collection, points=points)
    
    print("\n✅ Qdrant seeding completed successfully!")
    print(f"   - Compliance documents: {len(docs)}")
    print(f"   - Sanctioned entities: {len(entities)}")
    print(f"   - User profiles: {len(profiles)}")


if __name__ == "__main__":
    seed_qdrant()

"""
Embedding utilities for anomaly similarity search.
"""

import hashlib
import struct
from typing import List


class EmbeddingGenerator:
    """Generate simple embeddings for order events."""

    def __init__(self, embedding_dim: int = 128):
        self.embedding_dim = embedding_dim

    def generate_order_embedding(
        self,
        account_id: str,
        symbol: str,
        side: str,
        price: int,
        quantity: int,
        timestamp: float,
    ) -> List[float]:
        """Generate a fixed-size embedding for an order."""
        # Create feature vector from order attributes
        features = []

        # Hash account_id to numeric features
        account_hash = hashlib.md5(account_id.encode()).digest()
        for i in range(0, min(16, len(account_hash)), 4):
            val = struct.unpack("<I", account_hash[i : i + 4])[0]
            features.append((val % 1000) / 1000.0)

        # Hash symbol
        symbol_hash = hashlib.md5(symbol.encode()).digest()
        for i in range(0, min(8, len(symbol_hash)), 4):
            val = struct.unpack("<I", symbol_hash[i : i + 4])[0]
            features.append((val % 1000) / 1000.0)

        # Side encoding
        features.append(1.0 if side == "BUY" else 0.0)

        # Normalized price (log scale approximation)
        if price > 0:
            price_norm = min(1.0, (price % 1000000) / 1000000.0)
            features.append(price_norm)
        else:
            features.append(0.0)

        # Normalized quantity
        if quantity > 0:
            qty_norm = min(1.0, (quantity % 1000000) / 1000000.0)
            features.append(qty_norm)
        else:
            features.append(0.0)

        # Time-based features (hour of day, day of week)
        hour = int((timestamp % 86400) / 3600)
        features.append(hour / 24.0)

        # Pad to embedding_dim
        while len(features) < self.embedding_dim:
            features.append(0.0)

        return features[: self.embedding_dim]

    def cosine_similarity(self, emb1: List[float], emb2: List[float]) -> float:
        """Calculate cosine similarity between two embeddings."""
        if len(emb1) != len(emb2):
            raise ValueError("Embeddings must have same dimension")

        dot_product = sum(a * b for a, b in zip(emb1, emb2))
        norm1 = sum(a * a for a in emb1) ** 0.5
        norm2 = sum(b * b for b in emb2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

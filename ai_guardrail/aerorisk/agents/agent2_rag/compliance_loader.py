"""Compliance rules loader for RAG agent."""

import json
from pathlib import Path
from typing import Optional, Any
from aerorisk.models.context_bundle import ComplianceRule
from aerorisk.storage.qdrant_client import QdrantVectorClient
import logging

logger = logging.getLogger(__name__)


class ComplianceLoader:
    """Load and index compliance rules from files."""

    def __init__(
        self,
        qdrant_client: Optional[QdrantVectorClient] = None,
        rules_dir: str = "data/seed/compliance_rules",
    ):
        self.qdrant = qdrant_client or QdrantVectorClient()
        self.rules_dir = Path(rules_dir)

    async def load_all_rules(self) -> int:
        """Load all compliance rules from files into vector store."""
        total_loaded = 0
        
        if not self.rules_dir.exists():
            logger.warning(f"Rules directory not found: {self.rules_dir}")
            return 0
        
        for rule_file in self.rules_dir.glob("*.txt"):
            try:
                count = await self._load_rule_file(rule_file)
                total_loaded += count
                logger.info(f"Loaded {count} rules from {rule_file.name}")
            except Exception as e:
                logger.error(f"Failed to load {rule_file}: {e}")
        
        return total_loaded

    async def _load_rule_file(self, file_path: Path) -> int:
        """Load rules from a single file."""
        source = file_path.stem  # e.g., "mifid2_excerpts"
        rules = []
        
        with open(file_path, "r") as f:
            content = f.read()
        
        # Parse rules (assuming one rule per section separated by blank lines)
        sections = content.split("\n\n")
        
        for i, section in enumerate(sections):
            section = section.strip()
            if not section:
                continue
            
            rule_id = f"{source}_{i}"
            
            # Index in Qdrant
            await self.qdrant.upsert_document(
                collection_name="compliance_rules",
                document_id=rule_id,
                text=section,
                payload={
                    "rule_id": rule_id,
                    "source": source,
                    "content": section,
                },
            )
            rules.append(rule_id)
        
        return len(rules)

    def parse_mifid2_rules(self, content: str) -> list[dict[str, Any]]:
        """Parse MiFID II specific rule format."""
        rules = []
        lines = content.split("\n")
        
        current_rule = {"sections": []}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith("Article") or line.startswith("Section"):
                if current_rule.get("title"):
                    rules.append(current_rule)
                current_rule = {
                    "title": line,
                    "sections": [],
                }
            else:
                current_rule["sections"].append(line)
        
        if current_rule.get("title"):
            rules.append(current_rule)
        
        return rules

    def parse_finra_rules(self, content: str) -> list[dict[str, Any]]:
        """Parse FINRA rule format."""
        rules = []
        lines = content.split("\n")
        
        current_rule = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith("Rule ") and ":" in line:
                if current_rule:
                    rules.append(current_rule)
                
                parts = line.split(":", 1)
                current_rule = {
                    "rule_number": parts[0].replace("Rule ", ""),
                    "title": parts[1] if len(parts) > 1 else "",
                    "content": [],
                }
            elif current_rule:
                current_rule["content"].append(line)
        
        if current_rule:
            rules.append(current_rule)
        
        return rules

    async def get_rules_by_source(self, source: str) -> list[ComplianceRule]:
        """Retrieve rules filtered by source."""
        results = await self.qdrant.search_similar(
            collection_name="compliance_rules",
            query_text=f"rules from {source}",
            limit=100,
        )
        
        return [
            ComplianceRule(
                rule_id=r.payload.get("rule_id", ""),
                source=r.payload.get("source", ""),
                content=r.payload.get("content", ""),
                relevance_score=r.score,
            )
            for r in results
            if r.payload.get("source") == source
        ]

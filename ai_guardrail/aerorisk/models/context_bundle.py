"""
Context bundle models for RAG retrieval.
"""

from pydantic import BaseModel, Field
from typing import Any


class ComplianceRule(BaseModel):
    """Compliance rule retrieved from vector store."""

    rule_id: str
    title: str
    content: str
    jurisdiction: str
    category: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    source: str
    similarity_score: float = Field(ge=0.0, le=1.0)


class NewsItem(BaseModel):
    """News item for market context."""

    news_id: str
    headline: str
    summary: str
    source: str
    published_at: float
    sentiment: float = Field(ge=-1.0, le=1.0)
    relevance_score: float = Field(ge=0.0, le=1.0)
    symbols: list[str] = Field(default_factory=list)


class UserProfile(BaseModel):
    """User profile for risk assessment."""

    user_id: str
    account_type: str  # RETAIL, INSTITUTIONAL, MARKET_MAKER
    risk_tolerance: str  # LOW, MEDIUM, HIGH
    trading_experience_years: int
    avg_daily_volume: int
    max_position_size: int
    restricted_symbols: list[str] = Field(default_factory=list)
    kyc_status: str  # VERIFIED, PENDING, EXPIRED
    sanctions_checked_at: float | None = None


class SanctionsMatch(BaseModel):
    """Sanctions list match result."""

    match_id: str
    entity_name: str
    list_name: str  # OFAC_SDN, UN_SANCTIONS, EU_SANCTIONS
    match_score: float = Field(ge=0.0, le=1.0)
    match_type: str  # EXACT, FUZZY, ALIAS
    source_details: dict[str, Any] = Field(default_factory=dict)


class ContextBundle(BaseModel):
    """Aggregated context from all RAG sources."""

    compliance_rules: list[ComplianceRule] = Field(default_factory=list)
    news_items: list[NewsItem] = Field(default_factory=list)
    user_profile: UserProfile | None = None
    sanctions_matches: list[SanctionsMatch] = Field(default_factory=list)
    circuit_breaker_status: dict[str, Any] = Field(default_factory=dict)

    @property
    def has_sanctions_match(self) -> bool:
        """Check if any sanctions matches exist."""
        return len(self.sanctions_matches) > 0

    @property
    def highest_severity_rule(self) -> ComplianceRule | None:
        """Get the highest severity compliance rule."""
        if not self.compliance_rules:
            return None

        severity_order = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
        return max(
            self.compliance_rules,
            key=lambda r: severity_order.get(r.severity, 0),
        )

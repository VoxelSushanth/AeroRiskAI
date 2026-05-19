"""
Risk decision models from the orchestrator agent.
"""

from enum import Enum
from pydantic import BaseModel, Field
from typing import Any


class RiskDecisionType(str, Enum):
    """Allowed risk decisions."""

    ALLOW = "ALLOW"
    FLAG = "FLAG"
    BLOCK = "BLOCK"
    ADJUST_LIMIT = "ADJUST_LIMIT"


class RiskDecision(BaseModel):
    """Final risk decision from the AI orchestrator."""

    decision_id: str
    order_id: str | None = None
    account_id: str
    decision: RiskDecisionType
    risk_score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)

    # Decision rationale
    reasons: list[str] = Field(default_factory=list)
    anomaly_findings: list[dict[str, Any]] = Field(default_factory=list)
    compliance_issues: list[dict[str, Any]] = Field(default_factory=list)

    # Special flags
    sanctions_match: bool = False
    requires_human_review: bool = False

    # Actions
    adjusted_limit: int | None = None  # For ADJUST_LIMIT decisions
    circuit_breaker_trigger: bool = False
    incident_report_id: str | None = None

    # Metadata
    agent_version: str = "v1.0.0"
    model_name: str | None = None
    processing_time_ms: float | None = None
    timestamp: float | None = None

    class Config:
        use_enum_values = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = self.model_dump()
        if "decision" in data and hasattr(data["decision"], "value"):
            data["decision"] = data["decision"].value
        return data

    @classmethod
    def create_block_decision(
        cls,
        account_id: str,
        order_id: str | None = None,
        reason: str = "Risk threshold exceeded",
        sanctions_match: bool = False,
    ) -> "RiskDecision":
        """Factory method for creating BLOCK decisions."""
        return cls(
            decision_id=f"DEC-BLOCK-{account_id}-{order_id or 'UNKNOWN'}",
            order_id=order_id,
            account_id=account_id,
            decision=RiskDecisionType.BLOCK,
            risk_score=1.0,
            confidence=0.99,
            reasons=[reason],
            sanctions_match=sanctions_match,
            circuit_breaker_trigger=True,
            requires_human_review=sanctions_match,
        )

    @classmethod
    def create_allow_decision(
        cls,
        account_id: str,
        order_id: str | None = None,
        risk_score: float = 0.0,
    ) -> "RiskDecision":
        """Factory method for creating ALLOW decisions."""
        return cls(
            decision_id=f"DEC-ALLOW-{account_id}-{order_id or 'UNKNOWN'}",
            order_id=order_id,
            account_id=account_id,
            decision=RiskDecisionType.ALLOW,
            risk_score=risk_score,
            confidence=0.95,
            reasons=["No risk indicators detected"],
        )

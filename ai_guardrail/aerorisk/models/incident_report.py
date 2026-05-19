"""
Incident report models for compliance auditing.
"""

from enum import Enum
from pydantic import BaseModel, Field
from typing import Any
import hashlib
import json


class IncidentSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class IncidentStatus(str, Enum):
    OPEN = "OPEN"
    UNDER_REVIEW = "UNDER_REVIEW"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"


class IncidentType(str, Enum):
    FRAUD_SUSPECTED = "FRAUD_SUSPECTED"
    SANCTIONS_VIOLATION = "SANCTIONS_VIOLATION"
    MARKET_MANIPULATION = "MARKET_MANIPULATION"
    COMPLIANCE_BREACH = "COMPLIANCE_BREACH"
    VELOCITY_VIOLATION = "VELOCITY_VIOLATION"
    WASH_TRADE = "WASH_TRADE"
    SPOOFING = "SPOOFING"


class IncidentReport(BaseModel):
    """Incident report for compliance and audit purposes."""

    incident_id: str
    incident_type: IncidentType
    severity: IncidentSeverity
    status: IncidentStatus = IncidentStatus.OPEN

    # Related entities
    account_id: str
    order_id: str | None = None
    trade_ids: list[str] = Field(default_factory=list)

    # Timeline
    detected_at: float
    reported_at: float | None = None
    resolved_at: float | None = None

    # Details
    description: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    anomaly_findings: list[dict[str, Any]] = Field(default_factory=list)
    compliance_violations: list[str] = Field(default_factory=list)

    # Actions taken
    actions_taken: list[str] = Field(default_factory=list)
    circuit_breaker_triggered: bool = False
    account_restricted: bool = False

    # Assignment
    assigned_to: str | None = None
    reviewer_comments: str | None = None

    # Audit trail
    checksum: str | None = None
    version: int = 1

    class Config:
        use_enum_values = True

    def model_dump(self, *args, **kwargs):
        """Override to handle enum serialization."""
        data = super().model_dump(*args, **kwargs)
        for field in ["incident_type", "severity", "status"]:
            if field in data and hasattr(data[field], "value"):
                data[field] = data[field].value
        return data

    def compute_checksum(self) -> str:
        """Compute SHA256 checksum of incident data for audit integrity."""
        data = {
            "incident_id": self.incident_id,
            "incident_type": self.incident_type.value
            if hasattr(self.incident_type, "value")
            else self.incident_type,
            "account_id": self.account_id,
            "detected_at": self.detected_at,
            "evidence": self.evidence,
            "actions_taken": self.actions_taken,
        }
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()

    def finalize(self) -> None:
        """Finalize the incident report with checksum."""
        self.checksum = self.compute_checksum()

    @classmethod
    def create_from_risk_decision(
        cls,
        risk_decision: Any,
        anomaly_findings: list[dict[str, Any]],
    ) -> "IncidentReport":
        """Create incident report from a risk decision."""
        # Determine incident type based on findings
        incident_type = IncidentType.FRAUD_SUSPECTED
        if risk_decision.sanctions_match:
            incident_type = IncidentType.SANCTIONS_VIOLATION
        elif any(f.get("anomaly_type") == "wash_trade" for f in anomaly_findings):
            incident_type = IncidentType.WASH_TRADE
        elif any(f.get("anomaly_type") == "spoofing" for f in anomaly_findings):
            incident_type = IncidentType.SPOOFING

        # Determine severity
        severity = IncidentSeverity.MEDIUM
        if risk_decision.sanctions_match or risk_decision.risk_score > 0.8:
            severity = IncidentSeverity.CRITICAL
        elif risk_decision.risk_score > 0.5:
            severity = IncidentSeverity.HIGH

        import time

        report = cls(
            incident_id=f"INC-{risk_decision.account_id}-{int(time.time())}",
            incident_type=incident_type,
            severity=severity,
            status=IncidentStatus.OPEN,
            account_id=risk_decision.account_id,
            order_id=risk_decision.order_id,
            detected_at=time.time(),
            description=f"Automated detection: {', '.join(risk_decision.reasons)}",
            evidence=risk_decision.model_dump() if hasattr(risk_decision, "model_dump") else {},
            anomaly_findings=anomaly_findings,
            actions_taken=["Circuit breaker triggered"] if risk_decision.circuit_breaker_trigger else [],
            circuit_breaker_triggered=risk_decision.circuit_breaker_trigger,
            account_restricted=risk_decision.decision == "BLOCK",
        )
        report.finalize()
        return report

"""
Anomaly detection result models.
"""

from enum import Enum
from pydantic import BaseModel, Field
from typing import Any


class AnomalyType(str, Enum):
    """Types of detected anomalies."""

    VELOCITY_VIOLATION = "velocity_violation"
    VWAP_DEVIATION = "vwap_deviation"
    WASH_TRADE = "wash_trade"
    SPOOFING = "spoofing"
    SANCTIONS_MATCH = "sanctions_match"
    COMPLIANCE_VIOLATION = "compliance_violation"
    UNUSUAL_PATTERN = "unusual_pattern"


class AnomalyResult(BaseModel):
    """Result from a single anomaly detection check."""

    anomaly_type: AnomalyType
    is_anomalous: bool
    severity_score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    details: dict[str, Any] = Field(default_factory=dict)
    recommendation: str = "ALLOW"  # ALLOW, FLAG, BLOCK, ADJUST_LIMIT
    timestamp: float | None = None

    class Config:
        use_enum_values = True

    def model_dump(self, *args, **kwargs):
        """Override to handle enum serialization."""
        data = super().model_dump(*args, **kwargs)
        if "anomaly_type" in data and hasattr(data["anomaly_type"], "value"):
            data["anomaly_type"] = data["anomaly_type"].value
        return data

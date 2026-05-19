"""
Event models for the AeroRisk AI pipeline.
"""

from enum import Enum
from pydantic import BaseModel, Field


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderAction(str, Enum):
    SUBMIT = "SUBMIT"
    CANCEL = "CANCEL"
    FILL = "FILL"
    MODIFY = "MODIFY"


class EventType(str, Enum):
    ORDER = "ORDER"
    TRADE = "TRADE"
    RISK_DECISION = "RISK_DECISION"
    CIRCUIT_BREAKER = "CIRCUIT_BREAKER"
    AUDIT = "AUDIT"


class OrderEvent(BaseModel):
    """Order event from the matching engine."""

    order_id: str
    account_id: str
    symbol: str
    side: OrderSide
    action: OrderAction
    price: int  # Fixed-point (price * 10^6)
    quantity: int
    timestamp: float
    client_order_id: str | None = None
    user_agent: str | None = None
    ip_address: str | None = None

    class Config:
        use_enum_values = True


class TradeEvent(BaseModel):
    """Trade execution event."""

    trade_id: str
    order_id: str
    counterparty_order_id: str
    symbol: str
    price: int
    quantity: int
    buyer_account_id: str
    seller_account_id: str
    timestamp: float
    aggressor_side: OrderSide


class RiskDecisionEvent(BaseModel):
    """Risk decision from AI pipeline."""

    decision_id: str
    order_id: str | None = None
    account_id: str
    decision: str  # ALLOW, FLAG, BLOCK, ADJUST_LIMIT
    risk_score: float
    reasons: list[str] = Field(default_factory=list)
    sanctions_match: bool = False
    anomaly_flags: list[str] = Field(default_factory=list)
    timestamp: float
    agent_version: str = "v1.0.0"


class CircuitBreakerEvent(BaseModel):
    """Circuit breaker state change."""

    breaker_id: str
    account_id: str | None = None
    symbol: str | None = None
    state: str  # CLOSED, OPEN, HALF_OPEN
    trigger_reason: str
    triggered_at: float
    expires_at: float | None = None


class AuditEvent(BaseModel):
    """Audit log event."""

    audit_id: str
    event_type: EventType
    entity_id: str
    action: str
    actor: str
    details: dict
    timestamp: float
    checksum: str | None = None

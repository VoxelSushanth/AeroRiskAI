"""
LangGraph state definition for the AeroRisk AI pipeline.
"""

from typing import Annotated, Any
from typing_extensions import TypedDict
import operator

from aerorisk.models.event import OrderEvent
from aerorisk.models.anomaly_result import AnomalyResult
from aerorisk.models.context_bundle import ContextBundle
from aerorisk.models.risk_decision import RiskDecision


class PipelineState(TypedDict):
    """State passed through the LangGraph pipeline."""

    # Input event
    event: OrderEvent

    # Agent 1 outputs
    anomaly_results: list[AnomalyResult]
    anomaly_detected: bool
    max_anomaly_severity: float
    anomaly_types: list[str]
    anomaly_details: dict[str, Any]

    # Agent 2 outputs
    context_bundle: ContextBundle | None
    compliance_findings: list[dict[str, Any]]
    sanctions_check_result: dict[str, Any]

    # Agent 3 outputs
    risk_decision: RiskDecision | None
    decision_rationale: str
    incident_report_id: str | None

    # Metadata
    processing_start_time: float
    processing_end_time: float | None
    total_processing_time_ms: float | None
    errors: list[str]


def create_initial_state(event: OrderEvent) -> PipelineState:
    """Create initial pipeline state from an order event."""

    import time

    return PipelineState(
        event=event,
        anomaly_results=[],
        anomaly_detected=False,
        max_anomaly_severity=0.0,
        anomaly_types=[],
        anomaly_details={},
        context_bundle=None,
        compliance_findings=[],
        sanctions_check_result={},
        risk_decision=None,
        decision_rationale="",
        incident_report_id=None,
        processing_start_time=time.time(),
        processing_end_time=None,
        total_processing_time_ms=None,
        errors=[],
    )

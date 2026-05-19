"""
Agent 1: Anomaly Detection Agent
Detects velocity violations, VWAP deviations, wash trades, and spoofing patterns.
"""

from typing import Any
from langgraph.graph import StateGraph, END
from aerorisk.graph.state import PipelineState
from aerorisk.agents.agent1_anomaly.velocity_check import VelocityChecker
from aerorisk.agents.agent1_anomaly.vwap_monitor import VWAPMonitor
from aerorisk.agents.agent1_anomaly.wash_trade import WashTradeDetector
from aerorisk.agents.agent1_anomaly.spoofing_hmm import SpoofingDetector
from aerorisk.models.anomaly_result import AnomalyResult


class Agent1Anomaly:
    """Multi-strategy anomaly detection agent."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.velocity_checker = VelocityChecker(
            window_size=self.config.get("velocity_window", 60),
            max_orders_per_second=self.config.get("max_ops", 100),
        )
        self.vwap_monitor = VWAPMonitor(
            lookback_periods=self.config.get("vwap_lookback", 300),
            deviation_threshold=self.config.get("vwap_threshold", 0.05),
        )
        self.wash_trade_detector = WashTradeDetector(
            time_window_seconds=self.config.get("wash_trade_window", 300),
            min_round_trips=self.config.get("min_round_trips", 3),
        )
        self.spoofing_detector = SpoofingDetector(
            order_book_depth=self.config.get("order_book_depth", 10),
            cancellation_threshold=self.config.get("cancel_threshold", 0.8),
        )

    async def detect_anomalies(self, state: PipelineState) -> dict[str, Any]:
        """Run all anomaly detection strategies in parallel."""
        event = state["event"]
        account_id = event.account_id
        symbol = event.symbol

        results: list[AnomalyResult] = []

        # Velocity check
        velocity_result = await self.velocity_checker.check(event)
        if velocity_result.is_anomalous:
            results.append(velocity_result)

        # VWAP deviation
        vwap_result = await self.vwap_monitor.check(event)
        if vwap_result.is_anomalous:
            results.append(vwap_result)

        # Wash trade detection
        wash_result = await self.wash_trade_detector.check(event)
        if wash_result.is_anomalous:
            results.append(wash_result)

        # Spoofing detection
        spoof_result = await self.spoofing_detector.check(event)
        if spoof_result.is_anomalous:
            results.append(spoof_result)

        # Aggregate results
        max_severity = max((r.severity_score for r in results), default=0.0)
        anomaly_types = [r.anomaly_type for r in results]

        return {
            "anomaly_results": results,
            "anomaly_detected": len(results) > 0,
            "max_anomaly_severity": max_severity,
            "anomaly_types": anomaly_types,
            "anomaly_details": {
                "account_id": account_id,
                "symbol": symbol,
                "findings": [r.model_dump() for r in results],
            },
        }


def create_agent1_graph(config: dict[str, Any] | None = None) -> StateGraph:
    """Create LangGraph workflow for Agent 1."""
    agent = Agent1Anomaly(config)

    workflow = StateGraph(PipelineState)
    workflow.add_node("detect_anomalies", agent.detect_anomalies)
    workflow.set_entry_point("detect_anomalies")
    workflow.add_edge("detect_anomalies", END)

    return workflow.compile()

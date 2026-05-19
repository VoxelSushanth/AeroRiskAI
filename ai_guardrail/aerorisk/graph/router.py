"""
AeroRisk AI - Graph Router Module
Dynamic routing logic for multi-agent pipeline
"""

from typing import Literal, Optional
from aerorisk.graph.state import AgentState
from aerorisk.models.anomaly_result import AnomalyResult
from aerorisk.models.risk_decision import DecisionType


class PipelineRouter:
    """
    Handles dynamic routing decisions within the LangGraph pipeline.
    
    Determines which path to take based on:
    - Anomaly detection confidence
    - Sanctions match status
    - Risk score thresholds
    - Circuit breaker state
    """
    
    # Routing thresholds
    HIGH_RISK_CONFIDENCE_THRESHOLD = 0.85
    MEDIUM_RISK_CONFIDENCE_THRESHOLD = 0.50
    
    @classmethod
    def route_after_anomaly(
        cls, 
        state: AgentState
    ) -> Literal["high_risk", "suspicious", "normal"]:
        """
        Determine next node after anomaly detection.
        
        Args:
            state: Current agent state
            
        Returns:
            Route identifier for LangGraph conditional edges
        """
        anomaly_result = state.get("anomaly_result")
        
        if not anomaly_result:
            return "normal"
        
        # Check for high-confidence fraud
        if cls._is_high_confidence_fraud(anomaly_result):
            return "high_risk"
        
        # Check for medium-risk anomalies
        if cls._is_suspicious(anomaly_result):
            return "suspicious"
        
        return "normal"
    
    @classmethod
    def _is_high_confidence_fraud(cls, result: AnomalyResult) -> bool:
        """Check if anomaly indicates high-confidence fraud."""
        if result.confidence_score >= cls.HIGH_RISK_CONFIDENCE_THRESHOLD:
            return True
        
        # Specific fraud patterns that always trigger high-risk route
        high_risk_flags = {
            "sanctions_match",
            "confirmed_wash_trade",
            "spoofing_detected",
            "velocity_breach_critical"
        }
        
        return bool(set(result.flags) & high_risk_flags)
    
    @classmethod
    def _is_suspicious(cls, result: AnomalyResult) -> bool:
        """Check if anomaly indicates suspicious activity."""
        if result.confidence_score >= cls.MEDIUM_RISK_CONFIDENCE_THRESHOLD:
            return True
        
        # Medium-risk flags
        medium_risk_flags = {
            "velocity_warning",
            "vwap_deviation",
            "unusual_pattern",
            "new_counterparty"
        }
        
        return bool(set(result.flags) & medium_risk_flags)
    
    @classmethod
    def should_enrich_context(cls, state: AgentState) -> bool:
        """
        Determine if RAG context enrichment is needed.
        
        Skips enrichment for:
        - Clear low-risk transactions
        - Obvious high-confidence fraud (already decided)
        """
        anomaly_result = state.get("anomaly_result")
        
        if not anomaly_result:
            return True  # Enrich by default if no anomaly
        
        # Skip for obvious fraud - decision already clear
        if cls._is_high_confidence_fraud(anomaly_result):
            return False
        
        # Skip for clearly normal transactions
        if anomaly_result.confidence_score < 0.2 and not anomaly_result.flags:
            return False
        
        return True
    
    @classmethod
    def determine_decision_path(
        cls,
        state: AgentState
    ) -> Literal["auto_block", "auto_allow", "llm_review", "human_review"]:
        """
        Determine the decision-making path based on current state.
        
        Returns:
            Decision path identifier
        """
        anomaly_result = state.get("anomaly_result")
        context = state.get("context_bundle")
        
        # Auto-block conditions
        if context and context.sanctions_hit:
            return "auto_block"
        
        if anomaly_result and anomaly_result.confidence_score >= 0.95:
            if any(flag in anomaly_result.flags for flag in [
                "confirmed_wash_trade",
                "spoofing_detected",
                "sanctions_match"
            ]):
                return "auto_block"
        
        # Auto-allow conditions
        if (not anomaly_result or anomaly_result.confidence_score < 0.3) and \
           (not context or not context.sanctions_hit):
            return "auto_allow"
        
        # Human review for critical cases
        if context and context.user_profile:
            if context.user_profile.is_high_value_client:
                return "human_review"
        
        # Default to LLM review
        return "llm_review"
    
    @classmethod
    def get_priority_level(cls, state: AgentState) -> int:
        """
        Calculate processing priority (1=highest, 5=lowest).
        
        Used for queue prioritization in high-load scenarios.
        """
        anomaly_result = state.get("anomaly_result")
        context = state.get("context_bundle")
        
        # Priority 1: Sanctions match
        if context and context.sanctions_hit:
            return 1
        
        # Priority 2: High-confidence fraud
        if anomaly_result and anomaly_result.confidence_score >= 0.9:
            return 2
        
        # Priority 3: Suspicious activity
        if anomaly_result and anomaly_result.confidence_score >= 0.5:
            return 3
        
        # Priority 4: Low-risk anomalies
        if anomaly_result and anomaly_result.flags:
            return 4
        
        # Priority 5: Normal transactions
        return 5


# Convenience functions for use in LangGraph nodes
def route_after_anomaly(state: AgentState) -> str:
    """Standalone function for LangGraph conditional edge."""
    return PipelineRouter.route_after_anomaly(state)


def should_enrich_context(state: AgentState) -> bool:
    """Standalone function for conditional processing."""
    return PipelineRouter.should_enrich_context(state)


def get_decision_path(state: AgentState) -> str:
    """Standalone function for decision routing."""
    return PipelineRouter.determine_decision_path(state)

"""
AeroRisk AI - LangGraph Pipeline Implementation
Multi-agent risk orchestration with stateful processing
"""

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from typing import TypedDict, Annotated, List, Optional
import operator

from aerorisk.graph.state import AgentState, RiskDecisionState
from aerorisk.agents.agent1_anomaly.agent import AnomalyDetectionAgent
from aerorisk.agents.agent2_rag.agent import RAGContextAgent
from aerorisk.agents.agent3_orchestrator.agent import DecisionOrchestratorAgent
from aerorisk.models.event import TransactionEvent
from aerorisk.models.risk_decision import RiskDecision, DecisionType


class RiskPipeline:
    """
    LangGraph-based multi-agent pipeline for risk assessment.
    
    Flow:
    1. Parse incoming transaction event
    2. Run anomaly detection (Agent 1)
    3. Gather contextual data via RAG (Agent 2)
    4. Make final risk decision (Agent 3)
    5. Update circuit breakers and generate reports
    """
    
    def __init__(self):
        self.anomaly_agent = AnomalyDetectionAgent()
        self.rag_agent = RAGContextAgent()
        self.orchestrator = DecisionOrchestratorAgent()
        
        self._build_graph()
    
    def _build_graph(self):
        """Construct the LangGraph workflow."""
        self.graph_builder = StateGraph(AgentState)
        
        # Add nodes
        self.graph_builder.add_node("anomaly_detection", self._run_anomaly_detection)
        self.graph_builder.add_node("rag_context", self._run_rag_context)
        self.graph_builder.add_node("decision_engine", self._run_decision_engine)
        self.graph_builder.add_node("post_processing", self._run_post_processing)
        
        # Define edges
        self.graph_builder.set_entry_point("anomaly_detection")
        
        # Conditional routing after anomaly detection
        self.graph_builder.add_conditional_edges(
            "anomaly_detection",
            self._route_after_anomaly,
            {
                "high_risk": "decision_engine",  # Skip RAG for obvious fraud
                "normal": "rag_context",
                "suspicious": "rag_context"
            }
        )
        
        self.graph_builder.add_edge("rag_context", "decision_engine")
        self.graph_builder.add_edge("decision_engine", "post_processing")
        self.graph_builder.add_edge("post_processing", END)
        
        self.graph = self.graph_builder.compile()
    
    def _route_after_anomaly(self, state: AgentState) -> str:
        """Route based on anomaly severity."""
        anomaly_result = state.get("anomaly_result")
        
        if not anomaly_result:
            return "normal"
        
        if anomaly_result.is_high_confidence_fraud():
            return "high_risk"
        
        return "suspicious"
    
    async def _run_anomaly_detection(self, state: AgentState) -> AgentState:
        """Execute Agent 1: Anomaly Detection."""
        event = state.get("event")
        if not event:
            raise ValueError("No event provided for anomaly detection")
        
        result = await self.anomaly_agent.analyze(event)
        
        return {
            **state,
            "anomaly_result": result,
            "anomaly_flags": result.flags if result else []
        }
    
    async def _run_rag_context(self, state: AgentState) -> AgentState:
        """Execute Agent 2: RAG Context Gathering."""
        event = state.get("event")
        anomaly_result = state.get("anomaly_result")
        
        context = await self.rag_agent.gather_context(
            event=event,
            anomaly_flags=anomaly_result.flags if anomaly_result else []
        )
        
        return {
            **state,
            "context_bundle": context,
            "compliance_matches": context.compliance_retrievals if context else [],
            "sanctions_match": context.sanctions_hit if context else False
        }
    
    async def _run_decision_engine(self, state: AgentState) -> AgentState:
        """Execute Agent 3: Decision Orchestration."""
        event = state.get("event")
        anomaly_result = state.get("anomaly_result")
        context = state.get("context_bundle")
        
        # Enforce hard rule: sanctions match always blocks
        if context and context.sanctions_hit:
            decision = RiskDecision(
                decision_type=DecisionType.BLOCK,
                confidence=1.0,
                reason="OFAC Sanctions Match - Automatic Block",
                requires_human_review=True,
                sanctions_triggered=True
            )
            
            return {
                **state,
                "risk_decision": decision,
                "decision_bypassed_rag": True
            }
        
        decision = await self.orchestrator.make_decision(
            event=event,
            anomaly_result=anomaly_result,
            context=context
        )
        
        return {
            **state,
            "risk_decision": decision
        }
    
    async def _run_post_processing(self, state: AgentState) -> AgentState:
        """Execute post-decision actions."""
        decision = state.get("risk_decision")
        event = state.get("event")
        
        if not decision:
            return state
        
        # Generate incident report if needed
        incident_report = None
        if decision.requires_human_review or decision.decision_type in [
            DecisionType.BLOCK,
            DecisionType.FLAG
        ]:
            from aerorisk.agents.agent3_orchestrator.incident_report import IncidentReportGenerator
            generator = IncidentReportGenerator()
            incident_report = await generator.generate(event, decision, state.get("context_bundle"))
        
        # Update circuit breakers
        if decision.should_update_circuit_breaker():
            from aerorisk.agents.agent3_orchestrator.redis_writer import CircuitBreakerWriter
            writer = CircuitBreakerWriter()
            await writer.update_breaker(event.account_id, decision)
        
        return {
            **state,
            "incident_report": incident_report,
            "circuit_breaker_updated": decision.should_update_circuit_breaker(),
            "processing_complete": True
        }
    
    async def process_event(self, event: TransactionEvent) -> AgentState:
        """
        Process a single transaction event through the entire pipeline.
        
        Args:
            event: The transaction event to analyze
            
        Returns:
            Final agent state containing all results and decisions
        """
        initial_state: AgentState = {
            "event": event,
            "anomaly_result": None,
            "context_bundle": None,
            "risk_decision": None,
            "incident_report": None,
            "anomaly_flags": [],
            "compliance_matches": [],
            "sanctions_match": False,
            "circuit_breaker_updated": False,
            "decision_bypassed_rag": False,
            "processing_complete": False,
            "errors": []
        }
        
        try:
            final_state = await self.graph.ainvoke(initial_state)
            return final_state
        except Exception as e:
            # Log error and return state with error information
            initial_state["errors"].append(str(e))
            initial_state["processing_complete"] = True
            
            # Fail-open: allow transaction if pipeline fails
            from aerorisk.models.risk_decision import RiskDecision, DecisionType
            initial_state["risk_decision"] = RiskDecision(
                decision_type=DecisionType.ALLOW,
                confidence=0.0,
                reason=f"Pipeline error - fail-open: {str(e)}",
                requires_human_review=True,
                pipeline_error=True
            )
            
            return initial_state
    
    async def process_batch(self, events: List[TransactionEvent]) -> List[AgentState]:
        """
        Process multiple events concurrently.
        
        Args:
            events: List of transaction events
            
        Returns:
            List of final states for each event
        """
        import asyncio
        
        tasks = [self.process_event(event) for event in events]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Create error state
                error_state: AgentState = {
                    "event": events[i],
                    "anomaly_result": None,
                    "context_bundle": None,
                    "risk_decision": RiskDecision(
                        decision_type=DecisionType.ALLOW,
                        confidence=0.0,
                        reason=f"Batch processing error: {str(result)}",
                        requires_human_review=True,
                        pipeline_error=True
                    ),
                    "incident_report": None,
                    "anomaly_flags": [],
                    "compliance_matches": [],
                    "sanctions_match": False,
                    "circuit_breaker_updated": False,
                    "decision_bypassed_rag": False,
                    "processing_complete": True,
                    "errors": [str(result)]
                }
                processed_results.append(error_state)
            else:
                processed_results.append(result)
        
        return processed_results


# Convenience function for creating pipeline instance
def create_pipeline() -> RiskPipeline:
    """Factory function to create a new pipeline instance."""
    return RiskPipeline()

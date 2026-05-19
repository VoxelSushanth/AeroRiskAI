"""Agent 3 - LLM Decision Orchestrator."""

from typing import Optional, Any
import json
from datetime import datetime
from aerorisk.models.event import TransactionEvent
from aerorisk.models.context_bundle import ContextBundle
from aerorisk.models.risk_decision import RiskDecision, DecisionAction, RiskLevel
from aerorisk.models.incident_report import IncidentReport
from aerorisk.agents.agent3_orchestrator.llm_client import LLMClient
from aerorisk.agents.agent3_orchestrator.prompts import DECISION_PROMPT_TEMPLATE
from aerorisk.agents.agent3_orchestrator.risk_scorer import RiskScorer
from aerorisk.agents.agent3_orchestrator.redis_writer import CircuitBreakerWriter
from aerorisk.storage.postgres_client import PostgresClient
import logging

logger = logging.getLogger(__name__)


class DecisionOrchestrator:
    """LLM-based decision orchestrator for risk assessment."""

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        postgres_client: Optional[PostgresClient] = None,
        circuit_breaker_writer: Optional[CircuitBreakerWriter] = None,
    ):
        self.llm = llm_client or LLMClient()
        self.postgres = postgres_client or PostgresClient()
        self.cb_writer = circuit_breaker_writer or CircuitBreakerWriter()
        self.risk_scorer = RiskScorer()

    async def evaluate(
        self,
        event: TransactionEvent,
        context: ContextBundle,
        anomaly_flags: list[Any],
    ) -> RiskDecision:
        """
        Evaluate transaction and produce risk decision.
        
        Args:
            event: Transaction event
            context: Retrieved context from RAG agent
            anomaly_flags: Anomaly detection results from Agent 1
            
        Returns:
            RiskDecision with action recommendation
        """
        logger.info(f"Evaluating event {event.event_id}")
        
        # Check sanctions first - automatic BLOCK if matched
        if context.sanctions_match:
            logger.warning(f"SANCTIONS MATCH - auto-blocking event {event.event_id}")
            return RiskDecision(
                event_id=event.event_id,
                user_id=event.user_id,
                action=DecisionAction.BLOCK,
                risk_level=RiskLevel.CRITICAL,
                risk_score=1.0,
                reason=f"Sanctions match: {context.sanctions_match.matched_name}",
                sanctions_triggered=True,
                timestamp=datetime.now(),
            )
        
        # Calculate base risk score
        base_score = await self.risk_scorer.calculate_score(
            event=event,
            context=context,
            anomaly_flags=anomaly_flags,
        )
        
        # Prepare LLM prompt
        prompt_data = {
            "event": event.model_dump(),
            "context": {
                "compliance_rules": [
                    {"rule_id": r.rule_id, "content": r.content[:500]}
                    for r in context.compliance_rules[:3]
                ],
                "user_profile": context.user_profile.model_dump() if context.user_profile else None,
                "news_context": context.news_context[:3],
            },
            "anomaly_flags": [
                {"type": f.anomaly_type, "confidence": f.confidence, "details": f.details}
                for f in anomaly_flags
            ],
            "base_risk_score": base_score,
        }
        
        prompt = DECISION_PROMPT_TEMPLATE.format(
            event_json=json.dumps(prompt_data["event"], indent=2),
            compliance_rules=json.dumps(prompt_data["context"]["compliance_rules"], indent=2),
            user_profile=json.dumps(prompt_data["context"]["user_profile"], indent=2),
            anomaly_flags=json.dumps(prompt_data["anomaly_flags"], indent=2),
            base_score=base_score,
        )
        
        # Get LLM decision
        try:
            llm_response = await self.llm.generate_decision(prompt)
            
            # Parse LLM response
            decision_data = json.loads(llm_response)
            
            # Create risk decision
            decision = RiskDecision(
                event_id=event.event_id,
                user_id=event.user_id,
                action=DecisionAction(decision_data.get("action", "ALLOW")),
                risk_level=RiskLevel(decision_data.get("risk_level", "MEDIUM")),
                risk_score=decision_data.get("risk_score", base_score),
                reason=decision_data.get("reason", "LLM evaluation completed"),
                recommended_limits=decision_data.get("recommended_limits"),
                llm_metadata={
                    "model": self.llm.model_name,
                    "tokens_used": decision_data.get("tokens_used", 0),
                    "confidence": decision_data.get("confidence", 0.8),
                },
                timestamp=datetime.now(),
            )
            
        except Exception as e:
            logger.error(f"LLM evaluation failed: {e}, using fallback scoring")
            # Fallback to rule-based decision
            decision = self._fallback_decision(event, base_score, anomaly_flags)
        
        # Generate incident report if needed
        if decision.action in [DecisionAction.BLOCK, DecisionAction.FLAG]:
            report = await self._generate_incident_report(event, context, anomaly_flags, decision)
            decision.incident_report_id = report.report_id
            
            # Store report
            await self.postgres.insert_incident_report(report.model_dump())
        
        # Update circuit breakers if needed
        if decision.action == DecisionAction.BLOCK:
            await self.cb_writer.increment_trigger_count(event.symbol)
        
        return decision

    def _fallback_decision(
        self,
        event: TransactionEvent,
        risk_score: float,
        anomaly_flags: list[Any],
    ) -> RiskDecision:
        """Fallback rule-based decision when LLM fails."""
        
        if risk_score >= 0.8:
            action = DecisionAction.BLOCK
            risk_level = RiskLevel.HIGH
        elif risk_score >= 0.5:
            action = DecisionAction.FLAG
            risk_level = RiskLevel.MEDIUM
        else:
            action = DecisionAction.ALLOW
            risk_level = RiskLevel.LOW
        
        return RiskDecision(
            event_id=event.event_id,
            user_id=event.user_id,
            action=action,
            risk_level=risk_level,
            risk_score=risk_score,
            reason="Fallback rule-based decision (LLM unavailable)",
            timestamp=datetime.now(),
        )

    async def _generate_incident_report(
        self,
        event: TransactionEvent,
        context: ContextBundle,
        anomaly_flags: list[Any],
        decision: RiskDecision,
    ) -> IncidentReport:
        """Generate incident report for flagged/blocked transactions."""
        
        report = IncidentReport(
            event_id=event.event_id,
            user_id=event.user_id,
            symbol=event.symbol,
            incident_type=decision.action.value,
            severity=decision.risk_level.value,
            description=decision.reason,
            anomaly_details=[
                {"type": f.anomaly_type, "confidence": f.confidence}
                for f in anomaly_flags
            ],
            sanctions_match=context.sanctions_match.model_dump() if context.sanctions_match else None,
            risk_score=decision.risk_score,
            action_taken=decision.action.value,
        )
        
        return report

    async def batch_evaluate(
        self,
        events_with_context: list[tuple[TransactionEvent, ContextBundle, list[Any]]],
    ) -> list[RiskDecision]:
        """Evaluate multiple events in batch."""
        decisions = []
        
        # Process with concurrency limit
        import asyncio
        semaphore = asyncio.Semaphore(5)
        
        async def evaluate_with_semaphore(item):
            async with semaphore:
                event, context, flags = item
                return await self.evaluate(event, context, flags)
        
        tasks = [evaluate_with_semaphore(item) for item in events_with_context]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Batch evaluation error for event {i}: {result}")
                # Create fallback decision
                event = events_with_context[i][0]
                decisions.append(self._fallback_decision(event, 0.5, []))
            else:
                decisions.append(result)
        
        return decisions

# Agent 3: LLM Decision Orchestrator - Prompts & Design

## Overview

Agent 3 is the final decision engine that synthesizes inputs from Agent 1 (Anomaly Detection) and Agent 2 (RAG Context) to produce deterministic, auditable risk decisions using Local LLM inference.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              Agent 3: Decision Orchestrator                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────┐ │
│  │   LLM        │      │    Risk      │      │ Decision │ │
│  │   Client     │─────▶│    Scorer    │─────▶│  Engine  │ │
│  └──────────────┘      └──────────────┘      └──────────┘ │
│         │                                              │    │
│         ▼                                              ▼    │
│  ┌──────────────┐                              ┌──────────┐ │
│  │   Prompts    │                              │ Incident │ │
│  │   Library    │                              │ Reporter │ │
│  └──────────────┘                              └──────────┘ │
│                                                    │        │
│                                                    ▼        │
│                                             ┌──────────────┐│
│                                             │ Redis Writer ││
│                                             │ (Circuit     ││
│                                             │  Breakers)   ││
│                                             └──────────────┘│
└─────────────────────────────────────────────────────────────┘
```

## Decision Rules

### Mandatory Blocking Rules

**RULE 1: Sanctions Match → ALWAYS BLOCK**
```python
if rag_context.sanctions_result.is_sanctioned:
    return RiskDecision(
        decision="BLOCK",
        reason="SANCTIONS_MATCH",
        confidence=1.0,
        auto_generated=True,
        requires_review=False
    )
```

**RULE 2: Circuit Breaker Open → BLOCK**
```python
if any(cb.state == "OPEN" for cb in rag_context.circuit_breakers):
    return RiskDecision(
        decision="BLOCK",
        reason="CIRCUIT_BREAKER_OPEN",
        confidence=1.0,
        auto_generated=True
    )
```

**RULE 3: High Confidence Fraud Pattern → BLOCK**
```python
if (anomaly_result.anomaly_type in ["WASH_TRADE", "SPOOFING"] 
    and anomaly_result.confidence > 0.95):
    return RiskDecision(
        decision="BLOCK",
        reason=f"HIGH_CONFIDENCE_{anomaly_result.anomaly_type}",
        confidence=anomaly_result.confidence
    )
```

### Risk Scoring Matrix

| Factor | Weight | Score Range |
|--------|--------|-------------|
| Anomaly Detection Score | 40% | 0-40 |
| Sanctions Risk | 25% | 0 or 25 |
| User Profile Risk | 15% | 0-15 |
| News/Sentiment Impact | 10% | 0-10 |
| Compliance Violations | 10% | 0-10 |

**Decision Thresholds**:
- **ALLOW**: Total score < 30
- **FLAG**: 30 ≤ Total score < 60
- **ADJUST_LIMIT**: 60 ≤ Total score < 80
- **BLOCK**: Total score ≥ 80

## Prompt Templates

### System Prompt

```python
SYSTEM_PROMPT = """You are AeroRisk AI's Decision Orchestrator, a regulatory compliance 
and fraud detection system for financial trading.

YOUR ROLE:
- Analyze trading events for potential fraud, manipulation, or compliance violations
- Make deterministic, auditable decisions based on evidence
- Output structured JSON with clear reasoning

DECISION CATEGORIES:
1. ALLOW - No significant risk detected
2. FLAG - Moderate risk, allow but mark for review
3. ADJUST_LIMIT - High risk, reduce position limits
4. BLOCK - Critical risk, prevent transaction

MANDATORY RULES:
- If sanctions_match=true → ALWAYS BLOCK
- If circuit_breaker=open → ALWAYS BLOCK
- If wash_trade_confidence>0.95 → ALWAYS BLOCK
- If spoofing_confidence>0.95 → ALWAYS BLOCK

OUTPUT FORMAT:
You MUST output valid JSON matching this schema:
{
    "decision": "ALLOW|FLAG|ADJUST_LIMIT|BLOCK",
    "confidence": 0.0-1.0,
    "risk_score": 0-100,
    "primary_reason": "string",
    "secondary_reasons": ["string"],
    "evidence_summary": "string",
    "recommended_action": "string",
    "requires_human_review": boolean,
    "regulatory_references": ["string"],
    "incident_severity": "LOW|MEDIUM|HIGH|CRITICAL"
}

THINKING PROCESS:
1. Check mandatory blocking rules first
2. Evaluate anomaly detection results
3. Consider user profile and history
4. Review compliance context
5. Assess news/sentiment impact
6. Calculate aggregate risk score
7. Determine final decision

Be concise, factual, and cite specific evidence."""
```

### Decision Prompt Template

```python
DECISION_PROMPT = """Analyze the following trading event and make a risk decision.

=== EVENT DETAILS ===
Event ID: {event_id}
Timestamp: {timestamp}
Account ID: {account_id}
Symbol: {symbol}
Side: {side}
Order Type: {order_type}
Quantity: {quantity}
Price: {price}
Notional Value: ${notional_value:,.2f}

=== ANOMALY DETECTION RESULTS ===
Detected Anomalies: {anomalies}
Anomaly Risk Score: {anomaly_score}/100
Velocity Check: {velocity_status}
VWAP Deviation: {vwap_deviation}%
Wash Trade Confidence: {wash_trade_confidence}
Spoofing Probability: {spoofing_probability}
Similar Historical Patterns: {similar_patterns}

=== USER PROFILE ===
Customer Type: {customer_type}
Risk Tolerance: {risk_tolerance}
Trading Experience: {experience_years} years
Typical Order Size: ${typical_order_size:,.2f}
Typical Daily Volume: ${typical_daily_volume:,.2f}
Historical Violations: {violation_count}
KYC Status: {kyc_status}

=== COMPLIANCE CONTEXT ===
Relevant Regulations:
{compliance_rules}

Similar Historical Cases:
{historical_cases}

=== SANCTIONS SCREENING ===
Sanctions Match: {sanctions_match}
Matched Lists: {sanctions_lists}
Confidence: {sanctions_confidence}

=== MARKET CONTEXT ===
Recent News Sentiment: {news_sentiment}
Sentiment Score: {sentiment_score}
Market Impact Score: {impact_score}
Circuit Breaker Status: {circuit_breaker_status}

=== INSTRUCTIONS ===
Based on all available evidence:
1. Calculate aggregate risk score (0-100)
2. Determine decision category
3. Provide clear reasoning
4. Cite specific regulations if applicable
5. Indicate if human review is required

Output your decision as valid JSON."""
```

### Incident Report Prompt

```python
INCIDENT_REPORT_PROMPT = """Generate a formal incident report for regulatory compliance.

=== INCIDENT DETAILS ===
Decision: {decision}
Risk Score: {risk_score}
Account ID: {account_id}
Event ID: {event_id}
Timestamp: {timestamp}

=== SUMMARY ===
Primary Reason: {primary_reason}
Evidence Summary: {evidence_summary}

=== REGULATORY CONTEXT ===
Applicable Regulations: {regulations}
Potential Violations: {violations}

=== RECOMMENDED ACTIONS ===
Immediate Actions: {immediate_actions}
Follow-up Required: {followup}
Escalation Path: {escalation}

Generate a formal incident report suitable for regulatory submission.
Include all relevant details, timestamps, and audit trail information.
Format as structured JSON."""
```

## LLM Client Implementation

```python
class LLMClient:
    def __init__(self):
        # Use local LLM for low latency and data privacy
        self.model_name = "mistralai/Mixtral-8x7B-Instruct-v0.1"
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            device_map="auto",
            torch_dtype=torch.float16,
            max_memory={0: "20GB"}
        )
    
    async def generate_decision(
        self,
        event: TradingEvent,
        anomaly_results: List[AnomalyResult],
        rag_context: RAGContext
    ) -> RiskDecision:
        # Build prompt
        prompt = DECISION_PROMPT.format(
            event_id=event.id,
            timestamp=event.timestamp,
            account_id=event.account_id,
            symbol=event.symbol,
            side=event.side,
            order_type=event.order_type,
            quantity=event.quantity,
            price=event.price,
            notional_value=self._calculate_notional(event),
            anomalies=", ".join(anomaly.anomaly_type for anomaly in anomaly_results),
            anomaly_score=max(a.risk_score for a in anomaly_results) if anomaly_results else 0,
            velocity_status=self._get_velocity_status(anomaly_results),
            vwap_deviation=self._get_vwap_deviation(anomaly_results),
            wash_trade_confidence=self._get_wash_trade_confidence(anomaly_results),
            spoofing_probability=self._get_spoofing_probability(anomaly_results),
            similar_patterns=self._format_similar_patterns(anomaly_results),
            customer_type=rag_context.user_profile.customer_type,
            risk_tolerance=rag_context.user_profile.risk_tolerance,
            experience_years=rag_context.user_profile.trading_experience_years,
            typical_order_size=float(rag_context.user_profile.typical_order_size),
            typical_daily_volume=float(rag_context.user_profile.typical_daily_volume),
            violation_count=len(rag_context.user_profile.historical_violations),
            kyc_status=rag_context.user_profile.kyc_status,
            compliance_rules=self._format_compliance_rules(rag_context.relevant_rules),
            historical_cases=self._format_historical_cases(rag_context.similar_cases),
            sanctions_match=rag_context.sanctions_result.is_sanctioned,
            sanctions_lists=", ".join(rag_context.sanctions_result.matched_lists),
            sanctions_confidence=rag_context.sanctions_result.confidence,
            news_sentiment=rag_context.market_sentiment,
            sentiment_score=rag_context.sentiment_score,
            impact_score=rag_context.recent_news[0].impact_score if rag_context.recent_news else 0,
            circuit_breaker_status=self._format_circuit_breakers(rag_context.circuit_breakers)
        )
        
        # Generate response
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        
        input_ids = self.tokenizer.apply_chat_template(
            messages,
            return_tensors="pt"
        ).to(self.model.device)
        
        outputs = self.model.generate(
            input_ids,
            max_new_tokens=512,
            temperature=0.1,  # Low temperature for determinism
            top_p=0.9,
            do_sample=True,
            pad_token_id=self.tokenizer.eos_token_id
        )
        
        response = self.tokenizer.decode(outputs[0][input_ids.shape[1]:], skip_special_tokens=True)
        
        # Parse JSON response
        decision_data = self._parse_json_response(response)
        
        return RiskDecision(**decision_data)
    
    def _parse_json_response(self, response: str) -> Dict:
        # Extract JSON from response
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        # Fallback parsing
        return self._extract_fields_manually(response)
```

## Risk Scorer Implementation

```python
class RiskScorer:
    def calculate_aggregate_score(
        self,
        anomaly_results: List[AnomalyResult],
        rag_context: RAGContext
    ) -> RiskScoreBreakdown:
        breakdown = RiskScoreBreakdown()
        
        # Anomaly Detection (40%)
        if anomaly_results:
            max_anomaly_score = max(a.risk_score for a in anomaly_results)
            breakdown.anomaly_component = min(max_anomaly_score * 0.4, 40)
        
        # Sanctions (25% - binary)
        if rag_context.sanctions_result.is_sanctioned:
            breakdown.sanctions_component = 25
        
        # User Profile (15%)
        profile_risk = self._calculate_profile_risk(rag_context.user_profile)
        breakdown.profile_component = profile_risk * 0.15
        
        # News/Sentiment (10%)
        if rag_context.recent_news:
            news_impact = max(n.impact_score for n in rag_context.recent_news)
            breakdown.news_component = news_impact * 10
        
        # Compliance (10%)
        if rag_context.relevant_rules:
            breakdown.compliance_component = len(rag_context.relevant_rules) * 2
        
        breakdown.total = sum([
            breakdown.anomaly_component,
            breakdown.sanctions_component,
            breakdown.profile_component,
            breakdown.news_component,
            breakdown.compliance_component
        ])
        
        return breakdown
    
    def _calculate_profile_risk(self, profile: UserProfile) -> float:
        risk_factors = []
        
        # New account
        if profile.trading_experience_years < 1:
            risk_factors.append(0.3)
        
        # High-risk customer type
        if profile.customer_type == "RETAIL":
            risk_factors.append(0.2)
        
        # Previous violations
        if profile.historical_violations:
            risk_factors.append(min(len(profile.historical_violations) * 0.2, 0.5))
        
        # KYC issues
        if profile.kyc_status != "VERIFIED":
            risk_factors.append(0.4)
        
        return sum(risk_factors) / len(risk_factors) if risk_factors else 0
```

## Incident Reporter

```python
class IncidentReporter:
    def __init__(self, postgres_client: PostgresClient):
        self.db = postgres_client
    
    async def create_incident_report(
        self,
        decision: RiskDecision,
        event: TradingEvent,
        context: RAGContext
    ) -> IncidentReport:
        report = IncidentReport(
            id=generate_uuid(),
            created_at=datetime.utcnow(),
            severity=decision.incident_severity,
            status="OPEN" if decision.requires_human_review else "AUTO_RESOLVED",
            account_id=event.account_id,
            event_id=event.id,
            decision=decision.decision,
            risk_score=decision.risk_score,
            primary_reason=decision.primary_reason,
            evidence=decision.evidence_summary,
            regulatory_references=decision.regulatory_references,
            assigned_to=None,
            resolution=None,
            resolved_at=None
        )
        
        # Store in PostgreSQL
        await self.db.execute(
            """INSERT INTO incident_reports 
               (id, created_at, severity, status, account_id, event_id, 
                decision, risk_score, primary_reason, evidence)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)""",
            report.id, report.created_at, report.severity, report.status,
            report.account_id, report.event_id, report.decision,
            report.risk_score, report.primary_reason, report.evidence
        )
        
        return report
```

## Redis Writer for Circuit Breakers

```python
class RedisCircuitBreakerWriter:
    def __init__(self, redis_client: redis.AsyncRedis):
        self.redis = redis_client
    
    async def update_circuit_breakers(self, decision: RiskDecision, symbol: str):
        if decision.decision == "BLOCK":
            # Open circuit breaker
            await self.redis.setex(
                f"circuit_breaker:{symbol}",
                300,  # 5 minutes
                json.dumps({
                    "state": "OPEN",
                    "reason": decision.primary_reason,
                    "opened_at": time.time(),
                    "auto_close_at": time.time() + 300
                })
            )
            
            # Publish event
            await self.redis.publish(
                "circuit_breaker_events",
                json.dumps({
                    "symbol": symbol,
                    "action": "OPENED",
                    "reason": decision.primary_reason
                })
            )
        
        elif decision.decision == "ADJUST_LIMIT":
            # Update position limits
            current_limit = await self.redis.get(f"position_limit:{symbol}")
            new_limit = int(current_limit) * 0.5 if current_limit else 1000
            
            await self.redis.setex(
                f"position_limit:{symbol}",
                3600,  # 1 hour
                str(new_limit)
            )
```

## Performance Requirements

| Metric | Target | Measurement |
|--------|--------|-------------|
| LLM Inference Latency | <100ms p99 | Per decision |
| Risk Scoring Latency | <10ms | Calculation |
| Incident Report Write | <50ms | Database write |
| Circuit Breaker Update | <5ms | Redis write |
| End-to-End Pipeline | <200ms | Agent 3 total |

## Testing Strategy

1. **Unit Tests**: Test each component independently
2. **Prompt Tests**: Validate prompt templates with edge cases
3. **Integration Tests**: Test full decision pipeline
4. **Accuracy Tests**: Compare against labeled decisions
5. **Load Tests**: Verify performance under load
6. **Adversarial Tests**: Test with crafted edge cases

## Audit Trail

Every decision must be logged with:
- Full input context
- LLM prompt and response
- Risk score breakdown
- Timestamp (nanosecond precision)
- Model version
- Configuration snapshot

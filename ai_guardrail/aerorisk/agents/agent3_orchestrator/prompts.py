"""Prompt templates for LLM decision engine."""

DECISION_PROMPT_TEMPLATE = """
You are a financial risk assessment AI evaluating a transaction for potential fraud, market manipulation, or compliance violations.

## Transaction Event
{event_json}

## Compliance Rules (Top 3 Relevant)
{compliance_rules}

## User Profile
{user_profile}

## Anomaly Detection Flags
{anomaly_flags}

## Base Risk Score (from quantitative analysis)
{base_score}

## Instructions
Analyze this transaction considering:
1. Sanctions status (if any match exists, MUST BLOCK)
2. Anomaly detection results and confidence levels
3. User's historical behavior and risk tier
4. Applicable compliance rules
5. Current market context from news

## Output Format
Respond with ONLY valid JSON in this exact format:
{{
    "action": "ALLOW|FLAG|BLOCK|ADJUST_LIMIT",
    "risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
    "risk_score": 0.0-1.0,
    "reason": "Clear explanation of the decision",
    "recommended_limits": {{
        "max_order_size": null,
        "max_daily_volume": null,
        "cooling_period_minutes": null
    }}
}}

## Decision Guidelines
- ALLOW: No significant risk indicators, score < 0.3
- FLAG: Moderate concerns requiring review, score 0.3-0.6
- BLOCK: High risk or sanctions match, score > 0.6
- ADJUST_LIMIT: Allow but impose restrictions for elevated risk users

Be conservative when uncertain. Prioritize regulatory compliance over user experience.
"""


RISK_SCORING_PROMPT = """
Calculate a comprehensive risk score for this transaction.

Factors to consider:
1. Order characteristics (size relative to normal, price deviation)
2. User behavior patterns (velocity, historical flags)
3. Market context (volatility, news sentiment)
4. Compliance factors (jurisdiction, account type)

Current metrics:
- Base anomaly score: {anomaly_score}
- User risk tier: {user_risk_tier}
- Order size percentile: {order_percentile}
- Velocity ratio: {velocity_ratio}
- VWAP deviation: {vwap_deviation}

Output ONLY a number between 0.0 and 1.0 representing the overall risk score.
"""


INCIDENT_SUMMARY_PROMPT = """
Generate a concise incident summary for compliance reporting.

Event Details:
- Event ID: {event_id}
- User ID: {user_id}
- Symbol: {symbol}
- Action Taken: {action}
- Risk Score: {risk_score}

Anomaly Flags:
{anomaly_flags}

Write a 2-3 sentence summary suitable for regulatory reporting. Include:
1. What triggered the flag/block
2. Key risk indicators observed
3. Recommended follow-up actions

Summary:
"""


FEW_SHOT_EXAMPLES = """
Example 1 - Normal Trade:
Input: User with standard risk tier, order within normal limits, no anomalies
Output: {{"action": "ALLOW", "risk_level": "LOW", "risk_score": 0.15, "reason": "Normal trading activity within established patterns"}}

Example 2 - Velocity Violation:
Input: User exceeded max orders/minute, multiple rapid cancellations
Output: {{"action": "FLAG", "risk_level": "MEDIUM", "risk_score": 0.55, "reason": "Excessive order velocity suggests potential spoofing behavior", "recommended_limits": {{"max_orders_per_minute": 30}}}}

Example 3 - Sanctions Match:
Input: User matched on OFAC SDN list with 0.95 confidence
Output: {{"action": "BLOCK", "risk_level": "CRITICAL", "risk_score": 1.0, "reason": "Positive sanctions match - regulatory requirement to block"}}

Example 4 - Large Unusual Order:
Input: Institutional user, order 10x normal size, during low liquidity
Output: {{"action": "ADJUST_LIMIT", "risk_level": "MEDIUM", "risk_score": 0.45, "reason": "Unusually large order may impact market", "recommended_limits": {{"max_order_size": 5000}}}}
"""

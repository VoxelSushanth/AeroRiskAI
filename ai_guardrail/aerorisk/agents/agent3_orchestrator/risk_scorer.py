"""Risk scoring engine combining multiple signals."""

from typing import Any
from aerorisk.models.event import TransactionEvent
from aerorisk.models.context_bundle import ContextBundle
import logging

logger = logging.getLogger(__name__)


class RiskScorer:
    """Calculate composite risk scores from multiple signals."""

    # Weights for different risk factors
    WEIGHTS = {
        "anomaly_score": 0.30,
        "user_risk_tier": 0.20,
        "velocity_factor": 0.15,
        "size_factor": 0.15,
        "sanctions_factor": 0.20,
    }

    # Risk tier scores
    RISK_TIER_SCORES = {
        "low": 0.1,
        "standard": 0.3,
        "elevated": 0.6,
        "high": 0.9,
    }

    async def calculate_score(
        self,
        event: TransactionEvent,
        context: ContextBundle,
        anomaly_flags: list[Any],
    ) -> float:
        """
        Calculate composite risk score (0.0 - 1.0).
        
        Args:
            event: Transaction event
            context: Retrieved context
            anomaly_flags: Anomaly detection results
            
        Returns:
            Composite risk score
        """
        scores = {}
        
        # 1. Anomaly score (from Agent 1)
        scores["anomaly_score"] = self._calculate_anomaly_score(anomaly_flags)
        
        # 2. User risk tier score
        scores["user_risk_tier"] = self._get_user_risk_score(context)
        
        # 3. Velocity factor
        scores["velocity_factor"] = self._calculate_velocity_factor(event, context)
        
        # 4. Order size factor
        scores["size_factor"] = self._calculate_size_factor(event, context)
        
        # 5. Sanctions factor (binary - 1.0 if match, 0.0 otherwise)
        scores["sanctions_factor"] = 1.0 if context.sanctions_match else 0.0
        
        # Calculate weighted average
        total_score = sum(
            scores[factor] * weight 
            for factor, weight in self.WEIGHTS.items()
        )
        
        logger.debug(f"Risk scores: {scores}, total: {total_score}")
        
        return min(max(total_score, 0.0), 1.0)

    def _calculate_anomaly_score(self, anomaly_flags: list[Any]) -> float:
        """Calculate score from anomaly flags."""
        if not anomaly_flags:
            return 0.0
        
        # Weight by confidence and severity
        severity_weights = {
            "velocity_check": 0.3,
            "vwap_deviation": 0.2,
            "wash_trade": 0.8,
            "spoofing": 0.7,
            "embedding_similarity": 0.4,
        }
        
        weighted_sum = 0.0
        total_weight = 0.0
        
        for flag in anomaly_flags:
            severity = severity_weights.get(flag.anomaly_type, 0.5)
            confidence = getattr(flag, 'confidence', 0.5)
            weighted_sum += severity * confidence
            total_weight += severity
        
        if total_weight == 0:
            return 0.0
        
        return weighted_sum / total_weight

    def _get_user_risk_score(self, context: ContextBundle) -> float:
        """Get risk score based on user profile."""
        if not context.user_profile:
            return self.RISK_TIER_SCORES["standard"]
        
        tier = context.user_profile.risk_tier.lower()
        return self.RISK_TIER_SCORES.get(tier, 0.3)

    def _calculate_velocity_factor(
        self,
        event: TransactionEvent,
        context: ContextBundle,
    ) -> float:
        """Calculate velocity-based risk factor."""
        if not context.user_profile:
            return 0.3  # Default medium risk
        
        limits = context.user_profile.trading_limits
        max_orders = limits.get("max_orders_per_minute", 60)
        
        # Estimate current velocity (would need actual data in production)
        # This is a placeholder - real implementation would query Redis
        estimated_velocity = 10  # Placeholder
        
        velocity_ratio = estimated_velocity / max_orders
        
        # Map ratio to score: >1.0 = high risk, <0.5 = low risk
        if velocity_ratio > 1.0:
            return 0.9
        elif velocity_ratio > 0.8:
            return 0.7
        elif velocity_ratio > 0.5:
            return 0.4
        else:
            return 0.2

    def _calculate_size_factor(
        self,
        event: TransactionEvent,
        context: ContextBundle,
    ) -> float:
        """Calculate order size-based risk factor."""
        if not context.user_profile:
            return 0.3
        
        limits = context.user_profile.trading_limits
        single_order_limit = limits.get("single_order_limit", 100000)
        
        order_value = event.price * event.quantity / 10000  # Adjust for fixed point
        
        size_ratio = order_value / single_order_limit
        
        # Map ratio to score
        if size_ratio > 1.0:
            return 0.8  # Exceeds limit
        elif size_ratio > 0.8:
            return 0.6
        elif size_ratio > 0.5:
            return 0.4
        else:
            return 0.2

    def get_risk_level(self, score: float) -> str:
        """Convert numeric score to risk level."""
        if score >= 0.8:
            return "CRITICAL"
        elif score >= 0.6:
            return "HIGH"
        elif score >= 0.3:
            return "MEDIUM"
        else:
            return "LOW"

    def get_recommendation(self, score: float) -> str:
        """Get action recommendation based on score."""
        if score >= 0.8:
            return "BLOCK"
        elif score >= 0.5:
            return "FLAG"
        elif score >= 0.3:
            return "ADJUST_LIMIT"
        else:
            return "ALLOW"

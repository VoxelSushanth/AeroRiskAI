"""
Spoofing Detector: Identifies order book manipulation patterns using HMM-like analysis.
"""

import asyncio
from dataclasses import dataclass, field
from typing import Deque, Dict
from collections import deque, defaultdict

from aerorisk.models.event import OrderEvent, OrderSide, OrderAction
from aerorisk.models.anomaly_result import AnomalyResult, AnomalyType


@dataclass
class OrderBookLevel:
    """Snapshot of order book level."""

    price: int
    bid_quantity: int
    ask_quantity: int
    timestamp: float


@dataclass
class OrderLifecycle:
    """Track order lifecycle for spoofing detection."""

    order_id: str
    side: OrderSide
    price: int
    quantity: int
    submit_time: float
    cancel_time: float | None = None
    fill_time: float | None = None
    filled_quantity: int = 0


@dataclass
class SpoofingDetector:
    """Detect spoofing patterns (large orders cancelled before execution)."""

    order_book_depth: int = 10
    cancellation_threshold: float = 0.8  # 80% cancellation rate
    _order_lifecycles: Dict[str, OrderLifecycle] = field(
        default_factory=dict, init=False, repr=False
    )
    _account_orders: Dict[str, Deque[str]] = field(
        default_factory=lambda: defaultdict(deque), init=False, repr=False
    )
    _book_snapshots: Dict[str, Deque[OrderBookLevel]] = field(
        default_factory=lambda: defaultdict(deque), init=False, repr=False
    )

    async def check(self, event: OrderEvent) -> AnomalyResult:
        """Check for spoofing patterns."""
        account_id = event.account_id
        order_id = event.order_id

        if event.action == OrderAction.SUBMIT:
            # Track new order
            self._order_lifecycles[order_id] = OrderLifecycle(
                order_id=order_id,
                side=event.side,
                price=event.price,
                quantity=event.quantity,
                submit_time=event.timestamp,
            )

            # Add to account tracking
            self._account_orders[account_id].append(order_id)

            return AnomalyResult(
                anomaly_type=AnomalyType.SPOOFING,
                is_anomalous=False,
                severity_score=0.0,
                confidence=0.0,
                details={"reason": "order_submission", "order_id": order_id},
                recommendation="ALLOW",
            )

        elif event.action == OrderAction.CANCEL:
            # Mark order as cancelled
            if order_id in self._order_lifecycles:
                lifecycle = self._order_lifecycles[order_id]
                lifecycle.cancel_time = event.timestamp

                # Calculate order lifetime
                lifetime = event.timestamp - lifecycle.submit_time
                fill_ratio = lifecycle.filled_quantity / max(lifecycle.quantity, 1)

                # Check for spoofing indicators
                is_suspicious = (
                    lifetime < 1.0 and fill_ratio == 0  # Cancelled within 1s, no fills
                )

                if is_suspicious:
                    # Analyze account's overall cancellation pattern
                    cancellation_rate = await self._calculate_cancellation_rate(account_id)

                    is_anomalous = cancellation_rate > self.cancellation_threshold
                    severity = min(1.0, cancellation_rate) if is_anomalous else 0.0

                    return AnomalyResult(
                        anomaly_type=AnomalyType.SPOOFING,
                        is_anomalous=is_anomalous,
                        severity_score=severity,
                        confidence=0.80,
                        details={
                            "account_id": account_id,
                            "order_id": order_id,
                            "order_lifetime_seconds": round(lifetime, 3),
                            "fill_ratio": round(fill_ratio, 2),
                            "account_cancellation_rate": round(cancellation_rate, 2),
                            "threshold": self.cancellation_threshold,
                        },
                        recommendation="BLOCK" if severity > 0.7 else "FLAG",
                    )

            return AnomalyResult(
                anomaly_type=AnomalyType.SPOOFING,
                is_anomalous=False,
                severity_score=0.0,
                confidence=0.0,
                details={"reason": "normal_cancellation"},
                recommendation="ALLOW",
            )

        elif event.action == OrderAction.FILL:
            # Mark order as filled
            if order_id in self._order_lifecycles:
                self._order_lifecycles[order_id].fill_time = event.timestamp
                self._order_lifecycles[order_id].filled_quantity = event.quantity

        return AnomalyResult(
            anomaly_type=AnomalyType.SPOOFING,
            is_anomalous=False,
            severity_score=0.0,
            confidence=0.0,
            details={"reason": "no_spoofing_indicators"},
            recommendation="ALLOW",
        )

    async def _calculate_cancellation_rate(self, account_id: str) -> float:
        """Calculate cancellation rate for an account."""
        order_ids = list(self._account_orders.get(account_id, []))
        if not order_ids:
            return 0.0

        cancelled = 0
        total = len(order_ids)

        for oid in order_ids:
            if oid in self._order_lifecycles:
                if self._order_lifecycles[oid].cancel_time is not None:
                    cancelled += 1

        return cancelled / max(total, 1)

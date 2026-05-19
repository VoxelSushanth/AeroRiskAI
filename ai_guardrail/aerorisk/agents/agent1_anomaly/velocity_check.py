"""
Velocity Check: Detects excessive order submission rates.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Deque
from collections import deque

from aerorisk.models.event import OrderEvent
from aerorisk.models.anomaly_result import AnomalyResult, AnomalyType


@dataclass
class VelocityChecker:
    """Monitor order submission velocity per account."""

    window_size: int = 60  # seconds
    max_orders_per_second: int = 100
    _account_windows: dict[str, Deque[datetime]] = field(
        default_factory=dict, init=False, repr=False
    )

    async def check(self, event: OrderEvent) -> AnomalyResult:
        """Check if account exceeds velocity limits."""
        account_id = event.account_id
        now = datetime.utcnow()

        if account_id not in self._account_windows:
            self._account_windows[account_id] = deque()

        window = self._account_windows[account_id]
        cutoff = now - timedelta(seconds=self.window_size)

        # Remove old entries
        while window and window[0] < cutoff:
            window.popleft()

        # Add current event
        window.append(now)

        # Calculate rate
        order_count = len(window)
        time_span = (now - window[0]).total_seconds() if len(window) > 1 else 1.0
        rate = order_count / max(time_span, 1.0)

        is_anomalous = rate > self.max_orders_per_second
        severity = min(1.0, (rate / self.max_orders_per_second) - 1.0) if is_anomalous else 0.0

        return AnomalyResult(
            anomaly_type=AnomalyType.VELOCITY_VIOLATION,
            is_anomalous=is_anomalous,
            severity_score=severity,
            confidence=0.95,
            details={
                "account_id": account_id,
                "order_rate": round(rate, 2),
                "max_allowed": self.max_orders_per_second,
                "window_size_seconds": self.window_size,
                "order_count": order_count,
            },
            recommendation="BLOCK" if severity > 0.5 else "FLAG",
        )

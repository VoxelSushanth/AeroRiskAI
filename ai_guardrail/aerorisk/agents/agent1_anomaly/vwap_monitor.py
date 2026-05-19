"""
VWAP Monitor: Detects price deviations from Volume Weighted Average Price.
"""

import asyncio
from dataclasses import dataclass, field
from typing import Deque
from collections import deque

from aerorisk.models.event import OrderEvent
from aerorisk.models.anomaly_result import AnomalyResult, AnomalyType


@dataclass
class VWAPEntry:
    """Single VWAP observation."""

    price: int  # Fixed-point price
    quantity: int
    timestamp: float


@dataclass
class VWAPMonitor:
    """Monitor VWAP deviations for anomaly detection."""

    lookback_periods: int = 300
    deviation_threshold: float = 0.05  # 5% deviation
    _vwap_windows: dict[str, Deque[VWAPEntry]] = field(
        default_factory=dict, init=False, repr=False
    )

    def _calculate_vwap(self, entries: Deque[VWAPEntry]) -> int:
        """Calculate VWAP from window of entries."""
        if not entries:
            return 0

        total_value = sum(e.price * e.quantity for e in entries)
        total_volume = sum(e.quantity for e in entries)

        if total_volume == 0:
            return 0

        return total_value // total_volume

    async def check(self, event: OrderEvent) -> AnomalyResult:
        """Check for VWAP deviation anomalies."""
        account_id = event.account_id
        symbol = event.symbol
        key = f"{account_id}:{symbol}"

        if key not in self._vwap_windows:
            self._vwap_windows[key] = deque(maxlen=self.lookback_periods)

        window = self._vwap_windows[key]

        # Calculate current VWAP before adding new event
        current_vwap = self._calculate_vwap(window)

        # Add new event
        window.append(
            VWAPEntry(
                price=event.price,
                quantity=event.quantity,
                timestamp=event.timestamp,
            )
        )

        # Skip if not enough history
        if len(window) < 10:
            return AnomalyResult(
                anomaly_type=AnomalyType.VWAP_DEVIATION,
                is_anomalous=False,
                severity_score=0.0,
                confidence=0.0,
                details={"reason": "insufficient_history", "window_size": len(window)},
                recommendation="ALLOW",
            )

        # Calculate deviation
        if current_vwap == 0:
            return AnomalyResult(
                anomaly_type=AnomalyType.VWAP_DEVIATION,
                is_anomalous=False,
                severity_score=0.0,
                confidence=0.0,
                details={"reason": "zero_vwap"},
                recommendation="ALLOW",
            )

        price = event.price
        deviation = abs(price - current_vwap) / current_vwap

        is_anomalous = deviation > self.deviation_threshold
        severity = min(1.0, deviation / self.deviation_threshold) if is_anomalous else 0.0

        return AnomalyResult(
            anomaly_type=AnomalyType.VWAP_DEVIATION,
            is_anomalous=is_anomalous,
            severity_score=severity,
            confidence=0.90,
            details={
                "account_id": account_id,
                "symbol": symbol,
                "current_price": price,
                "current_vwap": current_vwap,
                "deviation_pct": round(deviation * 100, 2),
                "threshold_pct": self.deviation_threshold * 100,
            },
            recommendation="FLAG" if severity < 0.7 else "BLOCK",
        )

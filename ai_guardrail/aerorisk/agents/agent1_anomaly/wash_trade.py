"""
Wash Trade Detector: Identifies circular trading patterns.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Deque, Dict, Tuple
from collections import deque, defaultdict

from aerorisk.models.event import OrderEvent, OrderSide
from aerorisk.models.anomaly_result import AnomalyResult, AnomalyType


@dataclass
class TradeRecord:
    """Record of a trade for wash trade detection."""

    account_id: str
    symbol: str
    side: OrderSide
    price: int
    quantity: int
    timestamp: float
    counterparty_id: str | None = None


@dataclass
class WashTradeDetector:
    """Detect wash trading patterns (buy/sell to same entity)."""

    time_window_seconds: int = 300
    min_round_trips: int = 3
    _trade_history: Dict[str, Deque[TradeRecord]] = field(
        default_factory=lambda: defaultdict(deque), init=False, repr=False
    )
    _account_pairs: Dict[Tuple[str, str], list] = field(
        default_factory=dict, init=False, repr=False
    )

    async def check(self, event: OrderEvent) -> AnomalyResult:
        """Check for wash trade patterns."""
        account_id = event.account_id
        symbol = event.symbol
        key = f"{account_id}:{symbol}"

        now = datetime.utcnow().timestamp()
        cutoff = now - self.time_window_seconds

        # Get or create trade window
        window = self._trade_history[key]

        # Remove old trades
        while window and window[0].timestamp < cutoff:
            window.popleft()

        # Add current event as potential trade
        trade = TradeRecord(
            account_id=account_id,
            symbol=symbol,
            side=event.side,
            price=event.price,
            quantity=event.quantity,
            timestamp=now,
        )

        # Look for matching opposite trades
        round_trips = 0
        matching_trades = []

        for prev_trade in window:
            # Check for opposite side at similar price
            if prev_trade.side != event.side:
                price_diff = abs(prev_trade.price - event.price) / max(prev_trade.price, 1)
                if price_diff < 0.01:  # Within 1%
                    round_trips += 1
                    matching_trades.append(prev_trade)

        window.append(trade)

        is_anomalous = round_trips >= self.min_round_trips
        severity = min(1.0, round_trips / (self.min_round_trips * 2)) if is_anomalous else 0.0

        return AnomalyResult(
            anomaly_type=AnomalyType.WASH_TRADE,
            is_anomalous=is_anomalous,
            severity_score=severity,
            confidence=0.85,
            details={
                "account_id": account_id,
                "symbol": symbol,
                "round_trips_detected": round_trips,
                "min_required": self.min_round_trips,
                "time_window_seconds": self.time_window_seconds,
                "matching_trades": len(matching_trades),
            },
            recommendation="BLOCK" if severity > 0.6 else "FLAG",
        )

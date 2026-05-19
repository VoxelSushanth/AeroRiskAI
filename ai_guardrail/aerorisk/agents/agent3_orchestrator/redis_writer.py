"""Circuit breaker writer for Redis."""

from typing import Optional
import asyncio
from datetime import datetime, timedelta
from aerorisk.storage.redis_client import RedisClient
from aerorisk.config.settings import settings
import logging

logger = logging.getLogger(__name__)


class CircuitBreakerWriter:
    """Write circuit breaker state to Redis."""

    def __init__(
        self,
        redis_client: Optional[RedisClient] = None,
    ):
        self.redis = redis_client or RedisClient()
        self._prefix = "circuit_breaker:"
        self._trigger_threshold = 5  # Triggers before opening
        self._open_duration = timedelta(minutes=5)

    async def increment_trigger_count(self, symbol: str) -> int:
        """
        Increment trigger count for a symbol.
        
        Returns:
            New trigger count
        """
        key = f"{self._prefix}{symbol}:triggers"
        
        try:
            # Increment and get new value
            new_count = await self.redis.incr(key)
            
            # Set expiry if this is first trigger
            if new_count == 1:
                await self.redis.expire(key, int(self._open_duration.total_seconds()))
            
            logger.info(f"Circuit breaker trigger for {symbol}: count={new_count}")
            
            # Check if should open circuit
            if new_count >= self._trigger_threshold:
                await self._open_circuit(symbol)
            
            return new_count
            
        except Exception as e:
            logger.error(f"Error incrementing trigger count: {e}")
            return -1

    async def _open_circuit(self, symbol: str) -> None:
        """Open circuit breaker for symbol."""
        status_key = f"{self._prefix}{symbol}:status"
        
        try:
            await self.redis.set(status_key, "OPEN", ex=int(self._open_duration.total_seconds()))
            logger.warning(f"CIRCUIT BREAKER OPENED for {symbol}")
            
            # Publish event for monitoring
            await self._publish_circuit_event(symbol, "OPEN")
            
        except Exception as e:
            logger.error(f"Error opening circuit breaker: {e}")

    async def close_circuit(self, symbol: str) -> None:
        """Manually close circuit breaker for symbol."""
        status_key = f"{self._prefix}{symbol}:status"
        trigger_key = f"{self._prefix}{symbol}:triggers"
        
        try:
            await self.redis.set(status_key, "CLOSED")
            await self.redis.delete(trigger_key)
            
            logger.info(f"Circuit breaker CLOSED for {symbol}")
            await self._publish_circuit_event(symbol, "CLOSED")
            
        except Exception as e:
            logger.error(f"Error closing circuit breaker: {e}")

    async def get_status(self, symbol: str) -> dict:
        """Get current circuit breaker status for symbol."""
        status_key = f"{self._prefix}{symbol}:status"
        trigger_key = f"{self._prefix}{symbol}:triggers"
        
        try:
            status = await self.redis.get(status_key)
            triggers = await self.redis.get(trigger_key)
            
            return {
                "symbol": symbol,
                "status": status or "CLOSED",
                "trigger_count": int(triggers) if triggers else 0,
                "threshold": self._trigger_threshold,
            }
            
        except Exception as e:
            logger.error(f"Error getting circuit status: {e}")
            return {
                "symbol": symbol,
                "status": "ERROR",
                "trigger_count": 0,
                "threshold": self._trigger_threshold,
            }

    async def _publish_circuit_event(self, symbol: str, action: str) -> None:
        """Publish circuit breaker event to Kafka."""
        from aerorisk.internal.publisher.kafka_publisher import KafkaPublisher
        
        try:
            publisher = KafkaPublisher()
            await publisher.publish(
                topic="circuit_breaker_events",
                value={
                    "symbol": symbol,
                    "action": action,
                    "timestamp": datetime.now().isoformat(),
                },
            )
        except Exception as e:
            logger.error(f"Error publishing circuit event: {e}")

    async def reset_all(self) -> None:
        """Reset all circuit breakers (for testing/maintenance)."""
        try:
            # Find all circuit breaker keys
            pattern = f"{self._prefix}*:status"
            keys = await self.redis.keys(pattern)
            
            for key in keys:
                symbol = key.replace(f"{self._prefix}", "").replace(":status", "")
                await self.close_circuit(symbol)
            
            logger.info("All circuit breakers reset")
            
        except Exception as e:
            logger.error(f"Error resetting circuit breakers: {e}")

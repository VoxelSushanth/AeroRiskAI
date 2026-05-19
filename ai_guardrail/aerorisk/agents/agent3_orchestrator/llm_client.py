"""LLM client for decision generation."""

from typing import Optional, Any
import json
import aiohttp
from aerorisk.config.settings import settings
import logging

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for local LLM inference."""

    def __init__(
        self,
        api_url: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: int = 30,
    ):
        self.api_url = api_url or settings.llm_api_url
        self.model_name = model_name or settings.llm_model
        self.timeout = timeout
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers={"Content-Type": "application/json"},
            )
        return self._session

    async def close(self) -> None:
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def generate_decision(self, prompt: str) -> str:
        """
        Generate risk decision from LLM.
        
        Args:
            prompt: Formatted prompt with event context
            
        Returns:
            JSON string with decision data
        """
        session = await self._get_session()
        
        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a financial risk assessment AI. Output ONLY valid JSON with fields: action (ALLOW|FLAG|BLOCK|ADJUST_LIMIT), risk_level (LOW|MEDIUM|HIGH|CRITICAL), risk_score (0.0-1.0), reason (string), recommended_limits (optional object).",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,  # Low temperature for deterministic output
            "max_tokens": 500,
            "response_format": {"type": "json_object"},
        }
        
        try:
            async with session.post(
                f"{self.api_url}/v1/chat/completions",
                json=payload,
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"LLM API error: {response.status} - {error_text}")
                    raise RuntimeError(f"LLM API returned {response.status}")
                
                result = await response.json()
                
                # Extract content
                content = result["choices"][0]["message"]["content"]
                
                # Parse and validate JSON
                decision_data = json.loads(content)
                
                # Validate required fields
                if "action" not in decision_data:
                    decision_data["action"] = "FLAG"
                if "risk_score" not in decision_data:
                    decision_data["risk_score"] = 0.5
                
                # Add token usage info
                usage = result.get("usage", {})
                decision_data["tokens_used"] = usage.get("total_tokens", 0)
                
                return json.dumps(decision_data)
                
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error calling LLM: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in LLM call: {e}")
            raise

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate embedding vector for text."""
        session = await self._get_session()
        
        payload = {
            "model": settings.embedding_model,
            "input": text,
        }
        
        try:
            async with session.post(
                f"{self.api_url}/v1/embeddings",
                json=payload,
            ) as response:
                if response.status != 200:
                    raise RuntimeError(f"Embedding API returned {response.status}")
                
                result = await response.json()
                return result["data"][0]["embedding"]
                
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise

    async def health_check(self) -> bool:
        """Check if LLM service is healthy."""
        session = await self._get_session()
        
        try:
            async with session.get(f"{self.api_url}/health") as response:
                return response.status == 200
        except Exception:
            return False

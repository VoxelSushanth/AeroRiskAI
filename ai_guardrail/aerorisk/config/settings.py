"""
Configuration settings for AeroRisk AI Guardrail.
"""

import os
from pydantic import BaseModel, Field
from typing import Any


class KafkaSettings(BaseModel):
    """Kafka configuration."""

    bootstrap_servers: str = Field(default="localhost:9092")
    consumer_group: str = Field(default="aerorisk-ai-guardrail")
    order_topic: str = Field(default="orders.raw")
    decision_topic: str = Field(default="risk.decisions")
    auto_offset_reset: str = Field(default="earliest")
    enable_auto_commit: bool = Field(default=False)
    max_poll_records: int = Field(default=100)
    session_timeout_ms: int = Field(default=30000)


class RedisSettings(BaseModel):
    """Redis configuration."""

    host: str = Field(default="localhost")
    port: int = Field(default=6379)
    db: int = Field(default=0)
    password: str | None = Field(default=None)
    socket_timeout: float = Field(default=5.0)
    circuit_breaker_key_prefix: str = Field(default="circuit_breaker:")
    account_state_key_prefix: str = Field(default="account_state:")


class QdrantSettings(BaseModel):
    """Qdrant vector database configuration."""

    host: str = Field(default="localhost")
    port: int = Field(default=6333)
    https: bool = Field(default=False)
    compliance_collection: str = Field(default="compliance_rules")
    news_collection: str = Field(default="market_news")
    profiles_collection: str = Field(default="user_profiles")
    embedding_dim: int = Field(default=128)


class PostgresSettings(BaseModel):
    """PostgreSQL configuration."""

    host: str = Field(default="localhost")
    port: int = Field(default=5432)
    database: str = Field(default="aerorisk")
    user: str = Field(default="aerorisk")
    password: str = Field(default="aerorisk_password")
    pool_size: int = Field(default=10)
    incident_table: str = Field(default="incident_reports")


class LLMSettings(BaseModel):
    """LLM inference configuration."""

    provider: str = Field(default="ollama")  # ollama, openai, anthropic
    model_name: str = Field(default="llama3.1:8b")
    base_url: str = Field(default="http://localhost:11434")
    api_key: str | None = Field(default=None)
    max_tokens: int = Field(default=1024)
    temperature: float = Field(default=0.0)  # Deterministic outputs
    timeout_seconds: float = Field(default=30.0)


class AgentSettings(BaseModel):
    """Agent pipeline configuration."""

    # Agent 1 - Anomaly Detection
    velocity_window_seconds: int = Field(default=60)
    max_orders_per_second: int = Field(default=100)
    vwap_lookback_periods: int = Field(default=300)
    vwap_deviation_threshold: float = Field(default=0.05)
    wash_trade_window_seconds: int = Field(default=300)
    min_wash_trade_round_trips: int = Field(default=3)
    spoofing_cancellation_threshold: float = Field(default=0.8)

    # Agent 3 - Decision thresholds
    block_risk_threshold: float = Field(default=0.8)
    flag_risk_threshold: float = Field(default=0.5)
    require_human_review_threshold: float = Field(default=0.7)


class Settings(BaseModel):
    """Main application settings."""

    # Environment
    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")
    service_name: str = Field(default="aerorisk-ai-guardrail")

    # Sub-settings
    kafka: KafkaSettings = Field(default_factory=KafkaSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    qdrant: QdrantSettings = Field(default_factory=QdrantSettings)
    postgres: PostgresSettings = Field(default_factory=PostgresSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    agent: AgentSettings = Field(default_factory=AgentSettings)

    # Observability
    otel_exporter_endpoint: str = Field(default="http://localhost:4317")
    metrics_enabled: bool = Field(default=True)
    tracing_enabled: bool = Field(default=True)

    class Config:
        env_file = ".env"
        env_nested_delimiter = "__"


def load_settings() -> Settings:
    """Load settings from environment and defaults."""
    return Settings()

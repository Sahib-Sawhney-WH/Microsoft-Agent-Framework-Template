"""
Configuration models for the AI Assistant.

Provides type-safe configuration validation.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ObservabilityConfig(BaseModel):
    """Configuration for observability features."""

    # Tracing
    tracing_enabled: bool = Field(False, description="Enable OpenTelemetry tracing")
    tracing_exporter: str = Field("console", description="Trace exporter type")
    tracing_endpoint: str = Field("", description="OTLP endpoint for traces")
    tracing_sample_rate: float = Field(1.0, ge=0.0, le=1.0, description="Trace sample rate")

    # Metrics
    metrics_enabled: bool = Field(False, description="Enable metrics collection")
    metrics_exporter: str = Field("console", description="Metrics exporter type")
    metrics_port: int = Field(8000, ge=1, le=65535, description="Prometheus metrics port")

    # Azure Monitor
    azure_connection_string: str = Field("", description="Azure Monitor connection string")

    # Service info
    service_name: str = Field("ai-assistant", description="Service name for telemetry")
    service_version: str = Field("1.0.0", description="Service version")
    environment: str = Field("development", description="Deployment environment")

    class Config:
        json_schema_extra = {
            "example": {
                "tracing_enabled": True,
                "tracing_exporter": "azure",
                "metrics_enabled": True,
                "metrics_exporter": "prometheus",
                "service_name": "my-ai-assistant",
                "environment": "production"
            }
        }


class SecurityConfig(BaseModel):
    """Configuration for security features."""

    # Rate limiting
    rate_limit_enabled: bool = Field(True, description="Enable rate limiting")
    rate_limit_requests_per_minute: int = Field(60, ge=1, description="Max requests per minute")
    rate_limit_tokens_per_minute: int = Field(100000, ge=1, description="Max tokens per minute")

    # Input validation
    max_question_length: int = Field(32000, ge=100, description="Max question length")
    max_tool_calls_per_request: int = Field(10, ge=1, description="Max tool calls per request")

    # Content filtering
    block_prompt_injection: bool = Field(True, description="Block potential prompt injections")
    block_pii: bool = Field(False, description="Block PII in inputs")
    allowed_tool_names: Optional[List[str]] = Field(None, description="Whitelist of allowed tools")
    blocked_tool_names: List[str] = Field(default_factory=list, description="Blacklist of blocked tools")

    # Authentication (for future use)
    require_authentication: bool = Field(False, description="Require auth for requests")
    allowed_origins: List[str] = Field(default_factory=list, description="CORS allowed origins")

    class Config:
        json_schema_extra = {
            "example": {
                "rate_limit_enabled": True,
                "rate_limit_requests_per_minute": 60,
                "block_prompt_injection": True,
                "blocked_tool_names": ["dangerous_tool"]
            }
        }


class MemoryConfigModel(BaseModel):
    """Configuration for memory/session management."""

    # Cache settings
    cache_enabled: bool = Field(False, description="Enable Redis cache")
    cache_host: str = Field("", description="Redis host")
    cache_port: int = Field(6380, description="Redis port")
    cache_ssl: bool = Field(True, description="Use SSL for Redis")
    cache_ttl: int = Field(3600, ge=60, description="Cache TTL in seconds")
    cache_prefix: str = Field("chat:", description="Key prefix")

    # Persistence settings
    persistence_enabled: bool = Field(False, description="Enable ADLS persistence")
    persistence_account: str = Field("", description="Storage account name")
    persistence_container: str = Field("chat-history", description="Container name")
    persistence_folder: str = Field("threads", description="Folder path")
    persistence_schedule: str = Field("ttl+300", description="Persist schedule")

    # Summarization
    summarization_enabled: bool = Field(False, description="Enable context summarization")
    summarization_threshold_tokens: int = Field(4000, description="Token threshold for summarization")
    summarization_keep_recent: int = Field(5, description="Recent messages to keep after summarization")

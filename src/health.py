"""
Health Check Module for the AI Assistant.

Provides health check endpoints for:
- Kubernetes readiness/liveness probes
- Container orchestration
- Monitoring systems
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Awaitable
from enum import Enum

import structlog

logger = structlog.get_logger(__name__)


class HealthStatus(str, Enum):
    """Health check status values."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentCheck:
    """Result of a component health check."""
    name: str
    status: HealthStatus
    latency_ms: float
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class HealthCheckResult:
    """Overall health check result."""
    status: HealthStatus
    timestamp: datetime
    version: str
    components: List[ComponentCheck]
    uptime_seconds: float


@dataclass
class HealthCheckConfig:
    """Configuration for health checks."""
    enabled: bool = True
    timeout_seconds: float = 5.0
    cache_seconds: float = 10.0  # Cache health check results
    include_details: bool = True
    version: str = "1.0.0"


class HealthChecker:
    """
    Health checker for the AI Assistant.

    Provides comprehensive health checks for all components
    including Azure OpenAI, Redis, ADLS, and MCP servers.
    """

    def __init__(self, config: HealthCheckConfig = None):
        """
        Initialize health checker.

        Args:
            config: HealthCheckConfig with settings
        """
        self.config = config or HealthCheckConfig()
        self._start_time = time.time()
        self._checks: Dict[str, Callable[[], Awaitable[ComponentCheck]]] = {}
        self._last_result: Optional[HealthCheckResult] = None
        self._last_check_time: float = 0

        logger.info("Health checker initialized")

    def register_check(
        self,
        name: str,
        check_fn: Callable[[], Awaitable[ComponentCheck]]
    ) -> None:
        """
        Register a component health check.

        Args:
            name: Component name
            check_fn: Async function that returns ComponentCheck
        """
        self._checks[name] = check_fn
        logger.debug("Registered health check", component=name)

    async def check_all(self) -> HealthCheckResult:
        """
        Run all health checks.

        Returns:
            HealthCheckResult with overall status
        """
        # Return cached result if still valid
        if self._last_result and (time.time() - self._last_check_time) < self.config.cache_seconds:
            return self._last_result

        components: List[ComponentCheck] = []
        overall_status = HealthStatus.HEALTHY

        # Run all checks concurrently with timeout
        async def run_check(name: str, check_fn) -> ComponentCheck:
            try:
                return await asyncio.wait_for(
                    check_fn(),
                    timeout=self.config.timeout_seconds
                )
            except asyncio.TimeoutError:
                return ComponentCheck(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    latency_ms=self.config.timeout_seconds * 1000,
                    message="Health check timed out"
                )
            except Exception as e:
                return ComponentCheck(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    latency_ms=0,
                    message=f"Health check failed: {str(e)}"
                )

        # Run all checks
        if self._checks:
            tasks = [
                run_check(name, check_fn)
                for name, check_fn in self._checks.items()
            ]
            components = await asyncio.gather(*tasks)

            # Determine overall status
            for component in components:
                if component.status == HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.UNHEALTHY
                    break
                elif component.status == HealthStatus.DEGRADED:
                    if overall_status != HealthStatus.UNHEALTHY:
                        overall_status = HealthStatus.DEGRADED

        result = HealthCheckResult(
            status=overall_status,
            timestamp=datetime.now(timezone.utc),
            version=self.config.version,
            components=components,
            uptime_seconds=time.time() - self._start_time
        )

        # Cache result
        self._last_result = result
        self._last_check_time = time.time()

        return result

    async def check_readiness(self) -> bool:
        """
        Quick readiness check (for K8s readiness probe).

        Returns:
            True if service is ready to accept requests
        """
        result = await self.check_all()
        return result.status != HealthStatus.UNHEALTHY

    async def check_liveness(self) -> bool:
        """
        Quick liveness check (for K8s liveness probe).

        Returns:
            True if service is alive
        """
        # Basic check - service is running
        return True

    def to_dict(self, result: HealthCheckResult) -> Dict[str, Any]:
        """Convert health check result to dictionary."""
        return {
            "status": result.status.value,
            "timestamp": result.timestamp.isoformat(),
            "version": result.version,
            "uptime_seconds": round(result.uptime_seconds, 2),
            "components": [
                {
                    "name": c.name,
                    "status": c.status.value,
                    "latency_ms": round(c.latency_ms, 2),
                    "message": c.message,
                    **({"details": c.details} if c.details and self.config.include_details else {})
                }
                for c in result.components
            ]
        }


# Factory functions for common health checks

async def create_azure_openai_check(
    chat_client,
    deployment_name: str = None,
    test_prompt: str = "Hi"
) -> Callable[[], Awaitable[ComponentCheck]]:
    """
    Create a health check for Azure OpenAI.

    Performs a real API call to verify connectivity and model availability.

    Args:
        chat_client: The Azure OpenAI chat client instance
        deployment_name: Optional model deployment name to test
        test_prompt: Simple prompt to test (default: "Hi")

    Returns:
        Async function that performs the health check
    """

    async def check() -> ComponentCheck:
        start = time.perf_counter()
        try:
            # Attempt real API call with minimal tokens
            if hasattr(chat_client, 'complete'):
                # Using Agent Framework SDK client
                response = await chat_client.complete(
                    messages=[{"role": "user", "content": test_prompt}],
                    max_tokens=5,
                    temperature=0
                )
                latency = (time.perf_counter() - start) * 1000

                return ComponentCheck(
                    name="azure_openai",
                    status=HealthStatus.HEALTHY,
                    latency_ms=latency,
                    message="Azure OpenAI API responding",
                    details={
                        "model": deployment_name or "default",
                        "response_received": True
                    }
                )

            elif hasattr(chat_client, 'chat'):
                # Using Azure OpenAI SDK directly
                response = await chat_client.chat.completions.create(
                    model=deployment_name or chat_client.model,
                    messages=[{"role": "user", "content": test_prompt}],
                    max_tokens=5,
                    temperature=0
                )
                latency = (time.perf_counter() - start) * 1000

                return ComponentCheck(
                    name="azure_openai",
                    status=HealthStatus.HEALTHY,
                    latency_ms=latency,
                    message="Azure OpenAI API responding",
                    details={
                        "model": response.model if hasattr(response, 'model') else deployment_name,
                        "response_received": True
                    }
                )

            elif hasattr(chat_client, '_client'):
                # Wrapper with internal client
                inner_client = chat_client._client
                if hasattr(inner_client, 'chat'):
                    response = await inner_client.chat.completions.create(
                        model=deployment_name or getattr(chat_client, 'model', 'gpt-4'),
                        messages=[{"role": "user", "content": test_prompt}],
                        max_tokens=5,
                        temperature=0
                    )
                    latency = (time.perf_counter() - start) * 1000

                    return ComponentCheck(
                        name="azure_openai",
                        status=HealthStatus.HEALTHY,
                        latency_ms=latency,
                        message="Azure OpenAI API responding",
                        details={
                            "model": response.model if hasattr(response, 'model') else deployment_name,
                            "response_received": True
                        }
                    )

            # Fallback: try to verify connection exists
            latency = (time.perf_counter() - start) * 1000
            if chat_client is not None:
                return ComponentCheck(
                    name="azure_openai",
                    status=HealthStatus.DEGRADED,
                    latency_ms=latency,
                    message="Azure OpenAI client present but unable to verify API"
                )

            return ComponentCheck(
                name="azure_openai",
                status=HealthStatus.UNHEALTHY,
                latency_ms=latency,
                message="Azure OpenAI client not configured"
            )

        except Exception as e:
            latency = (time.perf_counter() - start) * 1000
            error_msg = str(e)

            # Determine if this is a temporary or permanent failure
            if "rate limit" in error_msg.lower() or "429" in error_msg:
                # Rate limited is degraded, not unhealthy
                return ComponentCheck(
                    name="azure_openai",
                    status=HealthStatus.DEGRADED,
                    latency_ms=latency,
                    message="Azure OpenAI rate limited",
                    details={"error": error_msg}
                )
            elif "timeout" in error_msg.lower():
                return ComponentCheck(
                    name="azure_openai",
                    status=HealthStatus.DEGRADED,
                    latency_ms=latency,
                    message="Azure OpenAI request timeout",
                    details={"error": error_msg}
                )

            return ComponentCheck(
                name="azure_openai",
                status=HealthStatus.UNHEALTHY,
                latency_ms=latency,
                message=f"Azure OpenAI error: {error_msg}",
                details={"error": error_msg}
            )

    return check


async def create_redis_check(cache) -> Callable[[], Awaitable[ComponentCheck]]:
    """Create a health check for Redis cache."""

    async def check() -> ComponentCheck:
        start = time.perf_counter()
        try:
            # Ping Redis
            if hasattr(cache, '_client') and cache._client:
                await cache._client.ping()
                latency = (time.perf_counter() - start) * 1000

                return ComponentCheck(
                    name="redis",
                    status=HealthStatus.HEALTHY,
                    latency_ms=latency,
                    message="Redis cache operational"
                )
            else:
                return ComponentCheck(
                    name="redis",
                    status=HealthStatus.DEGRADED,
                    latency_ms=0,
                    message="Redis not connected, using fallback"
                )
        except Exception as e:
            return ComponentCheck(
                name="redis",
                status=HealthStatus.DEGRADED,
                latency_ms=(time.perf_counter() - start) * 1000,
                message=f"Redis error: {str(e)}"
            )

    return check


async def create_adls_check(persistence) -> Callable[[], Awaitable[ComponentCheck]]:
    """Create a health check for ADLS persistence."""

    async def check() -> ComponentCheck:
        start = time.perf_counter()
        try:
            if not persistence.config.enabled:
                return ComponentCheck(
                    name="adls",
                    status=HealthStatus.HEALTHY,
                    latency_ms=0,
                    message="ADLS persistence disabled"
                )

            # Try to list container (quick check)
            if persistence._container_client:
                await persistence._container_client.get_container_properties()
                latency = (time.perf_counter() - start) * 1000

                return ComponentCheck(
                    name="adls",
                    status=HealthStatus.HEALTHY,
                    latency_ms=latency,
                    message="ADLS persistence operational"
                )
            else:
                return ComponentCheck(
                    name="adls",
                    status=HealthStatus.UNHEALTHY,
                    latency_ms=0,
                    message="ADLS not connected"
                )
        except Exception as e:
            return ComponentCheck(
                name="adls",
                status=HealthStatus.UNHEALTHY,
                latency_ms=(time.perf_counter() - start) * 1000,
                message=f"ADLS error: {str(e)}"
            )

    return check


async def create_mcp_check(mcp_manager) -> Callable[[], Awaitable[ComponentCheck]]:
    """Create a health check for MCP servers."""

    async def check() -> ComponentCheck:
        start = time.perf_counter()
        try:
            tool_count = len(mcp_manager.tools) if mcp_manager else 0
            latency = (time.perf_counter() - start) * 1000

            if tool_count > 0:
                return ComponentCheck(
                    name="mcp",
                    status=HealthStatus.HEALTHY,
                    latency_ms=latency,
                    message=f"{tool_count} MCP tools loaded",
                    details={"tool_count": tool_count}
                )
            else:
                return ComponentCheck(
                    name="mcp",
                    status=HealthStatus.HEALTHY,
                    latency_ms=latency,
                    message="No MCP servers configured"
                )
        except Exception as e:
            return ComponentCheck(
                name="mcp",
                status=HealthStatus.DEGRADED,
                latency_ms=(time.perf_counter() - start) * 1000,
                message=f"MCP error: {str(e)}"
            )

    return check

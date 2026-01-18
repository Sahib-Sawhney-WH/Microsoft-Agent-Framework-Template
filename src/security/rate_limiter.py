"""
Rate Limiting for the AI Assistant.

Provides token bucket and sliding window rate limiting
to protect against abuse and ensure fair usage.

Supports both in-memory and Redis-backed distributed rate limiting
for Kubernetes/multi-instance deployments.
"""

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from collections import defaultdict

import structlog

logger = structlog.get_logger(__name__)


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str,
        limit_type: str,
        retry_after: Optional[float] = None
    ):
        super().__init__(message)
        self.limit_type = limit_type
        self.retry_after = retry_after


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    enabled: bool = True

    # Request limits
    requests_per_minute: int = 60
    requests_per_hour: int = 1000

    # Token limits
    tokens_per_minute: int = 100000
    tokens_per_hour: int = 1000000

    # Concurrent request limits
    max_concurrent_requests: int = 10

    # Per-user vs global
    per_user: bool = True  # If False, limits are global

    # Burst allowance (percentage over limit allowed in short bursts)
    burst_multiplier: float = 1.5

    # Redis configuration for distributed rate limiting
    use_redis: bool = False
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 1  # Use separate DB from cache
    redis_prefix: str = "ratelimit:"

    # Require user identification (prevents bypass via null user_id)
    require_user_id: bool = False
    fallback_to_session: bool = True  # Use session ID if user_id is None


@dataclass
class RateLimitState:
    """State for a single rate limit window."""
    count: int = 0
    tokens: int = 0
    window_start: float = field(default_factory=time.time)
    concurrent: int = 0


class RedisRateLimitBackend:
    """
    Redis-backed rate limiting for distributed deployments.

    Uses Redis INCR with EXPIRE for atomic rate limiting across instances.
    """

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self._client = None
        self._initialized = False

    async def _ensure_connected(self) -> bool:
        """Ensure Redis connection is established."""
        if self._initialized:
            return self._client is not None

        self._initialized = True

        try:
            import redis.asyncio as redis_async

            self._client = redis_async.Redis(
                host=self.config.redis_host,
                port=self.config.redis_port,
                db=self.config.redis_db,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
            )

            await self._client.ping()
            logger.info(
                "Redis rate limit backend connected",
                host=self.config.redis_host
            )
            return True

        except ImportError:
            logger.warning("redis package not installed, falling back to in-memory")
            return False
        except Exception as e:
            logger.warning(
                "Redis connection failed, falling back to in-memory",
                error=str(e)
            )
            self._client = None
            return False

    def _make_key(self, identifier: str, window: str) -> str:
        """Create Redis key for rate limit counter."""
        return f"{self.config.redis_prefix}{identifier}:{window}"

    async def get_count(self, identifier: str, window: str) -> int:
        """Get current count for a window."""
        if not await self._ensure_connected():
            return 0

        try:
            key = self._make_key(identifier, window)
            count = await self._client.get(key)
            return int(count) if count else 0
        except Exception as e:
            logger.warning("Redis get failed", error=str(e))
            return 0

    async def increment(
        self,
        identifier: str,
        window: str,
        ttl: int,
        amount: int = 1
    ) -> int:
        """Atomically increment counter and set TTL."""
        if not await self._ensure_connected():
            return 0

        try:
            key = self._make_key(identifier, window)
            pipe = self._client.pipeline()
            pipe.incrby(key, amount)
            pipe.expire(key, ttl)
            results = await pipe.execute()
            return results[0]  # Return new count
        except Exception as e:
            logger.warning("Redis increment failed", error=str(e))
            return 0

    async def get_concurrent(self, identifier: str) -> int:
        """Get current concurrent request count."""
        if not await self._ensure_connected():
            return 0

        try:
            key = self._make_key(identifier, "concurrent")
            count = await self._client.get(key)
            return int(count) if count else 0
        except Exception:
            return 0

    async def incr_concurrent(self, identifier: str, ttl: int = 300) -> int:
        """Increment concurrent counter."""
        if not await self._ensure_connected():
            return 0

        try:
            key = self._make_key(identifier, "concurrent")
            pipe = self._client.pipeline()
            pipe.incr(key)
            pipe.expire(key, ttl)  # Auto-expire as safety net
            results = await pipe.execute()
            return results[0]
        except Exception:
            return 0

    async def decr_concurrent(self, identifier: str) -> int:
        """Decrement concurrent counter."""
        if not await self._ensure_connected():
            return 0

        try:
            key = self._make_key(identifier, "concurrent")
            count = await self._client.decr(key)
            # Ensure non-negative
            if count < 0:
                await self._client.set(key, 0)
                return 0
            return count
        except Exception:
            return 0

    async def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None


class RateLimiter:
    """
    Rate limiter using sliding window algorithm.

    Supports:
    - Per-user and global rate limiting
    - Request count limits
    - Token usage limits
    - Concurrent request limits
    - Distributed rate limiting via Redis
    """

    def __init__(self, config: RateLimitConfig):
        """
        Initialize rate limiter.

        Args:
            config: RateLimitConfig with limit settings
        """
        self.config = config
        self._enabled = config.enabled

        # Redis backend for distributed rate limiting
        self._redis_backend: Optional[RedisRateLimitBackend] = None
        if config.use_redis:
            self._redis_backend = RedisRateLimitBackend(config)

        # In-memory fallback state
        self._user_minute_state: Dict[str, RateLimitState] = defaultdict(RateLimitState)
        self._user_hour_state: Dict[str, RateLimitState] = defaultdict(RateLimitState)

        # Global state
        self._global_minute_state = RateLimitState()
        self._global_hour_state = RateLimitState()

        # Concurrent request tracking
        self._concurrent_requests: Dict[str, int] = defaultdict(int)
        self._global_concurrent = 0

        # Lock for thread safety (in-memory operations)
        self._lock = asyncio.Lock()

        logger.info(
            "Rate limiter initialized",
            enabled=config.enabled,
            requests_per_minute=config.requests_per_minute,
            tokens_per_minute=config.tokens_per_minute,
            distributed=config.use_redis
        )

    def _get_identifier(
        self,
        user_id: Optional[str],
        session_id: Optional[str] = None
    ) -> str:
        """
        Get rate limit identifier, handling null user_id securely.

        Args:
            user_id: User identifier (may be None)
            session_id: Session identifier as fallback

        Returns:
            Identifier string for rate limiting

        Raises:
            RateLimitExceeded: If user_id required but not provided
        """
        if user_id:
            return user_id

        # Null user_id handling
        if self.config.require_user_id:
            raise RateLimitExceeded(
                "User identification required for rate limiting",
                limit_type="authentication",
                retry_after=None
            )

        # Fallback to session ID
        if self.config.fallback_to_session and session_id:
            return f"session:{session_id}"

        # Last resort: use "anonymous" bucket (shared limit)
        # This prevents bypass but may be stricter for legitimate anonymous users
        return "anonymous"

    async def check_limit(
        self,
        user_id: Optional[str] = None,
        estimated_tokens: int = 0,
        session_id: Optional[str] = None
    ) -> bool:
        """
        Check if a request is within rate limits.

        Args:
            user_id: Optional user identifier for per-user limits
            estimated_tokens: Estimated tokens for this request
            session_id: Optional session ID as fallback identifier

        Returns:
            True if within limits

        Raises:
            RateLimitExceeded: If any limit is exceeded
        """
        if not self._enabled:
            return True

        identifier = self._get_identifier(user_id, session_id)
        now = time.time()

        if self._redis_backend and self.config.use_redis:
            return await self._check_limit_redis(identifier, estimated_tokens, now)
        else:
            return await self._check_limit_memory(identifier, estimated_tokens, now)

    async def _check_limit_redis(
        self,
        identifier: str,
        estimated_tokens: int,
        now: float
    ) -> bool:
        """Check limits using Redis backend."""
        # Current minute window key
        minute_window = f"minute:{int(now // 60)}"
        hour_window = f"hour:{int(now // 3600)}"

        # Check concurrent limit
        concurrent = await self._redis_backend.get_concurrent(identifier)
        if concurrent >= self.config.max_concurrent_requests:
            raise RateLimitExceeded(
                f"Too many concurrent requests: {concurrent}/{self.config.max_concurrent_requests}",
                limit_type="concurrent",
                retry_after=1.0
            )

        # Check request limits
        minute_count = await self._redis_backend.get_count(identifier, minute_window)
        max_requests = int(self.config.requests_per_minute * self.config.burst_multiplier)

        if minute_count >= max_requests:
            retry_after = 60 - (now % 60)
            raise RateLimitExceeded(
                f"Rate limit exceeded: {minute_count}/{self.config.requests_per_minute} per minute",
                limit_type="requests_per_minute",
                retry_after=retry_after
            )

        hour_count = await self._redis_backend.get_count(identifier, hour_window)
        if hour_count >= self.config.requests_per_hour:
            retry_after = 3600 - (now % 3600)
            raise RateLimitExceeded(
                f"Rate limit exceeded: {hour_count}/{self.config.requests_per_hour} per hour",
                limit_type="requests_per_hour",
                retry_after=retry_after
            )

        return True

    async def _check_limit_memory(
        self,
        identifier: str,
        estimated_tokens: int,
        now: float
    ) -> bool:
        """Check limits using in-memory state."""
        async with self._lock:
            # Clean up old windows
            self._cleanup_windows(now)

            # Check concurrent limit
            await self._check_concurrent_limit(identifier)

            # Check request limits
            await self._check_request_limit(identifier, now)

            # Check token limits
            if estimated_tokens > 0:
                await self._check_token_limit(identifier, estimated_tokens, now)

            return True

    async def _check_concurrent_limit(self, identifier: str) -> None:
        """Check concurrent request limit."""
        current = self._concurrent_requests[identifier] if self.config.per_user else self._global_concurrent

        if current >= self.config.max_concurrent_requests:
            logger.warning(
                "Concurrent request limit exceeded",
                identifier=identifier,
                current=current,
                limit=self.config.max_concurrent_requests
            )
            raise RateLimitExceeded(
                f"Too many concurrent requests: {current}/{self.config.max_concurrent_requests}",
                limit_type="concurrent",
                retry_after=1.0
            )

    async def _check_request_limit(self, identifier: str, now: float) -> None:
        """Check request count limits."""
        # Per-minute limit
        minute_state = self._user_minute_state[identifier] if self.config.per_user else self._global_minute_state

        if now - minute_state.window_start >= 60:
            minute_state.count = 0
            minute_state.window_start = now

        max_requests = int(self.config.requests_per_minute * self.config.burst_multiplier)
        if minute_state.count >= max_requests:
            retry_after = 60 - (now - minute_state.window_start)
            logger.warning(
                "Request rate limit exceeded (per minute)",
                identifier=identifier,
                count=minute_state.count,
                limit=self.config.requests_per_minute
            )
            raise RateLimitExceeded(
                f"Rate limit exceeded: {minute_state.count}/{self.config.requests_per_minute} requests per minute",
                limit_type="requests_per_minute",
                retry_after=max(0, retry_after)
            )

        # Per-hour limit
        hour_state = self._user_hour_state[identifier] if self.config.per_user else self._global_hour_state

        if now - hour_state.window_start >= 3600:
            hour_state.count = 0
            hour_state.window_start = now

        if hour_state.count >= self.config.requests_per_hour:
            retry_after = 3600 - (now - hour_state.window_start)
            logger.warning(
                "Request rate limit exceeded (per hour)",
                identifier=identifier,
                count=hour_state.count,
                limit=self.config.requests_per_hour
            )
            raise RateLimitExceeded(
                f"Rate limit exceeded: {hour_state.count}/{self.config.requests_per_hour} requests per hour",
                limit_type="requests_per_hour",
                retry_after=max(0, retry_after)
            )

    async def _check_token_limit(
        self,
        identifier: str,
        tokens: int,
        now: float
    ) -> None:
        """Check token usage limits."""
        minute_state = self._user_minute_state[identifier] if self.config.per_user else self._global_minute_state

        max_tokens = int(self.config.tokens_per_minute * self.config.burst_multiplier)
        if minute_state.tokens + tokens > max_tokens:
            retry_after = 60 - (now - minute_state.window_start)
            logger.warning(
                "Token rate limit exceeded",
                identifier=identifier,
                current_tokens=minute_state.tokens,
                requested=tokens,
                limit=self.config.tokens_per_minute
            )
            raise RateLimitExceeded(
                f"Token limit exceeded: {minute_state.tokens + tokens}/{self.config.tokens_per_minute} tokens per minute",
                limit_type="tokens_per_minute",
                retry_after=max(0, retry_after)
            )

    async def record_request(
        self,
        user_id: Optional[str] = None,
        tokens_used: int = 0,
        session_id: Optional[str] = None
    ) -> None:
        """
        Record a completed request for rate limiting.

        Args:
            user_id: Optional user identifier
            tokens_used: Actual tokens used
            session_id: Optional session ID as fallback
        """
        if not self._enabled:
            return

        identifier = self._get_identifier(user_id, session_id)
        now = time.time()

        if self._redis_backend and self.config.use_redis:
            minute_window = f"minute:{int(now // 60)}"
            hour_window = f"hour:{int(now // 3600)}"

            await self._redis_backend.increment(identifier, minute_window, 120)  # 2 min TTL
            await self._redis_backend.increment(identifier, hour_window, 7200)  # 2 hour TTL
        else:
            async with self._lock:
                # Update minute state
                minute_state = self._user_minute_state[identifier] if self.config.per_user else self._global_minute_state
                minute_state.count += 1
                minute_state.tokens += tokens_used

                # Update hour state
                hour_state = self._user_hour_state[identifier] if self.config.per_user else self._global_hour_state
                hour_state.count += 1
                hour_state.tokens += tokens_used

        logger.debug(
            "Recorded request",
            identifier=identifier,
            tokens=tokens_used
        )

    async def acquire_concurrent_slot(
        self,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> None:
        """Acquire a concurrent request slot."""
        if not self._enabled:
            return

        identifier = self._get_identifier(user_id, session_id)

        if self._redis_backend and self.config.use_redis:
            await self._redis_backend.incr_concurrent(identifier)
        else:
            async with self._lock:
                if self.config.per_user:
                    self._concurrent_requests[identifier] += 1
                else:
                    self._global_concurrent += 1

    async def release_concurrent_slot(
        self,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> None:
        """Release a concurrent request slot."""
        if not self._enabled:
            return

        identifier = self._get_identifier(user_id, session_id)

        if self._redis_backend and self.config.use_redis:
            await self._redis_backend.decr_concurrent(identifier)
        else:
            async with self._lock:
                if self.config.per_user:
                    self._concurrent_requests[identifier] = max(0, self._concurrent_requests[identifier] - 1)
                else:
                    self._global_concurrent = max(0, self._global_concurrent - 1)

    def _cleanup_windows(self, now: float) -> None:
        """Clean up expired rate limit windows."""
        # Clean up minute windows older than 2 minutes
        expired_minute = [
            k for k, v in self._user_minute_state.items()
            if now - v.window_start > 120
        ]
        for k in expired_minute:
            del self._user_minute_state[k]

        # Clean up hour windows older than 2 hours
        expired_hour = [
            k for k, v in self._user_hour_state.items()
            if now - v.window_start > 7200
        ]
        for k in expired_hour:
            del self._user_hour_state[k]

        # Clean up concurrent counters that are zero
        expired_concurrent = [
            k for k, v in self._concurrent_requests.items()
            if v == 0
        ]
        for k in expired_concurrent:
            del self._concurrent_requests[k]

    def get_usage(self, user_id: Optional[str] = None) -> Dict:
        """Get current usage statistics for a user."""
        identifier = user_id or "global"

        minute_state = self._user_minute_state.get(identifier, RateLimitState())
        hour_state = self._user_hour_state.get(identifier, RateLimitState())

        return {
            "requests_minute": {
                "used": minute_state.count,
                "limit": self.config.requests_per_minute,
                "remaining": max(0, self.config.requests_per_minute - minute_state.count)
            },
            "requests_hour": {
                "used": hour_state.count,
                "limit": self.config.requests_per_hour,
                "remaining": max(0, self.config.requests_per_hour - hour_state.count)
            },
            "tokens_minute": {
                "used": minute_state.tokens,
                "limit": self.config.tokens_per_minute,
                "remaining": max(0, self.config.tokens_per_minute - minute_state.tokens)
            },
            "concurrent": {
                "used": self._concurrent_requests.get(identifier, 0),
                "limit": self.config.max_concurrent_requests
            }
        }

    def reset(self, user_id: Optional[str] = None) -> None:
        """Reset rate limits for a user (admin function)."""
        if user_id:
            self._user_minute_state.pop(user_id, None)
            self._user_hour_state.pop(user_id, None)
            self._concurrent_requests.pop(user_id, None)
        else:
            self._user_minute_state.clear()
            self._user_hour_state.clear()
            self._concurrent_requests.clear()
            self._global_minute_state = RateLimitState()
            self._global_hour_state = RateLimitState()
            self._global_concurrent = 0

        logger.info("Rate limits reset", user_id=user_id or "all")

    async def close(self) -> None:
        """Close rate limiter and release resources."""
        if self._redis_backend:
            await self._redis_backend.close()

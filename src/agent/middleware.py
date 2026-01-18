"""
Agent Framework Middleware

Provides function-level middleware to intercept and monitor tool calls.
Follows Agent Framework middleware patterns for logging, security, and transformation.
Includes RBAC (Role-Based Access Control) for tool authorization.
"""

import time
from dataclasses import dataclass, field
from typing import Callable, Awaitable, Dict, List, Optional, Set
import structlog

# Import Agent Framework middleware types
try:
    from agent_framework import FunctionInvocationContext
except ImportError:
    # Fallback if agent_framework not available or different structure
    class FunctionInvocationContext:
        """Minimal FunctionInvocationContext for type hints."""
        function: any
        args: dict
        result: any

from src.observability import get_tracer
from src.observability.tracing import trace_tool_execution

logger = structlog.get_logger(__name__)


# ==================== RBAC Classes ====================


class ToolAccessDenied(Exception):
    """Raised when a user attempts to access a tool they're not authorized for."""

    def __init__(self, user_id: str, tool_name: str, required_roles: Set[str]):
        self.user_id = user_id
        self.tool_name = tool_name
        self.required_roles = required_roles
        super().__init__(
            f"User '{user_id}' denied access to tool '{tool_name}'. "
            f"Required roles: {required_roles}"
        )


@dataclass
class RBACConfig:
    """
    Configuration for Role-Based Access Control.

    Example configuration:
        rbac_config = RBACConfig(
            enabled=True,
            default_policy="deny",  # deny or allow
            role_permissions={
                "admin": {"*"},  # Admins can use all tools
                "analyst": {"query_tool", "search_tool", "export_tool"},
                "viewer": {"search_tool"},
            },
            tool_requirements={
                "admin_tool": {"admin"},
                "delete_tool": {"admin"},
                "query_tool": {"admin", "analyst"},
            }
        )
    """
    enabled: bool = False
    # Default policy: "allow" (whitelist approach) or "deny" (blacklist approach)
    default_policy: str = "allow"
    # Maps role -> set of tool names that role can access ("*" means all)
    role_permissions: Dict[str, Set[str]] = field(default_factory=dict)
    # Maps tool_name -> set of roles required (any of these roles grants access)
    tool_requirements: Dict[str, Set[str]] = field(default_factory=dict)
    # Audit all access decisions
    audit_decisions: bool = True


class ToolRBAC:
    """
    Role-Based Access Control for tool authorization.

    Supports two modes:
    1. Role-based: Define which tools each role can access
    2. Tool-based: Define which roles are required for each tool

    When both are specified, access is granted if EITHER condition is met.
    """

    def __init__(self, config: RBACConfig):
        """Initialize RBAC with configuration."""
        self.config = config
        self._user_roles: Dict[str, Set[str]] = {}

    def set_user_roles(self, user_id: str, roles: Set[str]) -> None:
        """
        Set roles for a user.

        Args:
            user_id: User identifier
            roles: Set of role names
        """
        self._user_roles[user_id] = roles
        logger.debug("User roles updated", user_id=user_id, roles=roles)

    def get_user_roles(self, user_id: str) -> Set[str]:
        """Get roles for a user."""
        return self._user_roles.get(user_id, set())

    def clear_user_roles(self, user_id: str) -> None:
        """Remove role assignments for a user."""
        self._user_roles.pop(user_id, None)

    def check_access(
        self,
        user_id: str,
        tool_name: str,
        user_roles: Optional[Set[str]] = None
    ) -> bool:
        """
        Check if a user has access to a tool.

        Args:
            user_id: User identifier
            tool_name: Name of the tool being accessed
            user_roles: Optional roles to use (overrides stored roles)

        Returns:
            True if access is granted
        """
        if not self.config.enabled:
            return True

        # Get user roles
        roles = user_roles or self._user_roles.get(user_id, set())

        # Check role-based permissions
        for role in roles:
            allowed_tools = self.config.role_permissions.get(role, set())
            if "*" in allowed_tools or tool_name in allowed_tools:
                self._log_decision(user_id, tool_name, roles, True, "role_permission")
                return True

        # Check tool-based requirements
        required_roles = self.config.tool_requirements.get(tool_name)
        if required_roles:
            # If tool has requirements, user must have at least one required role
            if roles & required_roles:
                self._log_decision(user_id, tool_name, roles, True, "tool_requirement")
                return True
        else:
            # No specific requirements for this tool
            if self.config.default_policy == "allow":
                self._log_decision(user_id, tool_name, roles, True, "default_allow")
                return True

        # Access denied
        self._log_decision(user_id, tool_name, roles, False, "denied")
        return False

    def require_access(
        self,
        user_id: str,
        tool_name: str,
        user_roles: Optional[Set[str]] = None
    ) -> None:
        """
        Require access to a tool, raising exception if denied.

        Args:
            user_id: User identifier
            tool_name: Name of the tool
            user_roles: Optional roles to use

        Raises:
            ToolAccessDenied: If access is denied
        """
        if not self.check_access(user_id, tool_name, user_roles):
            required_roles = self.config.tool_requirements.get(tool_name, set())
            raise ToolAccessDenied(user_id, tool_name, required_roles)

    def _log_decision(
        self,
        user_id: str,
        tool_name: str,
        roles: Set[str],
        allowed: bool,
        reason: str
    ) -> None:
        """Log access decision for auditing."""
        if self.config.audit_decisions:
            logger.info(
                "[RBAC] Access decision",
                user_id=user_id,
                tool_name=tool_name,
                roles=list(roles),
                allowed=allowed,
                reason=reason
            )

    def get_allowed_tools(self, user_id: str) -> Set[str]:
        """
        Get all tools a user is allowed to access.

        Args:
            user_id: User identifier

        Returns:
            Set of tool names the user can access
        """
        if not self.config.enabled:
            return {"*"}  # All tools allowed

        roles = self._user_roles.get(user_id, set())
        allowed = set()

        for role in roles:
            role_tools = self.config.role_permissions.get(role, set())
            if "*" in role_tools:
                return {"*"}  # User has access to all tools
            allowed.update(role_tools)

        # Add tools with matching requirements
        for tool_name, required_roles in self.config.tool_requirements.items():
            if roles & required_roles:
                allowed.add(tool_name)

        return allowed


def create_rbac_middleware(rbac: ToolRBAC, get_user_id: Callable = None):
    """
    Create RBAC middleware for tool authorization.

    Args:
        rbac: ToolRBAC instance
        get_user_id: Optional function to extract user ID from context.
                     If not provided, looks for user_id in context.args

    Returns:
        Middleware function

    Example:
        rbac = ToolRBAC(RBACConfig(
            enabled=True,
            role_permissions={"admin": {"*"}, "user": {"safe_tool"}},
        ))
        rbac.set_user_roles("user123", {"user"})

        middleware = create_rbac_middleware(rbac)
    """
    async def rbac_middleware(
        context: FunctionInvocationContext,
        next: Callable[[FunctionInvocationContext], Awaitable[None]],
    ) -> None:
        """
        RBAC middleware for tool authorization.

        Checks if the current user has permission to use the requested tool.
        """
        if not rbac.config.enabled:
            await next(context)
            return

        function_name = getattr(context.function, 'name', 'unknown')

        # Extract user ID
        user_id = None
        if get_user_id:
            user_id = get_user_id(context)
        elif hasattr(context, 'args') and context.args:
            user_id = context.args.get('user_id') or context.args.get('_user_id')

        if not user_id:
            # No user ID - check default policy
            if rbac.config.default_policy == "deny":
                logger.warning(
                    "[RBAC MIDDLEWARE] No user ID, access denied",
                    function_name=function_name
                )
                raise ToolAccessDenied("unknown", function_name, set())
            # Default allow - proceed
            await next(context)
            return

        # Check RBAC
        try:
            rbac.require_access(user_id, function_name)
            await next(context)
        except ToolAccessDenied:
            logger.warning(
                "[RBAC MIDDLEWARE] Access denied",
                function_name=function_name,
                user_id=user_id
            )
            raise

    return rbac_middleware


async def function_call_middleware(
    context: FunctionInvocationContext,
    next: Callable[[FunctionInvocationContext], Awaitable[None]],
) -> None:
    """
    Middleware that intercepts function (tool) calls.

    This middleware:
    1. Logs when a function is called
    2. Records tracing spans for observability
    3. Measures execution time
    4. Logs the result

    Args:
        context: Function invocation context with function metadata and arguments
        next: Continuation function to invoke the actual tool
    """
    function_name = getattr(context.function, 'name', 'unknown')
    args_preview = str(context.args)[:200] if hasattr(context, 'args') else 'N/A'
    start_time = time.perf_counter()

    tracer = get_tracer()

    with tracer.start_as_current_span("tool_execution") as span:
        span.set_attribute("tool.name", function_name)
        span.set_attribute("tool.args_preview", args_preview)

        logger.info(
            "[MIDDLEWARE] Function call starting",
            function_name=function_name,
            args_preview=args_preview
        )

        try:
            # Continue to actual function execution
            await next(context)

            # Calculate execution time
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            # Log successful completion
            result_preview = str(context.result)[:200] if hasattr(context, 'result') and context.result else 'N/A'

            span.set_attribute("tool.success", True)
            span.set_attribute("tool.latency_ms", elapsed_ms)

            logger.info(
                "[MIDDLEWARE] Function call completed",
                function_name=function_name,
                result_preview=result_preview,
                elapsed_ms=round(elapsed_ms, 2)
            )

            # Record metrics
            try:
                from src.observability import get_metrics
                metrics = get_metrics()
                metrics.record_tool_call(function_name, elapsed_ms, success=True)
            except Exception:
                pass  # Don't fail if metrics not available

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            span.set_attribute("tool.success", False)
            span.set_attribute("tool.error", str(e))
            span.record_exception(e)

            logger.error(
                "[MIDDLEWARE] Function call failed",
                function_name=function_name,
                error=str(e),
                elapsed_ms=round(elapsed_ms, 2),
                exc_info=True
            )

            # Record metrics
            try:
                from src.observability import get_metrics
                metrics = get_metrics()
                metrics.record_tool_call(function_name, elapsed_ms, success=False)
                metrics.record_error(type(e).__name__, f"tool_{function_name}")
            except Exception:
                pass

            # Re-raise to let agent framework handle it
            raise


def create_security_middleware(validator: Optional["InputValidator"] = None):
    """
    Create a security middleware that validates tool call parameters.

    Args:
        validator: Optional InputValidator instance for parameter validation

    Returns:
        Middleware function
    """
    async def security_middleware(
        context: FunctionInvocationContext,
        next: Callable[[FunctionInvocationContext], Awaitable[None]],
    ) -> None:
        """
        Security middleware for authorization and input validation.

        Validates:
        - Tool parameters for injection attempts
        - Sensitive data exposure
        - Rate limits (if configured)
        """
        function_name = getattr(context.function, 'name', 'unknown')

        logger.debug(
            "[SECURITY MIDDLEWARE] Checking authorization",
            function_name=function_name
        )

        # Validate parameters if validator provided
        if validator and hasattr(context, 'args') and context.args:
            try:
                for key, value in context.args.items():
                    if isinstance(value, str):
                        # Validate string parameters
                        validated = validator.validate(value, context="tool_param")
                        context.args[key] = validated
            except Exception as e:
                logger.warning(
                    "[SECURITY MIDDLEWARE] Parameter validation failed",
                    function_name=function_name,
                    error=str(e)
                )
                raise

        await next(context)

    return security_middleware


async def performance_middleware(
    context: FunctionInvocationContext,
    next: Callable[[FunctionInvocationContext], Awaitable[None]],
) -> None:
    """
    Performance monitoring middleware.

    Tracks execution time and logs slow operations.
    """
    function_name = getattr(context.function, 'name', 'unknown')
    start_time = time.perf_counter()

    logger.debug(
        "[PERFORMANCE MIDDLEWARE] Starting timer",
        function_name=function_name
    )

    try:
        await next(context)
    finally:
        elapsed_time = time.perf_counter() - start_time
        elapsed_ms = elapsed_time * 1000

        logger.info(
            "[PERFORMANCE MIDDLEWARE] Execution complete",
            function_name=function_name,
            elapsed_ms=round(elapsed_ms, 2)
        )

        # Warn about slow operations (> 10 seconds)
        if elapsed_time > 10.0:
            logger.warning(
                "[PERFORMANCE MIDDLEWARE] Slow operation detected",
                function_name=function_name,
                elapsed_seconds=round(elapsed_time, 3)
            )


async def rate_limit_middleware(
    context: FunctionInvocationContext,
    next: Callable[[FunctionInvocationContext], Awaitable[None]],
    rate_limiter: Optional["RateLimiter"] = None,
) -> None:
    """
    Rate limiting middleware for tool calls.

    Args:
        context: Function invocation context
        next: Continuation function
        rate_limiter: Optional RateLimiter instance
    """
    function_name = getattr(context.function, 'name', 'unknown')

    if rate_limiter:
        try:
            # Check tool-specific rate limit
            await rate_limiter.check_limit(identifier=f"tool:{function_name}")
        except Exception as e:
            logger.warning(
                "[RATE LIMIT MIDDLEWARE] Rate limit exceeded for tool",
                function_name=function_name,
                error=str(e)
            )
            raise

    await next(context)

    # Record the tool call for rate limiting
    if rate_limiter:
        await rate_limiter.record_request(identifier=f"tool:{function_name}")


def create_audit_middleware(audit_log_fn: Callable = None):
    """
    Create an audit logging middleware.

    Args:
        audit_log_fn: Optional custom audit log function

    Returns:
        Middleware function
    """
    async def audit_middleware(
        context: FunctionInvocationContext,
        next: Callable[[FunctionInvocationContext], Awaitable[None]],
    ) -> None:
        """
        Audit logging middleware.

        Records all tool calls for compliance and debugging.
        """
        function_name = getattr(context.function, 'name', 'unknown')
        args = dict(context.args) if hasattr(context, 'args') else {}

        # Sanitize sensitive fields
        sensitive_keys = {'password', 'token', 'secret', 'key', 'credential', 'auth'}
        sanitized_args = {
            k: '[REDACTED]' if any(s in k.lower() for s in sensitive_keys) else v
            for k, v in args.items()
        }

        audit_entry = {
            "event": "tool_call",
            "function": function_name,
            "args": sanitized_args,
            "timestamp": time.time(),
        }

        try:
            await next(context)
            audit_entry["success"] = True
            audit_entry["result_preview"] = str(context.result)[:100] if context.result else None
        except Exception as e:
            audit_entry["success"] = False
            audit_entry["error"] = str(e)
            raise
        finally:
            if audit_log_fn:
                audit_log_fn(audit_entry)
            else:
                logger.info("[AUDIT] Tool call recorded", **audit_entry)

    return audit_middleware


# Middleware combiner for stacking multiple middleware
def combine_middleware(*middleware_fns):
    """
    Combine multiple middleware functions into a single middleware.

    Args:
        *middleware_fns: Variable number of middleware functions

    Returns:
        Combined middleware function

    Example:
        combined = combine_middleware(
            function_call_middleware,
            security_middleware,
            performance_middleware
        )
    """
    async def combined_middleware(
        context: FunctionInvocationContext,
        next: Callable[[FunctionInvocationContext], Awaitable[None]],
    ) -> None:
        # Build middleware chain from inside out
        chain = next
        for middleware in reversed(middleware_fns):
            # Capture middleware in closure
            def make_wrapper(mw, inner):
                async def wrapper(ctx):
                    await mw(ctx, inner)
                return wrapper
            chain = make_wrapper(middleware, chain)

        await chain(context)

    return combined_middleware

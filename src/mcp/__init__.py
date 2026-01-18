"""
MCP (Model Context Protocol) session management package.

Provides session handling for stateful MCP servers like D365 ERP
that require session continuity across tool invocations.
"""

from src.mcp.session import (
    MCPSessionState,
    MCPSessionManager,
    MCPSessionConfig,
    parse_mcp_session_config,
)
from src.mcp.session_aware_tool import SessionAwareMCPTool, wrap_stateful_tools

__all__ = [
    "MCPSessionState",
    "MCPSessionManager",
    "MCPSessionConfig",
    "SessionAwareMCPTool",
    "parse_mcp_session_config",
    "wrap_stateful_tools",
]

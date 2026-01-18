"""
MCP (Model Context Protocol) loader for the AI Assistant.

Loads and manages MCP server connections from configuration.
Supports three MCP transport types:
- stdio: Local process-based MCP servers
- http: HTTP/SSE MCP servers
- websocket: WebSocket MCP servers
"""

import asyncio
from typing import Any, Dict, List, Optional, Set, TYPE_CHECKING
from contextlib import AsyncExitStack
from urllib.parse import urlparse

import structlog

# Import MCP tool types from Agent Framework
try:
    from agent_framework import MCPStdioTool, MCPStreamableHTTPTool, MCPWebsocketTool
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    MCPStdioTool = None
    MCPStreamableHTTPTool = None
    MCPWebsocketTool = None

if TYPE_CHECKING:
    from src.mcp.session import MCPSessionManager

logger = structlog.get_logger(__name__)


class MCPManager:
    """
    Manages MCP server connections for the AI Assistant.
    
    Loads MCP configurations and creates appropriate tool instances
    based on transport type (stdio, http, websocket).
    
    Enhanced with session management support for stateful MCP servers
    like D365 ERP that require session continuity.
    """
    
    def __init__(self):
        """Initialize the MCP manager."""
        self._exit_stack: Optional[AsyncExitStack] = None
        self._mcp_tools: List[Any] = []
        self._mcp_configs: List[Dict[str, Any]] = []
        self._session_manager: Optional["MCPSessionManager"] = None
        self._stateful_servers: Set[str] = set()
        self._initialized = False

    def set_session_manager(self, manager: "MCPSessionManager") -> None:
        """
        Attach session manager for stateful MCP servers.
        
        When a session manager is attached, stateful MCP tools will be
        wrapped to automatically inject session context.
        
        Args:
            manager: MCPSessionManager instance
        """
        self._session_manager = manager
        
        # Re-wrap tools if already loaded
        if self._initialized and self._mcp_tools:
            self._wrap_stateful_tools()
            logger.info(
                "Session manager attached to MCP manager",
                stateful_servers=list(self._stateful_servers)
            )
        
    async def load_mcp_servers(self, mcp_configs: List[Dict[str, Any]]) -> List[Any]:
        """
        Load and initialize MCP servers from configuration.
        
        Args:
            mcp_configs: List of MCP server configurations, each containing:
                - name: Friendly name for the MCP server
                - type: "stdio", "http", or "websocket"
                - enabled: Whether this MCP is enabled (default: true)
                - stateful: Whether this server requires session management (default: false)
                - session_header: Header name for session ID (for stateful servers)
                - form_context_header: Header name for form context (for D365)
                - requires_user_id: Whether user_id is required (for stateful servers)
                
                For stdio type:
                - command: Command to run (e.g., "uvx", "npx")
                - args: List of arguments
                - env: Optional environment variables dict
                
                For http type:
                - url: HTTP URL of the MCP server
                - headers: Optional headers dict (for auth, etc.)
                
                For websocket type:
                - url: WebSocket URL (wss://...)
                - headers: Optional headers dict (for auth, etc.)
                
        Returns:
            List of initialized MCP tool instances
        """
        if not MCP_AVAILABLE:
            logger.warning(
                "MCP tools not available. Install agent-framework with MCP support."
            )
            return []
        
        if not mcp_configs:
            logger.debug("No MCP servers configured")
            return []
        
        # Store configs for later session wrapping
        self._mcp_configs = mcp_configs
        
        self._exit_stack = AsyncExitStack()
        await self._exit_stack.__aenter__()
        
        for config in mcp_configs:
            # Skip disabled MCPs
            if not config.get("enabled", True):
                logger.debug("Skipping disabled MCP", name=config.get("name"))
                continue
            
            # Track stateful servers
            if config.get("stateful", False):
                self._stateful_servers.add(config.get("name", ""))
                
            try:
                mcp_tool = await self._create_mcp_tool(config)
                if mcp_tool:
                    self._mcp_tools.append(mcp_tool)
                    logger.info(
                        "Loaded MCP server",
                        name=config.get("name"),
                        type=config.get("type"),
                        stateful=config.get("stateful", False)
                    )
            except Exception as e:
                logger.error(
                    "Failed to load MCP server",
                    name=config.get("name"),
                    error=str(e)
                )
        
        self._initialized = True
        
        # Wrap stateful tools if session manager is available
        if self._session_manager and self._stateful_servers:
            self._wrap_stateful_tools()
        
        logger.info(
            "MCP servers loaded",
            count=len(self._mcp_tools),
            stateful_count=len(self._stateful_servers)
        )
        return self._mcp_tools

    def _wrap_stateful_tools(self) -> None:
        """Wrap stateful MCP tools with session awareness."""
        if not self._session_manager:
            return
        
        from src.mcp.session_aware_tool import SessionAwareMCPTool
        
        # Build config lookup for stateful servers
        stateful_configs: Dict[str, Dict[str, Any]] = {}
        for config in self._mcp_configs:
            if config.get("stateful", False):
                stateful_configs[config.get("name", "")] = config
        
        # Wrap the tools
        wrapped_tools = []
        for tool in self._mcp_tools:
            tool_name = getattr(tool, "name", str(tool))
            
            if tool_name in stateful_configs:
                wrapped_tool = SessionAwareMCPTool(
                    mcp_tool=tool,
                    session_manager=self._session_manager,
                    server_config=stateful_configs[tool_name],
                )
                wrapped_tools.append(wrapped_tool)
                logger.debug("Wrapped stateful MCP tool", tool_name=tool_name)
            else:
                wrapped_tools.append(tool)
        
        self._mcp_tools = wrapped_tools
        logger.info("Wrapped stateful MCP tools", count=len(stateful_configs))
    
    async def _create_mcp_tool(self, config: Dict[str, Any]) -> Optional[Any]:
        """Create an MCP tool instance based on configuration."""
        mcp_type = config.get("type", "").lower()
        name = config.get("name", "unnamed-mcp")
        
        if mcp_type == "stdio":
            return await self._create_stdio_mcp(config)
        elif mcp_type == "http":
            return await self._create_http_mcp(config)
        elif mcp_type == "websocket":
            return await self._create_websocket_mcp(config)
        else:
            logger.error("Unknown MCP type", name=name, type=mcp_type)
            return None
    
    async def _create_stdio_mcp(self, config: Dict[str, Any]) -> Any:
        """Create a stdio-based MCP tool."""
        command = config.get("command")
        if not command:
            raise ValueError(f"MCP '{config.get('name')}' requires 'command' for stdio type")
        
        mcp_tool = MCPStdioTool(
            name=config.get("name", "stdio-mcp"),
            command=command,
            args=config.get("args", []),
            env=config.get("env"),
        )
        
        # Enter the async context to initialize the MCP
        initialized_tool = await self._exit_stack.enter_async_context(mcp_tool)
        return initialized_tool
    
    def _validate_url_security(self, url: str, name: str, allow_insecure: bool = False) -> None:
        """
        Validate URL security requirements.

        Args:
            url: URL to validate
            name: MCP server name for error messages
            allow_insecure: If True, allow HTTP/WS (for local development only)

        Raises:
            ValueError: If URL doesn't meet security requirements
        """
        parsed = urlparse(url)

        # Check for HTTPS/WSS in production
        secure_schemes = {"https", "wss"}
        insecure_schemes = {"http", "ws"}

        if parsed.scheme in insecure_schemes:
            # Allow localhost/127.0.0.1 for local development
            is_local = parsed.hostname in ("localhost", "127.0.0.1", "::1")

            if not is_local and not allow_insecure:
                raise ValueError(
                    f"MCP '{name}' uses insecure URL scheme '{parsed.scheme}'. "
                    f"Use HTTPS/WSS for production or set allow_insecure=True for testing."
                )

            if not is_local:
                logger.warning(
                    "MCP server using insecure connection",
                    name=name,
                    scheme=parsed.scheme,
                    host=parsed.hostname
                )
        elif parsed.scheme not in secure_schemes:
            raise ValueError(f"MCP '{name}' has invalid URL scheme: {parsed.scheme}")

    async def _create_http_mcp(self, config: Dict[str, Any]) -> Any:
        """Create an HTTP-based MCP tool."""
        url = config.get("url")
        if not url:
            raise ValueError(f"MCP '{config.get('name')}' requires 'url' for http type")

        # Validate URL security
        self._validate_url_security(
            url,
            config.get("name", "http-mcp"),
            allow_insecure=config.get("allow_insecure", False)
        )

        mcp_tool = MCPStreamableHTTPTool(
            name=config.get("name", "http-mcp"),
            url=url,
            headers=config.get("headers", {}),
        )

        initialized_tool = await self._exit_stack.enter_async_context(mcp_tool)
        return initialized_tool

    async def _create_websocket_mcp(self, config: Dict[str, Any]) -> Any:
        """Create a WebSocket-based MCP tool."""
        url = config.get("url")
        if not url:
            raise ValueError(f"MCP '{config.get('name')}' requires 'url' for websocket type")

        # Validate URL security
        self._validate_url_security(
            url,
            config.get("name", "websocket-mcp"),
            allow_insecure=config.get("allow_insecure", False)
        )

        mcp_tool = MCPWebsocketTool(
            name=config.get("name", "websocket-mcp"),
            url=url,
            headers=config.get("headers", {}),
        )

        initialized_tool = await self._exit_stack.enter_async_context(mcp_tool)
        return initialized_tool
    
    @property
    def tools(self) -> List[Any]:
        """Get list of loaded MCP tools."""
        return self._mcp_tools
    
    async def close(self, timeout: float = 10.0) -> None:
        """
        Close all MCP connections with timeout.

        Args:
            timeout: Maximum seconds to wait for graceful shutdown (default: 10s)
        """
        if self._exit_stack:
            try:
                # Use timeout to prevent hanging on unresponsive MCP servers
                await asyncio.wait_for(
                    self._exit_stack.aclose(),
                    timeout=timeout
                )
                logger.info("Closed all MCP connections")
            except asyncio.TimeoutError:
                logger.warning(
                    "MCP connection close timed out, forcing shutdown",
                    timeout=timeout
                )
                # Force cleanup - connections may leak but won't block shutdown
            except Exception as e:
                logger.error("Error closing MCP connections", error=str(e))
            finally:
                self._exit_stack = None
                self._mcp_tools = []
                self._initialized = False


def parse_mcp_configs(config_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Parse MCP configurations from agent config.
    
    Supports two formats in TOML:
    
    1. Array format (recommended for multiple MCPs):
        [[agent.mcp]]
        name = "calculator"
        type = "stdio"
        command = "uvx"
        args = ["mcp-server-calculator"]
        
        [[agent.mcp]]
        name = "docs"
        type = "http"
        url = "https://api.example.com/mcp"
    
    2. Table format (for single MCP or named MCPs):
        [agent.mcp.calculator]
        type = "stdio"
        command = "uvx"
        args = ["mcp-server-calculator"]
    
    Args:
        config_dict: The agent configuration dictionary
        
    Returns:
        List of MCP configuration dictionaries
    """
    mcp_config = config_dict.get("mcp", {})
    
    # If it's a list, return as-is
    if isinstance(mcp_config, list):
        return mcp_config
    
    # If it's a dict, convert to list format
    if isinstance(mcp_config, dict):
        mcp_list = []
        for name, settings in mcp_config.items():
            if isinstance(settings, dict):
                # Add name from key if not specified
                if "name" not in settings:
                    settings["name"] = name
                mcp_list.append(settings)
        return mcp_list
    
    return []

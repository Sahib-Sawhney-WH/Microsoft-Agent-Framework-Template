"""
Decorator-based tool registration system for SDK-compliant tool development.

This module provides the @register_tool decorator and auto-discovery system
that enables SDK-compliant tool patterns using @ai_function with Annotated types.

Also provides SDK schema generation utilities to extract JSON schemas from
decorated tools for documentation, API responses, and OpenAI function calling.

Usage:
    from src.loaders.decorators import register_tool
    from typing import Annotated
    from pydantic import Field

    @register_tool(name="my_tool", tags=["demo"])
    def my_tool(
        message: Annotated[str, Field(description="Input message")],
    ) -> str:
        '''Tool docstring becomes AI's understanding.'''
        return f"Processed: {message}"
"""

import inspect
import sys
import importlib
import importlib.util
import structlog
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, get_type_hints, get_origin, get_args, Annotated

logger = structlog.get_logger(__name__)

# Global registry for decorated tools
_registered_tools: Dict[str, Callable] = {}
_tool_metadata: Dict[str, Dict] = {}


def register_tool(
    name: Optional[str] = None,
    tags: Optional[List[str]] = None,
    enabled: bool = True,
):
    """
    Decorator to register a tool for auto-discovery.
    
    This decorator marks a function as a tool and registers it in the global
    tool registry. Can be used alone or combined with @ai_function.
    
    Args:
        name: Tool name override. Defaults to function name.
        tags: Optional list of tags for categorization/filtering.
        enabled: Whether the tool is enabled. Disabled tools are not registered.
    
    Returns:
        Decorated function with registration metadata.
    
    Example:
        @register_tool(name="my_tool", tags=["demo"])
        @ai_function
        def my_tool(message: Annotated[str, Field(description="Input")]) -> str:
            '''Processes messages.'''
            return f"Result: {message}"
    """
    def decorator(func: Callable) -> Callable:
        if not enabled:
            logger.debug("Tool disabled, skipping registration", tool_name=name or func.__name__)
            return func
        
        tool_name = name or func.__name__
        
        # Store metadata
        _tool_metadata[tool_name] = {
            "tags": tags or [],
            "enabled": enabled,
            "source": "decorator",
            "module": func.__module__,
        }
        
        # Register the tool
        _registered_tools[tool_name] = func
        
        # Add metadata to function for introspection
        func._tool_name = tool_name
        func._tool_tags = tags or []
        func._tool_source = "decorator"
        
        logger.debug(
            "Registered decorator tool",
            tool_name=tool_name,
            tags=tags,
            module=func.__module__
        )
        
        return func
    
    return decorator


def get_registered_tools() -> Dict[str, Callable]:
    """
    Get all registered decorator-based tools.
    
    Returns:
        Dictionary mapping tool names to tool functions.
    """
    return _registered_tools.copy()


def get_tool_metadata(tool_name: str) -> Optional[Dict]:
    """
    Get metadata for a specific tool.
    
    Args:
        tool_name: Name of the tool.
        
    Returns:
        Tool metadata dict or None if not found.
    """
    return _tool_metadata.get(tool_name)


def get_tools_by_tag(tag: str) -> List[Callable]:
    """
    Get all tools with a specific tag.
    
    Args:
        tag: Tag to filter by.
        
    Returns:
        List of tool functions with the specified tag.
    """
    return [
        func for name, func in _registered_tools.items()
        if tag in _tool_metadata.get(name, {}).get("tags", [])
    ]


def clear_registry() -> None:
    """Clear all registered tools. Useful for testing."""
    _registered_tools.clear()
    _tool_metadata.clear()
    logger.debug("Tool registry cleared")


def discover_decorator_tools(
    tools_dir: str = "src",
    tool_file_pattern: str = "tools.py",
    exclude_dirs: Optional[Set[str]] = None,
) -> List[Callable]:
    """
    Scan for and import modules containing @register_tool decorated functions.
    
    This function walks through the specified directory tree, finds files
    matching the pattern (default: tools.py), and imports them to trigger
    tool registration via the @register_tool decorator.
    
    Args:
        tools_dir: Root directory to scan for tool modules.
        tool_file_pattern: Filename pattern to match (default: "tools.py").
        exclude_dirs: Set of directory names to skip (default: __pycache__, .git, etc).
        
    Returns:
        List of discovered and registered tool functions.
    """
    if exclude_dirs is None:
        exclude_dirs = {"__pycache__", ".git", ".pytest_cache", "node_modules", ".venv", "venv"}
    
    tools_path = Path(tools_dir)
    if not tools_path.exists():
        logger.warning("Tools directory not found", path=tools_dir)
        return []
    
    discovered_modules: List[str] = []
    
    # Walk directory tree
    for path in tools_path.rglob(tool_file_pattern):
        # Skip excluded directories
        if any(excluded in path.parts for excluded in exclude_dirs):
            continue
        
        # Convert path to module name
        # e.g., src/example_tool/tools.py -> src.example_tool.tools
        try:
            relative = path.relative_to(Path.cwd())
            module_name = str(relative.with_suffix("")).replace("\\", ".").replace("/", ".")
            discovered_modules.append(module_name)
        except ValueError:
            logger.warning("Could not determine module name", path=str(path))
            continue
    
    # Import discovered modules to trigger registration
    newly_registered = []
    before_count = len(_registered_tools)
    
    for module_name in discovered_modules:
        try:
            # Check if already imported
            if module_name in sys.modules:
                logger.debug("Module already imported", module=module_name)
                continue
            
            logger.debug("Importing tool module", module=module_name)
            importlib.import_module(module_name)
            
        except ImportError as e:
            logger.warning(
                "Failed to import tool module",
                module=module_name,
                error=str(e)
            )
        except Exception as e:
            logger.error(
                "Error loading tool module",
                module=module_name,
                error=str(e),
                exc_info=True
            )
    
    after_count = len(_registered_tools)
    newly_registered = list(_registered_tools.values())
    
    logger.info(
        "Tool discovery complete",
        modules_scanned=len(discovered_modules),
        tools_registered=after_count,
        new_tools=after_count - before_count
    )
    
    return newly_registered


def load_tool_modules(module_paths: List[str]) -> List[Callable]:
    """
    Explicitly load specific tool modules.
    
    This function imports the specified modules to trigger tool registration.
    Use this when you want explicit control over which modules are loaded.
    
    Args:
        module_paths: List of module paths to import (e.g., ["src.my_tool.tools"]).
        
    Returns:
        List of all registered tool functions after loading.
    """
    for module_path in module_paths:
        try:
            if module_path in sys.modules:
                # Reload to pick up changes
                importlib.reload(sys.modules[module_path])
            else:
                importlib.import_module(module_path)
            
            logger.debug("Loaded tool module", module=module_path)
            
        except ImportError as e:
            logger.error(
                "Failed to import tool module",
                module=module_path,
                error=str(e)
            )
        except Exception as e:
            logger.error(
                "Error loading tool module",
                module=module_path,
                error=str(e),
                exc_info=True
            )
    
    return list(_registered_tools.values())


# ==================== SDK Schema Generation ====================


def _python_type_to_json_type(python_type: type) -> str:
    """Convert Python type to JSON Schema type."""
    type_map = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
        type(None): "null",
    }

    # Handle generic types
    origin = get_origin(python_type)
    if origin is not None:
        if origin in (list, List):
            return "array"
        elif origin in (dict, Dict):
            return "object"

    return type_map.get(python_type, "string")


def _extract_field_info(annotation: Any) -> Dict[str, Any]:
    """
    Extract field information from Annotated type hints.

    Supports pydantic.Field and other annotation metadata.
    """
    field_info = {}

    # Check if it's Annotated
    origin = get_origin(annotation)
    if origin is Annotated:
        args = get_args(annotation)
        if args:
            # First arg is the actual type
            field_info["type"] = _python_type_to_json_type(args[0])

            # Look for Field metadata in remaining args
            for arg in args[1:]:
                if hasattr(arg, "description"):
                    field_info["description"] = arg.description
                if hasattr(arg, "default"):
                    if arg.default is not None and not callable(arg.default):
                        field_info["default"] = arg.default
                if hasattr(arg, "ge"):
                    field_info["minimum"] = arg.ge
                if hasattr(arg, "le"):
                    field_info["maximum"] = arg.le
                if hasattr(arg, "min_length"):
                    field_info["minLength"] = arg.min_length
                if hasattr(arg, "max_length"):
                    field_info["maxLength"] = arg.max_length
                if hasattr(arg, "pattern"):
                    field_info["pattern"] = arg.pattern

                # Handle enum
                if hasattr(arg, "json_schema_extra"):
                    extra = arg.json_schema_extra
                    if extra and "enum" in extra:
                        field_info["enum"] = extra["enum"]
    else:
        # Plain type annotation
        field_info["type"] = _python_type_to_json_type(annotation)

    return field_info


def extract_tool_schema(func: Callable) -> Dict[str, Any]:
    """
    Extract OpenAI function calling schema from a decorated tool.

    Uses type hints (especially Annotated with pydantic.Field) to generate
    a JSON Schema compatible with OpenAI's function calling format.

    Args:
        func: A tool function decorated with @register_tool and @ai_function

    Returns:
        Dict in OpenAI function calling format:
        {
            "name": "tool_name",
            "description": "Tool description",
            "parameters": {
                "type": "object",
                "properties": {...},
                "required": [...]
            }
        }
    """
    # Get tool name
    tool_name = getattr(func, "_tool_name", func.__name__)

    # Get description from docstring
    description = inspect.getdoc(func) or ""

    # Get type hints
    try:
        hints = get_type_hints(func, include_extras=True)
    except Exception:
        hints = {}

    # Get signature for default values
    sig = inspect.signature(func)

    # Build parameters schema
    properties = {}
    required = []

    for param_name, param in sig.parameters.items():
        # Skip special parameters
        if param_name in ("self", "cls", "return"):
            continue

        # Get type annotation
        annotation = hints.get(param_name, param.annotation)
        if annotation == inspect.Parameter.empty:
            annotation = str  # Default to string

        # Extract field info
        field_info = _extract_field_info(annotation)

        # Check if required (no default value)
        if param.default == inspect.Parameter.empty:
            required.append(param_name)
        elif "default" not in field_info and param.default is not None:
            field_info["default"] = param.default

        properties[param_name] = field_info

    # Build full schema
    schema = {
        "name": tool_name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": properties,
        }
    }

    if required:
        schema["parameters"]["required"] = required

    return schema


def get_all_tool_schemas() -> List[Dict[str, Any]]:
    """
    Get OpenAI function calling schemas for all registered tools.

    Returns:
        List of tool schemas in OpenAI format
    """
    schemas = []
    for tool_name, func in _registered_tools.items():
        try:
            schema = extract_tool_schema(func)
            schemas.append(schema)
        except Exception as e:
            logger.warning(
                "Failed to extract schema for tool",
                tool_name=tool_name,
                error=str(e)
            )
    return schemas


def get_tool_schema(tool_name: str) -> Optional[Dict[str, Any]]:
    """
    Get OpenAI function calling schema for a specific tool.

    Args:
        tool_name: Name of the registered tool

    Returns:
        Tool schema or None if not found
    """
    func = _registered_tools.get(tool_name)
    if func:
        try:
            return extract_tool_schema(func)
        except Exception as e:
            logger.warning(
                "Failed to extract schema for tool",
                tool_name=tool_name,
                error=str(e)
            )
    return None


def validate_tool_schema(func: Callable) -> List[str]:
    """
    Validate that a tool function has proper schema annotations.

    Checks for:
    - Type hints on all parameters
    - Descriptions on parameters (via Annotated/Field)
    - Docstring present
    - Return type annotation

    Args:
        func: The tool function to validate

    Returns:
        List of validation issues (empty if valid)
    """
    issues = []
    tool_name = getattr(func, "_tool_name", func.__name__)

    # Check docstring
    if not inspect.getdoc(func):
        issues.append(f"{tool_name}: Missing docstring (tool description)")

    # Get signature and hints
    sig = inspect.signature(func)
    try:
        hints = get_type_hints(func, include_extras=True)
    except Exception as e:
        issues.append(f"{tool_name}: Could not get type hints: {e}")
        return issues

    # Check return annotation
    if "return" not in hints or hints["return"] == inspect.Parameter.empty:
        issues.append(f"{tool_name}: Missing return type annotation")

    # Check each parameter
    for param_name, param in sig.parameters.items():
        if param_name in ("self", "cls"):
            continue

        # Check type annotation
        annotation = hints.get(param_name, param.annotation)
        if annotation == inspect.Parameter.empty:
            issues.append(f"{tool_name}.{param_name}: Missing type annotation")
            continue

        # Check for description (via Annotated/Field)
        origin = get_origin(annotation)
        if origin is Annotated:
            args = get_args(annotation)
            has_description = any(
                hasattr(arg, "description") and arg.description
                for arg in args[1:]
            )
            if not has_description:
                issues.append(
                    f"{tool_name}.{param_name}: Missing description "
                    "(use Annotated[type, Field(description='...')])"
                )
        else:
            issues.append(
                f"{tool_name}.{param_name}: Consider using Annotated with "
                "Field for richer parameter metadata"
            )

    return issues


def validate_all_tools() -> Dict[str, List[str]]:
    """
    Validate all registered tools for proper schema annotations.

    Returns:
        Dict mapping tool names to lists of validation issues
    """
    results = {}
    for tool_name, func in _registered_tools.items():
        issues = validate_tool_schema(func)
        if issues:
            results[tool_name] = issues
    return results

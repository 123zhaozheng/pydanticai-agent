from typing import Optional
import logfire

try:
    from pydantic_ai.toolsets.fastmcp import FastMCPToolset
    from pydantic_deep.mcp_config import load_mcp_config_from_db
except ImportError:
    FastMCPToolset = None
    load_mcp_config_from_db = None


def create_mcp_toolset() -> Optional["FastMCPToolset"]:
    """Create a new MCP Toolset instance (per-request creation).
    
    This creates a fresh connection each time to avoid stale connection issues.
    The configuration is cached in mcp_config.py, so database queries are minimized.
    
    Returns:
        New FastMCPToolset instance or None if no MCP servers configured.
    """
    if FastMCPToolset is None:
        logfire.warn("FastMCPToolset not available")
        return None

    try:
        mcp_config = load_mcp_config_from_db()
        if mcp_config and mcp_config.get('mcpServers'):
            toolset = FastMCPToolset(mcp_config, id="deep-mcp")
            logfire.info("Created MCP toolset", server_count=len(mcp_config['mcpServers']))
            return toolset
        else:
            logfire.debug("No active MCP servers")
            return None
    except Exception as e:
        logfire.error("Failed to create MCP toolset", error=str(e))
        return None


# Keep for backward compatibility - now creates new instance each time
def get_mcp_toolset() -> Optional["FastMCPToolset"]:
    """Get MCP Toolset (backward compatible, now creates new instance).
    
    DEPRECATED: Use create_mcp_toolset() for clarity.
    """
    return create_mcp_toolset()


def reload_mcp_toolset():
    """Reload MCP configuration cache.
    
    Call this after creating/updating/deleting MCP servers to invalidate the config cache.
    The next create_mcp_toolset() call will use the updated configuration.
    """
    from pydantic_deep.mcp_config import invalidate_config_cache
    invalidate_config_cache()
    logfire.info("MCP config cache invalidated, next request will use fresh config")



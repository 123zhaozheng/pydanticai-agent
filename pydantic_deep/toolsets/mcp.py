from typing import Optional
import logging

try:
    from pydantic_ai.toolsets.fastmcp import FastMCPToolset
    from pydantic_deep.mcp_config import load_mcp_config_from_db
except ImportError:
    FastMCPToolset = None
    load_mcp_config_from_db = None

logger = logging.getLogger(__name__)


def create_mcp_toolset() -> Optional["FastMCPToolset"]:
    """Create a new MCP Toolset instance (per-request creation).
    
    This creates a fresh connection each time to avoid stale connection issues.
    The configuration is cached in mcp_config.py, so database queries are minimized.
    
    Returns:
        New FastMCPToolset instance or None if no MCP servers configured.
    """
    if FastMCPToolset is None:
        logger.warning("⚠️  FastMCPToolset not available")
        return None

    try:
        mcp_config = load_mcp_config_from_db()
        if mcp_config and mcp_config.get('mcpServers'):
            toolset = FastMCPToolset(mcp_config, id="deep-mcp")
            logger.info(f"✅ Created MCP toolset with {len(mcp_config['mcpServers'])} servers")
            return toolset
        else:
            logger.debug("ℹ️  No active MCP servers")
            return None
    except Exception as e:
        logger.error(f"❌ Failed to create MCP toolset: {e}")
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
    logger.info("🔄 MCP config cache invalidated, next request will use fresh config")


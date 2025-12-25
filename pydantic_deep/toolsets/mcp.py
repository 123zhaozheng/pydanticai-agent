from typing import Optional
import logging

try:
    from pydantic_ai.toolsets.fastmcp import FastMCPToolset
    from pydantic_deep.mcp_config import load_mcp_config_from_db
except ImportError:
    FastMCPToolset = None
    load_mcp_config_from_db = None

logger = logging.getLogger(__name__)

# ========== Global MCP Toolset Singleton ==========
_mcp_toolset: Optional["FastMCPToolset"] = None

def get_mcp_toolset() -> Optional["FastMCPToolset"]:
    """Get global MCP Toolset instance (for agent.py)"""
    return _mcp_toolset

def reload_mcp_toolset():
    """Reload MCP Toolset (called after creating/updating/deleting MCP servers)"""
    global _mcp_toolset
    
    if FastMCPToolset is None:
        logger.warning("⚠️  FastMCPToolset not available")
        _mcp_toolset = None
        return

    try:
        mcp_config = load_mcp_config_from_db()
        if mcp_config and mcp_config.get('mcpServers'):
            _mcp_toolset = FastMCPToolset(mcp_config, id="deep-mcp")
            print(f"🔄 Loaded {len(mcp_config['mcpServers'])} MCP servers")
        else:
            _mcp_toolset = None
            print("ℹ️  No active MCP servers")
    except Exception as e:
        print(f"❌ Failed to load MCP toolset: {e}")
        _mcp_toolset = None

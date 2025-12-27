"""MCP Configuration loader for FastMCPToolset."""

from typing import Dict, Any
import hashlib
import json

# Cache to avoid unnecessary database queries
_config_cache: Dict[str, Any] = {}
_config_hash: str | None = None


def load_mcp_config_from_db(force_refresh: bool = False) -> Dict[str, Any]:
    """
    Load MCP configuration from database for FastMCPToolset.

    Args:
        force_refresh: If True, bypass cache and reload from database.

    Returns:
        MCP config dict in FastMCPToolset format:
        {
            'mcpServers': {
                'tool_name': {
                    'command': 'npx',
                    'args': ['-y', '@playwright/mcp-server'],
                    'env': {'API_KEY': 'xxx'}  # optional
                }
            }
        }
    """
    global _config_cache, _config_hash

    from src.database import get_db
    from src.models.tools_skills import McpServer, TransportType

    # Return cached config if available and not forcing refresh
    if not force_refresh and _config_cache:
        return _config_cache

    db_gen = get_db()
    db_session = next(db_gen)
    
    try:
        # Query all active MCP servers
        servers = db_session.query(McpServer).filter(McpServer.is_active == True).all()
        
        mcp_servers = {}
        for server in servers:
            if server.transport_type == TransportType.STDIO:
                # Use explicit command + args
                if server.command:
                    server_config = {
                        'command': server.command,
                        'args': server.args or [],
                    }
                    
                    # Add env vars if present
                    if server.env:
                        server_config['env'] = server.env
                    
                    mcp_servers[server.name] = server_config
            
            elif server.transport_type == TransportType.HTTP:
                if server.url:
                    mcp_servers[server.name] = {
                        'url': server.url,
                        'transport': 'http'
                    }
            
            elif server.transport_type == TransportType.SSE:
                if server.url:
                    mcp_servers[server.name] = {
                        'url': server.url,
                        'transport': 'sse'
                    }

        # Build config
        new_config = {'mcpServers': mcp_servers} if mcp_servers else {}

        # Calculate config hash to detect changes
        config_str = json.dumps(new_config, sort_keys=True)
        new_hash = hashlib.md5(config_str.encode()).hexdigest()

        # Only update cache if config changed
        if new_hash != _config_hash:
            _config_cache = new_config
            _config_hash = new_hash
            import logfire
            logfire.info(
                "MCP config updated", hash=new_hash[:8], server_count=len(mcp_servers)
            )

        return _config_cache

    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass


def invalidate_config_cache():
    """Invalidate the config cache. Call this after creating/updating/deleting MCP servers."""
    global _config_cache, _config_hash
    _config_cache = {}
    _config_hash = None
    import logfire
    logfire.debug("MCP config cache invalidated")

"""MCP Configuration loader for FastMCPToolset."""

from typing import Dict, Any


def load_mcp_config_from_db() -> Dict[str, Any]:
    """
    Load MCP configuration from database for FastMCPToolset.
    
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
    from src.database import get_db
    from src.models.tools_skills import McpServer, TransportType
    
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
        
        return {'mcpServers': mcp_servers} if mcp_servers else {}
    
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass

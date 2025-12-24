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
    from src.models.tools_skills import McpTool, TransportType
    
    db_gen = get_db()
    db_session = next(db_gen)
    
    try:
        # Query all active MCP tools
        tools = db_session.query(McpTool).filter(McpTool.is_active == True).all()
        
        mcp_servers = {}
        for tool in tools:
            if tool.transport_type == TransportType.STDIO:
                # Parse command into program + args
                parts = tool.command.split() if tool.command else []
                if parts:
                    server_config = {
                        'command': parts[0],
                        'args': parts[1:] if len(parts) > 1 else [],
                    }
                    
                    # Add env vars if present in tool_metadata
                    if tool.tool_metadata and 'env' in tool.tool_metadata:
                        server_config['env'] = tool.tool_metadata['env']
                    
                    mcp_servers[tool.name] = server_config
            
            elif tool.transport_type == TransportType.HTTP:
                if tool.url:
                    mcp_servers[tool.name] = {
                        'url': tool.url,
                        'transport': 'http'
                    }
            
            elif tool.transport_type == TransportType.SSE:
                if tool.url:
                    mcp_servers[tool.name] = {
                        'url': tool.url,
                        'transport': 'sse'
                    }
        
        return {'mcpServers': mcp_servers} if mcp_servers else {}
    
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass

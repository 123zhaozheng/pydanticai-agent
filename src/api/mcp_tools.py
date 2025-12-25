"""API endpoints for MCP Server management."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session
from datetime import datetime

from src.database import get_db
from src.models.tools_skills import McpServer, TransportType
from src.services.mcp_service import MCPServerService
from pydantic_deep.toolsets.mcp import reload_mcp_toolset

router = APIRouter(prefix="/api/mcp-servers", tags=["mcp-servers"])


# ===== Request/Response Models =====

class MCPServerCreate(BaseModel):
    """Request model for creating an MCP server."""
    name: str = Field(..., min_length=1, max_length=100, description="Unique server identifier")
    description: str | None = Field(None, description="Server description")
    transport_type: TransportType
    url: str | None = Field(None, max_length=500, description="URL for HTTP/SSE transport")
    command: str | None = Field(None, description="Command for STDIO transport")
    args: list[str] | None = Field(None, description="Arguments for STDIO transport")
    env: dict[str, str] | None = Field(None, description="Environment variables for STDIO transport")
    server_metadata: dict | None = None
    timeout_seconds: int = Field(120, ge=1, le=600)
    is_active: bool = True


class MCPServerUpdate(BaseModel):
    """Request model for updating an MCP server."""
    description: str | None = None
    transport_type: TransportType | None = None
    url: str | None = None
    command: str | None = None
    args: list[str] | None = None
    env: dict[str, str] | None = None
    server_metadata: dict | None = None
    timeout_seconds: int | None = Field(None, ge=1, le=600)
    is_active: bool | None = None


class MCPServerResponse(BaseModel):
    """Response model for an MCP server."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    transport_type: TransportType
    url: str | None
    command: str | None
    args: list[str] | None
    env: dict[str, str] | None
    server_metadata: dict | None
    is_active: bool
    is_builtin: bool
    timeout_seconds: int
    created_at: datetime
    updated_at: datetime


class ConnectionTestResponse(BaseModel):
    """Response model for connection test."""
    success: bool
    message: str
    error: str | None


# ===== Endpoints =====

@router.get("", response_model=list[MCPServerResponse])
async def list_mcp_servers(
    user_id: int = 1,  # TODO: Get from JWT token
    include_inactive: bool = Query(False, description="Include inactive servers"),
    transport_type: TransportType | None = Query(None, description="Filter by transport type"),
    db: Session = Depends(get_db)
):
    """
    List all MCP servers.
    """
    service = MCPServerService(db)
    servers = service.list_servers(
        user_id=user_id,
        include_inactive=include_inactive,
        transport_type=transport_type
    )
    return servers


@router.post("", response_model=MCPServerResponse, status_code=201)
async def create_mcp_server(
    body: MCPServerCreate,
    user_id: int = 1,  # TODO: Get from JWT token
    db: Session = Depends(get_db)
):
    """Create a new MCP server."""
    service = MCPServerService(db)
    try:
        server = service.create_server(body.dict(), created_by=user_id)
        # Reload MCP toolset to pick up changes
        reload_mcp_toolset()
        return server
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{server_name}", response_model=MCPServerResponse)
async def get_mcp_server(
    server_name: str,
    db: Session = Depends(get_db)
):
    """Get a single MCP server by name."""
    service = MCPServerService(db)
    server = service.get_server(server_name)
    if not server:
        raise HTTPException(status_code=404, detail=f"Server '{server_name}' not found")
    return server


@router.put("/{server_name}", response_model=MCPServerResponse)
async def update_mcp_server(
    server_name: str,
    body: MCPServerUpdate,
    db: Session = Depends(get_db)
):
    """Update an existing MCP server."""
    service = MCPServerService(db)
    try:
        updates = body.dict(exclude_unset=True)
        server = service.update_server(server_name, updates)
        # Reload MCP toolset to pick up changes
        reload_mcp_toolset()
        return server
    except ValueError as e:
        raise HTTPException(status_code=404 if "not found" in str(e) else 400, detail=str(e))


@router.delete("/{server_name}", status_code=204)
async def delete_mcp_server(
    server_name: str,
    hard_delete: bool = Query(False, description="Permanently delete (vs soft delete)"),
    db: Session = Depends(get_db)
):
    """Delete an MCP server."""
    service = MCPServerService(db)
    try:
        service.delete_server(server_name, soft_delete=not hard_delete)
        # Reload MCP toolset to pick up changes
        reload_mcp_toolset()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{server_name}/test", response_model=ConnectionTestResponse)
async def test_mcp_server(
    server_name: str,
    db: Session = Depends(get_db)
):
    """
    Test MCP server connection.
    """
    service = MCPServerService(db)
    result = service.test_connection(server_name)
    return result

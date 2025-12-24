"""API endpoints for MCP Tool management."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from datetime import datetime

from src.database import get_db
from src.models.tools_skills import McpTool, TransportType
from src.services.mcp_service import MCPToolService

router = APIRouter(prefix="/api/mcp-tools", tags=["mcp-tools"])


# ===== Request/Response Models =====

class MCPToolCreate(BaseModel):
    """Request model for creating an MCP tool."""
    name: str = Field(..., min_length=1, max_length=100, description="Unique tool identifier")
    description: str | None = Field(None, description="Tool description")
    transport_type: TransportType
    url: str | None = Field(None, max_length=500, description="URL for HTTP/SSE transport")
    command: str | None = Field(None, description="Command for STDIO transport")
    input_schema: dict = Field(..., description="JSON Schema for tool parameters")
    metadata: dict | None = None
    timeout_seconds: int = Field(120, ge=1, le=600)
    is_active: bool = True


class MCPToolUpdate(BaseModel):
    """Request model for updating an MCP tool."""
    description: str | None = None
    transport_type: TransportType | None = None
    url: str | None = None
    command: str | None = None
    input_schema: dict | None = None
    metadata: dict | None = None
    timeout_seconds: int | None = Field(None, ge=1, le=600)
    is_active: bool | None = None


class MCPToolResponse(BaseModel):
    """Response model for an MCP tool."""
    id: int
    name: str
    description: str | None
    transport_type: TransportType
    url: str | None
    command: str | None
    input_schema: dict
    tool_metadata: dict | None  # Changed from metadata
    is_active: bool
    is_builtin: bool
    timeout_seconds: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ConnectionTestResponse(BaseModel):
    """Response model for connection test."""
    success: bool
    message: str
    error: str | None


# ===== Endpoints =====

@router.get("", response_model=list[MCPToolResponse])
async def list_mcp_tools(
    user_id: int = 1,  # TODO: Get from JWT token
    include_inactive: bool = Query(False, description="Include inactive tools"),
    transport_type: TransportType | None = Query(None, description="Filter by transport type"),
    db: Session = Depends(get_db)
):
    """
    List all MCP tools.
    
    **Returns:** List of MCP tools ordered by name.
    """
    service = MCPToolService(db)
    tools = service.list_tools(
        user_id=user_id,
        include_inactive=include_inactive,
        transport_type=transport_type
    )
    return tools


@router.post("", response_model=MCPToolResponse, status_code=201)
async def create_mcp_tool(
    body: MCPToolCreate,
    user_id: int = 1,  # TODO: Get from JWT token
    db: Session = Depends(get_db)
):
    """Create a new MCP tool."""
    service = MCPToolService(db)
    try:
        tool = service.create_tool(body.dict(), created_by=user_id)
        return tool
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{tool_name}", response_model=MCPToolResponse)
async def get_mcp_tool(
    tool_name: str,
    db: Session = Depends(get_db)
):
    """Get a single MCP tool by name."""
    service = MCPToolService(db)
    tool = service.get_tool(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    return tool


@router.put("/{tool_name}", response_model=MCPToolResponse)
async def update_mcp_tool(
    tool_name: str,
    body: MCPToolUpdate,
    db: Session = Depends(get_db)
):
    """Update an existing MCP tool."""
    service = MCPToolService(db)
    try:
        updates = body.dict(exclude_unset=True)
        tool = service.update_tool(tool_name, updates)
        return tool
    except ValueError as e:
        raise HTTPException(status_code=404 if "not found" in str(e) else 400, detail=str(e))


@router.delete("/{tool_name}", status_code=204)
async def delete_mcp_tool(
    tool_name: str,
    hard_delete: bool = Query(False, description="Permanently delete (vs soft delete)"),
    db: Session = Depends(get_db)
):
    """Delete an MCP tool."""
    service = MCPToolService(db)
    try:
        service.delete_tool(tool_name, soft_delete=not hard_delete)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{tool_name}/test", response_model=ConnectionTestResponse)
async def test_mcp_tool(
    tool_name: str,
    db: Session = Depends(get_db)
):
    """
    Test MCP tool connection.
    
    **Returns:** Connection test results.
    """
    service = MCPToolService(db)
    result = service.test_connection(tool_name)
    return result

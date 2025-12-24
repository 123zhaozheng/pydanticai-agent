"""MCP Tool Service for managing MCP tool configurations."""

from sqlalchemy.orm import Session
from sqlalchemy import and_

from src.models.tools_skills import McpTool, TransportType, RoleToolPermission


class MCPToolService:
    """Service for MCP Tool CRUD operations and management."""
    
    def __init__(self, db_session: Session):
        self.session = db_session
    
    def list_tools(
        self,
        user_id: int | None = None,
        include_inactive: bool = False,
        transport_type: TransportType | None = None
    ) -> list[McpTool]:
        """
        List MCP tools.
        
        Args:
            user_id: Filter by user permissions (None = all tools)
            include_inactive: Include deactivated tools
            transport_type: Filter by transport type
        
        Returns:
            List of McpTool records
        """
        query = self.session.query(McpTool)
        
        # Filter by active status
        if not include_inactive:
            query = query.filter(McpTool.is_active == True)
        
        # Filter by transport type
        if transport_type:
            query = query.filter(McpTool.transport_type == transport_type)
        
        # Filter by user permissions
        if user_id:
            # Get permitted tool IDs for user
            from pydantic_deep.tool_filter import get_user_tool_permissions
            try:
                permitted_names = get_user_tool_permissions(user_id, None)
                if permitted_names:
                    query = query.filter(McpTool.name.in_(permitted_names))
                else:
                    return []  # No permissions
            except Exception:
                pass  # Fallback to all tools
        
        return query.order_by(McpTool.name).all()
    
    def get_tool(self, tool_name: str) -> McpTool | None:
        """Get single MCP tool by name."""
        return self.session.query(McpTool).filter(McpTool.name == tool_name).first()
    
    def create_tool(self, tool_data: dict, created_by: int | None = None) -> McpTool:
        """
        Create a new MCP tool.
        
        Args:
            tool_data: Tool configuration dict
            created_by: User ID creating the tool
        
        Returns:
            Created McpTool record
        
        Raises:
            ValueError: If tool name already exists or validation fails
        """
        # Validate name uniqueness
        existing = self.session.query(McpTool).filter(McpTool.name == tool_data.get("name")).first()
        if existing:
            raise ValueError(f"Tool '{tool_data['name']}' already exists")
        
        # Validate transport-specific fields
        transport_type = tool_data.get("transport_type")
        if transport_type == TransportType.STDIO:
            if not tool_data.get("command"):
                raise ValueError("STDIO tools require 'command' field")
        elif transport_type in (TransportType.HTTP, TransportType.SSE):
            if not tool_data.get("url"):
                raise ValueError(f"{transport_type} tools require 'url' field")
        
        # Validate input_schema
        if not tool_data.get("input_schema"):
            raise ValueError("Tool must have 'input_schema' (JSON Schema)")
        
        # Create tool
        tool = McpTool(
            name=tool_data["name"],
            description=tool_data.get("description"),
            transport_type=transport_type,
            url=tool_data.get("url"),
            command=tool_data.get("command"),
            input_schema=tool_data["input_schema"],
            tool_metadata=tool_data.get("metadata"),  # API still uses 'metadata' in requests
            timeout_seconds=tool_data.get("timeout_seconds", 120),
            is_active=tool_data.get("is_active", True),
            is_builtin=tool_data.get("is_builtin", False),
            created_by=created_by
        )
        
        self.session.add(tool)
        self.session.commit()
        self.session.refresh(tool)
        
        # Clear MCP manager cache
        from pydantic_deep.mcp_manager import mcp_tool_manager
        mcp_tool_manager.clear_cache()
        
        return tool
    
    def update_tool(self, tool_name: str, updates: dict) -> McpTool:
        """
        Update an existing MCP tool.
        
        Args:
            tool_name: Tool name to update
            updates: Fields to update
        
        Returns:
            Updated McpTool record
        
        Raises:
            ValueError: If tool not found or validation fails
        """
        tool = self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool '{tool_name}' not found")
        
        # Update fields
        for key, value in updates.items():
            if key == "name":
                # Check name uniqueness
                if value != tool_name:
                    existing = self.session.query(McpTool).filter(McpTool.name == value).first()
                    if existing:
                        raise ValueError(f"Tool name '{value}' already exists")
            
            if hasattr(tool, key):
                setattr(tool, key, value)
        
        self.session.commit()
        self.session.refresh(tool)
        
        # Clear cache
        from pydantic_deep.mcp_manager import mcp_tool_manager
        mcp_tool_manager.clear_cache(tool_name)
        
        return tool
    
    def delete_tool(self, tool_name: str, soft_delete: bool = True) -> bool:
        """
        Delete an MCP tool.
        
        Args:
            tool_name: Tool name to delete
            soft_delete: If True, set is_active=False; if False, hard delete
        
        Returns:
            True if deleted successfully
        
        Raises:
            ValueError: If tool not found
        """
        tool = self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool '{tool_name}' not found")
        
        if soft_delete:
            tool.is_active = False
            self.session.commit()
        else:
            self.session.delete(tool)
            self.session.commit()
        
        # Clear cache
        from pydantic_deep.mcp_manager import mcp_tool_manager
        mcp_tool_manager.clear_cache(tool_name)
        
        return True
    
    def test_connection(self, tool_name: str) -> dict:
        """
        Test MCP tool connection.
        
        Args:
            tool_name: Tool name to test
        
        Returns:
            Dict with test results: {"success": bool, "message": str, "error": str | None}
        """
        tool = self.get_tool(tool_name)
        if not tool:
            return {
                "success": False,
                "message": f"Tool '{tool_name}' not found",
                "error": "NOT_FOUND"
            }
        
        if not tool.is_active:
            return {
                "success": False,
                "message": f"Tool '{tool_name}' is inactive",
                "error": "INACTIVE"
            }
        
        try:
            # Attempt to load the tool
            from pydantic_deep.mcp_manager import mcp_tool_manager
            mcp_tool = mcp_tool_manager.load_tool(tool)
            
            # TODO: Add actual connection test (ping MCP server)
            # For now, successful loading indicates basic validity
            
            return {
                "success": True,
                "message": f"Tool '{tool_name}' loaded successfully",
                "error": None
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to load tool '{tool_name}'",
                "error": str(e)
            }

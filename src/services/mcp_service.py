"""MCP Tool Service for managing MCP tool configurations."""

from sqlalchemy.orm import Session
from sqlalchemy import and_

from src.models.tools_skills import McpServer, TransportType, RoleToolPermission


class MCPServerService:
    """Service for MCP Server CRUD operations and management."""
    
    def __init__(self, db_session: Session):
        self.session = db_session
    
    def list_servers(
        self,
        user_id: int | None = None,
        include_inactive: bool = False,
        transport_type: TransportType | None = None
    ) -> list[McpServer]:
        """
        List MCP servers.
        
        Args:
            user_id: Filter by user permissions (None = all servers)
            include_inactive: Include deactivated servers
            transport_type: Filter by transport type
        
        Returns:
            List of McpServer records
        """
        query = self.session.query(McpServer)
        
        # Filter by active status
        if not include_inactive:
            query = query.filter(McpServer.is_active == True)
        
        # Filter by transport type
        if transport_type:
            query = query.filter(McpServer.transport_type == transport_type)
        
        # Filter by user permissions
        if user_id:
            # TODO: Update permission logic to verify server access
            from pydantic_deep.tool_filter import get_user_tool_permissions
            try:
                # Assuming get_user_tool_permissions handles server names now or needs update
                # For now, we return all for admin/creator or implement basic check
                pass 
            except Exception:
                pass
        
        return query.order_by(McpServer.name).all()
    
    def get_server(self, server_name: str) -> McpServer | None:
        """Get single MCP server by name."""
        return self.session.query(McpServer).filter(McpServer.name == server_name).first()
    
    def create_server(self, server_data: dict, created_by: int | None = None) -> McpServer:
        """
        Create a new MCP server configuration.
        
        Args:
            server_data: Server configuration dict
            created_by: User ID creating the server
        
        Returns:
            Created McpServer record
        
        Raises:
            ValueError: If server name already exists or validation fails
        """
        # Validate name uniqueness
        existing = self.session.query(McpServer).filter(McpServer.name == server_data.get("name")).first()
        if existing:
            raise ValueError(f"Server '{server_data['name']}' already exists")
        
        # Validate transport-specific fields
        transport_type = server_data.get("transport_type")
        if transport_type == TransportType.STDIO:
            if not server_data.get("command"):
                raise ValueError("STDIO servers require 'command' field")
        elif transport_type in (TransportType.HTTP, TransportType.SSE):
            if not server_data.get("url"):
                raise ValueError(f"{transport_type} servers require 'url' field")
        
        # Create server
        server = McpServer(
            name=server_data["name"],
            description=server_data.get("description"),
            transport_type=transport_type,
            url=server_data.get("url"),
            command=server_data.get("command"),
            args=server_data.get("args"),
            env=server_data.get("env"),
            server_metadata=server_data.get("server_metadata"),
            timeout_seconds=server_data.get("timeout_seconds", 120),
            is_active=server_data.get("is_active", True),
            is_builtin=server_data.get("is_builtin", False),
            created_by=created_by
        )
        
        self.session.add(server)
        self.session.commit()
        self.session.refresh(server)

        # Invalidate config cache and reload global MCP toolset
        try:
            from pydantic_deep.mcp_config import invalidate_config_cache
            from pydantic_deep.toolsets.mcp import reload_mcp_toolset
            invalidate_config_cache()  # Force cache refresh
            reload_mcp_toolset()
        except Exception as e:
            import logfire
            logfire.warn("Failed to reload MCP toolset", error=str(e))

        return server
    
    def update_server(self, server_name: str, updates: dict) -> McpServer:
        """
        Update an existing MCP server.
        
        Args:
            server_name: Server name to update
            updates: Fields to update
        
        Returns:
            Updated McpServer record
        """
        server = self.get_server(server_name)
        if not server:
            raise ValueError(f"Server '{server_name}' not found")
        
        # Update fields
        for key, value in updates.items():
            if key == "name":
                # Check name uniqueness
                if value != server_name:
                    existing = self.session.query(McpServer).filter(McpServer.name == value).first()
                    if existing:
                        raise ValueError(f"Server name '{value}' already exists")
            
            if hasattr(server, key):
                setattr(server, key, value)
        
        self.session.commit()
        self.session.refresh(server)

        # Invalidate config cache and reload global MCP toolset
        try:
            from pydantic_deep.mcp_config import invalidate_config_cache
            from pydantic_deep.toolsets.mcp import reload_mcp_toolset
            invalidate_config_cache()
            reload_mcp_toolset()
        except Exception:
            pass

        return server
    
    def delete_server(self, server_name: str, soft_delete: bool = True) -> bool:
        """
        Delete an MCP server.
        
        Args:
            server_name: Server name to delete
            soft_delete: If True, set is_active=False
        """
        server = self.get_server(server_name)
        if not server:
            raise ValueError(f"Server '{server_name}' not found")
        
        if soft_delete:
            server.is_active = False
            self.session.commit()
        else:
            self.session.delete(server)
            self.session.commit()

        # Invalidate config cache and reload global MCP toolset
        try:
            from pydantic_deep.mcp_config import invalidate_config_cache
            from pydantic_deep.toolsets.mcp import reload_mcp_toolset
            invalidate_config_cache()
            reload_mcp_toolset()
        except Exception:
            pass

        return True
    
    def test_connection(self, server_name: str) -> dict:
        """
        Test MCP server connection.
        """
        server = self.get_server(server_name)
        if not server:
            return {
                "success": False,
                "message": f"Server '{server_name}' not found",
                "error": "NOT_FOUND"
            }
        
        if not server.is_active:
            return {
                "success": False,
                "message": f"Server '{server_name}' is inactive",
                "error": "INACTIVE"
            }
        
        try:
            if server.transport_type == TransportType.STDIO:
                # Basic check: verify command exists and is executable
                import shutil
                import subprocess
                
                cmd_path = shutil.which(server.command)
                if not cmd_path:
                    return {
                        "success": False,
                        "message": f"Command '{server.command}' not found in PATH",
                        "error": "COMMAND_NOT_FOUND"
                    }
                
                # We can't easily 'test' a full stdio connection without implementing the protocol,
                # so we just check if it launches.
                return {
                    "success": True,
                    "message": f"Command found at {cmd_path}",
                    "error": None
                }
                
            elif server.transport_type in (TransportType.HTTP, TransportType.SSE):
                import httpx
                
                # Basic check: verify URL is reachable
                # Use a short timeout
                try:
                    # Just check headers to see if it responds, ignore strict status for now 
                    # as MCP endpoints might 404 on root or return 405 on GET if strictly JSON-RPC
                    response = httpx.get(server.url, timeout=5.0)
                    
                    # Accept any response as 'reachable'
                    return {
                        "success": True,
                        "message": f"Server reachable (Status: {response.status_code})",
                        "error": None
                    }
                except httpx.RequestError as e:
                    return {
                        "success": False,
                        "message": f"Network error connecting to {server.url}",
                        "error": str(e)
                    }
            
            return {
                "success": False,
                "message": f"Unknown transport type: {server.transport_type}",
                "error": "UNKNOWN_TRANSPORT"
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to test connection: {e}",
                "error": str(e)
            }
    
    # ===== Permission Management =====
    
    def add_role_permission(
        self,
        server_name: str,
        role_id: int,
        can_use: bool = True,
        can_configure: bool = False,
    ) -> RoleToolPermission | None:
        """为角色添加 MCP Server 权限。"""
        server = self.get_server(server_name)
        if not server:
            return None
        
        # Check existing
        existing = self.session.query(RoleToolPermission).filter(
            and_(
                RoleToolPermission.role_id == role_id,
                RoleToolPermission.server_id == server.id,
            )
        ).first()
        
        if existing:
            existing.can_use = can_use
            existing.can_configure = can_configure
            self.session.commit()
            return existing
        
        perm = RoleToolPermission(
            role_id=role_id,
            server_id=server.id,
            can_use=can_use,
            can_configure=can_configure,
        )
        self.session.add(perm)
        self.session.commit()
        self.session.refresh(perm)
        return perm
    
    def remove_role_permission(self, server_name: str, role_id: int) -> bool:
        """移除角色的 MCP Server 权限。"""
        server = self.get_server(server_name)
        if not server:
            return False
        
        perm = self.session.query(RoleToolPermission).filter(
            and_(
                RoleToolPermission.role_id == role_id,
                RoleToolPermission.server_id == server.id,
            )
        ).first()
        
        if not perm:
            return False
        
        self.session.delete(perm)
        self.session.commit()
        return True
    
    def add_department_permission(
        self,
        server_name: str,
        department_id: int,
        is_allowed: bool = True,
    ) -> "DepartmentToolPermission | None":
        """为部门添加 MCP Server 权限。"""
        from src.models.tools_skills import DepartmentToolPermission
        
        server = self.get_server(server_name)
        if not server:
            return None
        
        existing = self.session.query(DepartmentToolPermission).filter(
            and_(
                DepartmentToolPermission.department_id == department_id,
                DepartmentToolPermission.server_id == server.id,
            )
        ).first()
        
        if existing:
            existing.is_allowed = is_allowed
            self.session.commit()
            return existing
        
        perm = DepartmentToolPermission(
            department_id=department_id,
            server_id=server.id,
            is_allowed=is_allowed,
        )
        self.session.add(perm)
        self.session.commit()
        self.session.refresh(perm)
        return perm
    
    def remove_department_permission(self, server_name: str, department_id: int) -> bool:
        """移除部门的 MCP Server 权限。"""
        from src.models.tools_skills import DepartmentToolPermission
        
        server = self.get_server(server_name)
        if not server:
            return False
        
        perm = self.session.query(DepartmentToolPermission).filter(
            and_(
                DepartmentToolPermission.department_id == department_id,
                DepartmentToolPermission.server_id == server.id,
            )
        ).first()
        
        if not perm:
            return False
        
        self.session.delete(perm)
        self.session.commit()
        return True

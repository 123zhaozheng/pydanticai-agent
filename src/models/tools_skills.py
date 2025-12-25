"""SQLAlchemy models for MCP tools and skills with permission management."""

from sqlalchemy import Boolean, Column, Integer, String, Text, JSON, Enum, ForeignKey, DateTime, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from src.database import Base


class TransportType(str, enum.Enum):
    """MCP transport protocol types."""
    HTTP = "http"
    SSE = "sse"
    STDIO = "stdio"


class McpServer(Base):
    """MCP Server Registry - Configuration for MCP servers."""
    __tablename__ = "mcp_servers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True, 
                  comment="Server identifier (e.g., 'filesystem-server')")
    description = Column(Text, comment="Human-readable description")
    
    # MCP Protocol Fields
    transport_type = Column(Enum(TransportType), nullable=False, default=TransportType.HTTP,
                           comment="MCP transport protocol")
    url = Column(String(500), comment="Endpoint URL for HTTP/SSE transport")
    command = Column(Text, comment="Command for stdio transport")
    args = Column(JSON, comment="Arguments for stdio transport (list of strings)")
    env = Column(JSON, comment="Environment variables for stdio transport (dict)")
    
    # Configuration
    server_metadata = Column(JSON, comment="Additional server metadata")
    
    # Status & Management
    is_active = Column(Boolean, default=True, comment="Whether server is enabled")
    is_builtin = Column(Boolean, default=False, 
                       comment="Whether server is built-in")
    timeout_seconds = Column(Integer, default=120, comment="Connection/Request timeout")
    
    # Audit Fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
                       comment="User ID who registered the server")
    
    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    role_permissions = relationship("RoleToolPermission", back_populates="server", 
                                   cascade="all, delete-orphan")
    department_permissions = relationship("DepartmentToolPermission", back_populates="server",
                                         cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<McpServer {self.name}>"


class Skill(Base):
    """Skill Package Registry - Path-based skill packages with SKILL.md."""
    __tablename__ = "skills"
    
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True,
                 comment="Skill identifier (e.g., 'code_review')")
    description = Column(Text, comment="Brief description of skill functionality")
    
    # Skill Location
    path = Column(String(500), nullable=False, 
                 comment="Absolute path to skill directory containing SKILL.md")
    
    # Skill Metadata (from SKILL.md frontmatter)
    version = Column(String(50), default="1.0.0")
    author = Column(String(100))
    tags = Column(JSON, comment="Array of tags for categorization")
    
    # Skill Configuration
    resources = Column(JSON, comment="List of resource files in skill directory")
    frontmatter = Column(JSON, comment="Complete YAML frontmatter from SKILL.md")
    
    # Status & Management
    is_active = Column(Boolean, default=True, comment="Whether skill is enabled")
    is_verified = Column(Boolean, default=False, 
                        comment="Whether skill has been verified/reviewed")
    
    # Audit Fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
                       comment="User ID who added the skill")
    
    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    role_permissions = relationship("RoleSkillPermission", back_populates="skill",
                                   cascade="all, delete-orphan")
    department_permissions = relationship("DepartmentSkillPermission", back_populates="skill",
                                         cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Skill {self.name}>"


class RoleToolPermission(Base):
    """Role's MCP Server Permissions - Defines which roles can access which servers."""
    __tablename__ = "role_tool_permissions"
    
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    server_id = Column(Integer, ForeignKey("mcp_servers.id", ondelete="CASCADE"), nullable=False)
    
    # Permission Types
    can_use = Column(Boolean, default=True, comment="Can use tools from this server")
    can_configure = Column(Boolean, default=False, comment="Can modify server config")
    
    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    role = relationship("Role", back_populates="tool_permissions")
    server = relationship("McpServer", back_populates="role_permissions")
    
    # Composite unique constraint
    __table_args__ = (
        {"comment": "Role-Server Permission Mapping"},
    )
    
    def __repr__(self):
        return f"<RoleToolPermission role_id={self.role_id} server_id={self.server_id}>"


class RoleSkillPermission(Base):
    """Role's Skill Permissions - Defines which roles can access which skills."""
    __tablename__ = "role_skill_permissions"
    
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    skill_id = Column(Integer, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False)
    
    # Permission Types
    can_use = Column(Boolean, default=True, comment="Can load and use the skill")
    can_manage = Column(Boolean, default=False, 
                       comment="Can add/remove resources from skill")
    
    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    role = relationship("Role", back_populates="skill_permissions")
    skill = relationship("Skill", back_populates="role_permissions")
    
    __table_args__ = (
        {"comment": "Role-Skill Permission Mapping"},
    )
    
    def __repr__(self):
        return f"<RoleSkillPermission role_id={self.role_id} skill_id={self.skill_id}>"


class DepartmentToolPermission(Base):
    """Department-level Server Access Control - Overrides role permissions within department."""
    __tablename__ = "department_tool_permissions"
    
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="CASCADE"), 
                          nullable=False)
    server_id = Column(Integer, ForeignKey("mcp_servers.id", ondelete="CASCADE"), nullable=False)
    
    is_allowed = Column(Boolean, default=True, 
                       comment="Whether department can access this server")
    
    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    department = relationship("Department", back_populates="tool_permissions")
    server = relationship("McpServer", back_populates="department_permissions")
    
    __table_args__ = (
        {"comment": "Department-level Server Access Control"},
    )
    
    def __repr__(self):
        return f"<DepartmentToolPermission dept_id={self.department_id} server_id={self.server_id}>"


class DepartmentSkillPermission(Base):
    """Department-level Skill Access Control - Overrides role permissions within department."""
    __tablename__ = "department_skill_permissions"
    
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="CASCADE"), 
                          nullable=False)
    skill_id = Column(Integer, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False)
    
    is_allowed = Column(Boolean, default=True,
                       comment="Whether department can access this skill")
    
    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    department = relationship("Department", back_populates="skill_permissions")
    skill = relationship("Skill", back_populates="department_permissions")
    
    __table_args__ = (
        {"comment": "Department-level Skill Access Control"},
    )
    
    def __repr__(self):
        return f"<DepartmentSkillPermission dept_id={self.department_id} skill_id={self.skill_id}>"

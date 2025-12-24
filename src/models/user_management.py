"""SQLAlchemy models for user, role, and department management."""

from datetime import datetime
from sqlalchemy import Boolean, Column, Integer, String, Text, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.database import Base


# Association table for user-role many-to-many relationship
user_role = Table(
    "user_role",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
)


class User(Base):
    """User model representing system users"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255))
    phone = Column(String(32))
    avatar = Column(String(255))
    hashed_password = Column(String(255), nullable=False)
    
    # User status
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    password_reset_required = Column(Boolean, default=False)
    
    # Department relationship
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    # Explicitly specify foreign_keys to resolve ambiguity with Department.manager_id
    department = relationship("Department", back_populates="users", foreign_keys=[department_id])
    
    # Relationships
    roles = relationship("Role", secondary=user_role, back_populates="users")
    
    # Conversations
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<User {self.username}>"


class RoleMenu(Base):
    """Association model for roles and menus with additional fields"""
    __tablename__ = "role_menu"
    
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    menu_id = Column(Integer, ForeignKey("menus.id", ondelete="CASCADE"), primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    role = relationship("Role", back_populates="menu_permissions")
    menu = relationship("Menu", back_populates="role_permissions")


class RoleButton(Base):
    """Association model for roles and buttons with additional fields"""
    __tablename__ = "role_button"
    
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    button_id = Column(Integer, ForeignKey("buttons.id", ondelete="CASCADE"), primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    role = relationship("Role", back_populates="button_permissions")
    button = relationship("Button", back_populates="role_permissions")


class Role(Base):
    """Role model for RBAC system"""
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), unique=True, index=True, nullable=False)
    description = Column(Text)
    is_default = Column(Boolean, default=False)
    
    # Relationships
    users = relationship("User", secondary="user_role", back_populates="roles")
    menu_permissions = relationship("RoleMenu", back_populates="role", cascade="all, delete-orphan")
    button_permissions = relationship("RoleButton", back_populates="role", cascade="all, delete-orphan")
    
    # Tool & Skill permissions (from tools_skills.py)
    tool_permissions = relationship("RoleToolPermission", back_populates="role", 
                                   cascade="all, delete-orphan")
    skill_permissions = relationship("RoleSkillPermission", back_populates="role",
                                    cascade="all, delete-orphan")
    
    # Agent permissions (if exists)
    # agent_permissions = relationship("AgentPermission", back_populates="role", cascade="all, delete-orphan")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Role {self.name}>"


class Department(Base):
    """Department model for organizational structure"""
    __tablename__ = "departments"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), unique=True, index=True, nullable=False)
    description = Column(Text)
    
    # Self-referential relationship for hierarchical structure
    parent_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    parent = relationship("Department", remote_side=[id], backref="children")
    
    # Department manager
    manager_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    manager = relationship("User", foreign_keys=[manager_id], post_update=True)
    
    # Users in this department
    users = relationship("User", back_populates="department", foreign_keys="User.department_id")
    
    # Tool & Skill permissions (from tools_skills.py)
    tool_permissions = relationship("DepartmentToolPermission", back_populates="department",
                                   cascade="all, delete-orphan")
    skill_permissions = relationship("DepartmentSkillPermission", back_populates="department",
                                    cascade="all, delete-orphan")
    
    # Agent permissions (if exists)
    # agent_permissions = relationship("AgentPermission", back_populates="department", cascade="all, delete-orphan")
    
    # Digital humans (if exists)
    # digital_humans = relationship("Agent", back_populates="department", foreign_keys="Agent.department_id")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Department {self.name}>"


class Menu(Base):
    """Menu model for navigation structure"""
    __tablename__ = "menus"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), nullable=False)
    path = Column(String(255))
    icon = Column(String(64))
    order = Column(Integer, default=0)
    
    # Parent menu for hierarchical structure
    parent_id = Column(Integer, ForeignKey("menus.id", ondelete="CASCADE"), nullable=True)
    parent = relationship("Menu", remote_side=[id], backref="children")
    
    # Relationships
    role_permissions = relationship("RoleMenu", back_populates="menu", cascade="all, delete-orphan")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Menu {self.name}>"


class Button(Base):
    """Button model for fine-grained permission control"""
    __tablename__ = "buttons"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), nullable=False)
    permission_key = Column(String(100), unique=True, nullable=False, index=True,
                           comment="Permission key for checking access")
    description = Column(Text)
    
    # Associated menu
    menu_id = Column(Integer, ForeignKey("menus.id", ondelete="CASCADE"), nullable=True)
    menu = relationship("Menu", backref="buttons")
    
    # Relationships
    role_permissions = relationship("RoleButton", back_populates="button", cascade="all, delete-orphan")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Button {self.name}>"

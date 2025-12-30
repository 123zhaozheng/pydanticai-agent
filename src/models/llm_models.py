"""LLM Model Configuration models with permission management."""

from sqlalchemy import Column, Integer, String, Text, Boolean, Float, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

from src.database import Base


class LLMModelConfig(Base):
    """LLM Model Configuration for dynamic model management."""
    
    __tablename__ = "llm_model_configs"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False, index=True, 
                  comment="Unique identifier for the model config")
    display_name = Column(String(200), nullable=False,
                         comment="Human-readable display name")
    
    # Provider Configuration
    provider_type = Column(String(50), nullable=False, index=True,
                          comment="Provider type: openai, anthropic, gemini, custom")
    model_name = Column(String(200), nullable=False,
                       comment="Actual model name used by the provider")
    base_url = Column(String(500), nullable=True,
                     comment="Custom API endpoint URL (for OpenAI-compatible APIs)")
    api_key = Column(Text, nullable=True,
                    comment="API key (should be encrypted in production)")
    
    # Model Parameters
    default_temperature = Column(Float, default=0.7,
                                comment="Default temperature for generation")
    default_max_tokens = Column(Integer, default=2000,
                               comment="Default max tokens limit")
    supports_streaming = Column(Boolean, default=True,
                               comment="Whether the model supports streaming")
    supports_tools = Column(Boolean, default=True,
                           comment="Whether the model supports function calling")
    
    # Extra Configuration (JSON)
    extra_config = Column(JSON, nullable=True,
                         comment="Additional provider-specific configuration")
    
    # Status
    is_active = Column(Boolean, default=True, index=True,
                      comment="Whether this config is active")
    is_default = Column(Boolean, default=False, index=True,
                       comment="Whether this is the default model")
    
    # Metadata
    description = Column(Text, nullable=True,
                        comment="Optional description of the model")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships for permissions
    role_permissions = relationship("RoleModelPermission", back_populates="model",
                                   cascade="all, delete-orphan")
    department_permissions = relationship("DepartmentModelPermission", back_populates="model",
                                         cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<LLMModelConfig(name='{self.name}', provider='{self.provider_type}', model='{self.model_name}')>"


class RoleModelPermission(Base):
    """Role's Model Permissions - Defines which roles can access which models."""
    __tablename__ = "role_model_permissions"
    
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    model_id = Column(Integer, ForeignKey("llm_model_configs.id", ondelete="CASCADE"), nullable=False)
    
    # Permission Types
    can_use = Column(Boolean, default=True, comment="Can use this model for chat")
    can_configure = Column(Boolean, default=False, comment="Can modify model config")
    
    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    role = relationship("Role", back_populates="model_permissions")
    model = relationship("LLMModelConfig", back_populates="role_permissions")
    
    __table_args__ = (
        {"comment": "Role-Model Permission Mapping"},
    )
    
    def __repr__(self):
        return f"<RoleModelPermission role_id={self.role_id} model_id={self.model_id}>"


class DepartmentModelPermission(Base):
    """Department-level Model Access Control - Overrides role permissions within department."""
    __tablename__ = "department_model_permissions"
    
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="CASCADE"), 
                          nullable=False)
    model_id = Column(Integer, ForeignKey("llm_model_configs.id", ondelete="CASCADE"), nullable=False)
    
    is_allowed = Column(Boolean, default=True, 
                       comment="Whether department can access this model")
    
    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    department = relationship("Department", back_populates="model_permissions")
    model = relationship("LLMModelConfig", back_populates="department_permissions")
    
    __table_args__ = (
        {"comment": "Department-level Model Access Control"},
    )
    
    def __repr__(self):
        return f"<DepartmentModelPermission dept_id={self.department_id} model_id={self.model_id}>"


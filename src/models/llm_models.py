"""LLM Model Configuration models."""

from sqlalchemy import Column, Integer, String, Text, Boolean, Float, JSON, DateTime
from datetime import datetime

from src.models.base import Base


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
    
    def __repr__(self):
        return f"<LLMModelConfig(name='{self.name}', provider='{self.provider_type}', model='{self.model_name}')>"

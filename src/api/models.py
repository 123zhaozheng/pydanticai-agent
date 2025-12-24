"""API endpoints for LLM Model Configuration management."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from datetime import datetime

from src.database import get_db
from src.models.llm_models import LLMModelConfig
from src.services.model_manager import model_manager

router = APIRouter(prefix="/api/models", tags=["models"])


# ===== Request/Response Models =====

class ModelConfigCreate(BaseModel):
    """Request model for creating a model config."""
    name: str = Field(..., min_length=1, max_length=100, description="Unique identifier")
    display_name: str = Field(..., min_length=1, max_length=200)
    provider_type: str = Field(..., pattern="^(openai|anthropic|gemini|deepseek|custom)$")
    model_name: str = Field(..., min_length=1, max_length=200)
    base_url: str | None = Field(None, max_length=500, description="Custom API endpoint")
    api_key: str | None = Field(None, description="API key (will be encrypted)")
    default_temperature: float = Field(0.7, ge=0.0, le=2.0)
    default_max_tokens: int = Field(2000, ge=1, le=100000)
    supports_streaming: bool = True
    supports_tools: bool = True
    extra_config: dict | None = None
    is_default: bool = False
    description: str | None = None


class ModelConfigUpdate(BaseModel):
    """Request model for updating a model config."""
    display_name: str | None = None
    provider_type: str | None = Field(None, pattern="^(openai|anthropic|gemini|deepseek|custom)$")
    model_name: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    default_temperature: float | None = Field(None, ge=0.0, le=2.0)
    default_max_tokens: int | None = Field(None, ge=1, le=100000)
    supports_streaming: bool | None = None
    supports_tools: bool | None = None
    extra_config: dict | None = None
    is_active: bool | None = None
    is_default: bool | None = None
    description: str | None = None


class ModelConfigResponse(BaseModel):
    """Response model for a model config."""
    id: int
    name: str
    display_name: str
    provider_type: str
    model_name: str
    base_url: str | None
    # api_key: Excluded for security
    default_temperature: float
    default_max_tokens: int
    supports_streaming: bool
    supports_tools: bool
    extra_config: dict | None
    is_active: bool
    is_default: bool
    description: str | None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ===== Endpoints =====

@router.get("", response_model=list[ModelConfigResponse])
async def list_models(
    include_inactive: bool = Query(False, description="Include inactive models"),
    db: Session = Depends(get_db)
):
    """
    Get all model configurations.
    
    **Returns:** List of model configs ordered by name.
    """
    query = db.query(LLMModelConfig)
    
    if not include_inactive:
        query = query.filter(LLMModelConfig.is_active == True)
    
    models = query.order_by(LLMModelConfig.name).all()
    return models


@router.post("", response_model=ModelConfigResponse, status_code=201)
async def create_model(
    body: ModelConfigCreate,
    db: Session = Depends(get_db)
):
    """Create a new model configuration."""
    
    # Check if name already exists
    existing = db.query(LLMModelConfig).filter(LLMModelConfig.name == body.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Model '{body.name}' already exists")
    
    # If setting as default, unset other defaults
    if body.is_default:
        db.query(LLMModelConfig).filter(LLMModelConfig.is_default == True).update(
            {"is_default": False}
        )
    
    # Create model config
    model_config = LLMModelConfig(**body.dict())
    db.add(model_config)
    db.commit()
    db.refresh(model_config)
    
    return model_config


@router.get("/{model_name}", response_model=ModelConfigResponse)
async def get_model(
    model_name: str,
    db: Session = Depends(get_db)
):
    """Get a single model configuration by name."""
    model_config = db.query(LLMModelConfig).filter(LLMModelConfig.name == model_name).first()
    if not model_config:
        raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")
    return model_config


@router.put("/{model_name}", response_model=ModelConfigResponse)
async def update_model(
    model_name: str,
    body: ModelConfigUpdate,
    db: Session = Depends(get_db)
):
    """Update an existing model configuration."""
    model_config = db.query(LLMModelConfig).filter(LLMModelConfig.name == model_name).first()
    if not model_config:
        raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")
    
    # If setting as default, unset other defaults
    if body.is_default:
        db.query(LLMModelConfig).filter(
            LLMModelConfig.is_default == True,
            LLMModelConfig.name != model_name
        ).update({"is_default": False})
    
    # Update fields
    update_data = body.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(model_config, key, value)
    
    db.commit()
    db.refresh(model_config)
    
    # Clear cache for this model
    model_manager.reload_model(model_name, db)
    
    return model_config


@router.delete("/{model_name}", status_code=204)
async def delete_model(
    model_name: str,
    db: Session = Depends(get_db)
):
    """Delete a model configuration."""
    model_config = db.query(LLMModelConfig).filter(LLMModelConfig.name == model_name).first()
    if not model_config:
        raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")
    
    # Prevent deleting default model
    if model_config.is_default:
        raise HTTPException(
            status_code=400, 
            detail="Cannot delete default model. Set another model as default first."
        )
    
    db.delete(model_config)
    db.commit()
    
    # Clear cache
    if model_name in model_manager._model_cache:
        del model_manager._model_cache[model_name]


@router.post("/{model_name}/set-default", response_model=ModelConfigResponse)
async def set_default_model(
    model_name: str,
    db: Session = Depends(get_db)
):
    """Set a model as the default."""
    model_config = db.query(LLMModelConfig).filter(LLMModelConfig.name == model_name).first()
    if not model_config:
        raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")
    
    # Unset all other defaults
    db.query(LLMModelConfig).filter(LLMModelConfig.is_default == True).update(
        {"is_default": False}
    )
    
    # Set this one as default
    model_config.is_default = True
    db.commit()
    db.refresh(model_config)
    
    return model_config

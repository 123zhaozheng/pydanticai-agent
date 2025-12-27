"""Model Manager for dynamic LLM model configuration and instantiation."""

import os
import logfire
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from src.models.llm_models import LLMModelConfig


class ModelManager:
    """
    Singleton Manager for LLM Model Configuration.
    
    Responsibilities:
    1. Load model configs from database
    2. Cache model instances (avoid repeated creation)
    3. Provide model instances for Agent creation
    """
    
    _instance: Optional['ModelManager'] = None
    _model_cache: Dict[str, Any] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._model_cache = {}
    
    def get_model(self, model_name: str, db_session: Session) -> Any:
        """
        Get model instance by name (with caching).
        
        Args:
            model_name: Model config name OR model_name from database
            db_session: SQLAlchemy Session
        
        Returns:
            PydanticAI Model instance
        
        Raises:
            ValueError: If model config not found or inactive
        """
        logfire.debug("ModelManager looking for model", model_name=model_name)
        
        # Check cache
        if model_name in self._model_cache:
            logfire.debug("Model found in cache", model_name=model_name)
            return self._model_cache[model_name]
        
        # Load from database - try config name first, then model_name
        config = db_session.query(LLMModelConfig).filter(
            LLMModelConfig.name == model_name,
            LLMModelConfig.is_active == True
        ).first()
        
        logfire.debug("Model query by name", model_name=model_name, found=bool(config))
        
        # If not found by config name, try by model_name
        if not config:
            config = db_session.query(LLMModelConfig).filter(
                LLMModelConfig.model_name == model_name,
                LLMModelConfig.is_active == True
            ).first()
            logfire.debug("Model query by model_name", model_name=model_name, found=bool(config))
        
        if not config:
            raise ValueError(f"Model config '{model_name}' not found or inactive")
        
        # Log config details (mask API key)
        api_key_preview = config.api_key[:8] + "..." if config.api_key else "None"
        logfire.info("Model config found", name=config.name, provider=config.provider_type, model=config.model_name, base_url=config.base_url, api_key=api_key_preview)
        
        # Create instance
        model = self._create_model_instance(config)
        
        # Cache by both names
        self._model_cache[model_name] = model
        self._model_cache[config.name] = model
        
        return model
    
    def _create_model_instance(self, config: LLMModelConfig) -> Any:
        """Create PydanticAI model instance from config."""
        
        if config.provider_type in ('openai', 'custom'):
            return self._create_openai_model(config)
        
        elif config.provider_type == 'anthropic':
            return self._create_anthropic_model(config)
        
        elif config.provider_type == 'gemini':
            return self._create_gemini_model(config)
        
        elif config.provider_type == 'deepseek':
            return self._create_deepseek_model(config)
        
        else:
            raise ValueError(f"Unsupported provider type: {config.provider_type}")
    
    def _create_openai_model(self, config: LLMModelConfig):
        """Create OpenAI or OpenAI-compatible model."""
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider
        
        provider = OpenAIProvider(
            base_url=config.base_url,
            api_key=config.api_key or os.getenv('OPENAI_API_KEY')
        )
        
        return OpenAIChatModel(
            config.model_name,
            provider=provider
        )
    
    def _create_anthropic_model(self, config: LLMModelConfig):
        """Create Anthropic Claude model."""
        from pydantic_ai.models.anthropic import AnthropicModel
        from pydantic_ai.providers.anthropic import AnthropicProvider
        
        provider = AnthropicProvider(
            api_key=config.api_key or os.getenv('ANTHROPIC_API_KEY')
        )
        
        return AnthropicModel(
            config.model_name,
            provider=provider
        )
    
    def _create_gemini_model(self, config: LLMModelConfig):
        """Create Google Gemini model."""
        from pydantic_ai.models.google import GoogleModel
        from pydantic_ai.providers.google import GoogleProvider
        
        provider = GoogleProvider(
            api_key=config.api_key or os.getenv('GOOGLE_API_KEY')
        )
        
        return GoogleModel(
            config.model_name,
            provider=provider
        )
    
    def _create_deepseek_model(self, config: LLMModelConfig):
        """Create DeepSeek model (OpenAI-compatible)."""
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.deepseek import DeepSeekProvider
        
        provider = DeepSeekProvider(
            api_key=config.api_key or os.getenv('DEEPSEEK_API_KEY')
        )
        
        return OpenAIChatModel(
            config.model_name,
            provider=provider
        )
    
    def get_default_model(self, db_session: Session):
        """Get default model instance."""
        config = db_session.query(LLMModelConfig).filter(
            LLMModelConfig.is_default == True,
            LLMModelConfig.is_active == True
        ).first()
        
        if not config:
            raise ValueError("No default model configured")
        
        return self.get_model(config.name, db_session)
    
    def clear_cache(self):
        """Clear all cached models."""
        self._model_cache.clear()
    
    def reload_model(self, model_name: str, db_session: Session):
        """Reload specific model configuration."""
        if model_name in self._model_cache:
            del self._model_cache[model_name]
        return self.get_model(model_name, db_session)


# Global singleton instance
model_manager = ModelManager()

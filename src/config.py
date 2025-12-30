from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    统一的配置管理类 (Unified Configuration Management)
    """
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Project Base Directory
    # Priority: PYDANTIC_DEEP_BASE_DIR env var > calculated from file location
    PYDANTIC_DEEP_BASE_DIR: Optional[Path] = None
    PYDANTIC_DEEP_HOST_DIR: Optional[Path] = None
    
    # JWT Authentication
    JWT_SECRET_KEY: str = "change-me-in-production-use-strong-random-key"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    @property
    def BASE_DIR(self) -> Path:
        """Calculate the project base directory."""
        if self.PYDANTIC_DEEP_BASE_DIR:
            return self.PYDANTIC_DEEP_BASE_DIR
        return Path(__file__).resolve().parent.parent

    @property
    def HOST_DIR(self) -> Path:
        """Host directory path for Docker-outside-of-Docker volume mounting."""
        if self.PYDANTIC_DEEP_HOST_DIR:
            return self.PYDANTIC_DEEP_HOST_DIR
        return self.BASE_DIR

    @property
    def UPLOAD_DIR(self) -> Path:
        """Directory for file uploads."""
        path = self.BASE_DIR / "uploads"
        path.mkdir(exist_ok=True, parents=True)
        return path

    @property
    def SKILLS_DIR(self) -> Path:
        """Directory for skills."""
        path = self.BASE_DIR / "skills"
        path.mkdir(exist_ok=True, parents=True)
        return path
    
    @property
    def INTERMEDIATE_DIR(self) -> Path:
        """Directory for intermediate files (sandbox artifacts)."""
        path = self.BASE_DIR / "intermediate"
        path.mkdir(exist_ok=True, parents=True)
        return path

    @property
    def DATABASE_URL(self) -> str:
        """Database connection URL."""
        return f"sqlite:///{self.BASE_DIR}/app.db"


# Global settings instance
settings = Settings()

# Export for backward compatibility
BASE_DIR = settings.BASE_DIR
UPLOAD_DIR = settings.UPLOAD_DIR
DATABASE_URL = settings.DATABASE_URL

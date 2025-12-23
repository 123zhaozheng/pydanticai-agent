
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from redis import Redis
    from sqlalchemy.orm import Session

class DbClient:
    """Database client wrapper for lazy loading."""
    
    def __init__(self, session_factory: Any = None) -> None:
        self._session_factory = session_factory
        self._session: Session | None = None

    def get_session(self) -> Session:
        """Get a database session, creating it if necessary."""
        if self._session is None:
            if self._session_factory:
                self._session = self._session_factory()
            else:
                # Fallback to importing from src.database if available, 
                # or raise error if no factory provided
                try:
                    from src.database import SessionLocal
                    self._session = SessionLocal()
                except ImportError:
                    raise RuntimeError("No session factory provided and src.database not found")
        return self._session

    def close(self) -> None:
        """Close the session if it exists."""
        if self._session:
            self._session.close()
            self._session = None

class RedisClient:
    """Redis client wrapper for lazy loading."""

    def __init__(self, url: str = "redis://localhost:6379/0") -> None:
        self.url = url
        self._client: Redis | None = None

    @property
    def client(self) -> Redis:
        """Get the Redis client, connecting if necessary."""
        if self._client is None:
            try:
                import redis
                self._client = redis.from_url(self.url or "redis://localhost:6379/0")
            except ImportError:
                raise ImportError("Redis package is required. Install it with: pip install redis")
        return self._client

    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to the underlying Redis client."""
        return getattr(self.client, name)

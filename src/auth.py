"""JWT Authentication and Authorization module.

Provides dependency injection for FastAPI endpoints with role-based access control.
Compatible with external systems that issue simple JWT tokens (sub + exp only).

Usage:
    from src.auth import CurrentUser, get_current_user, require_admin
    
    # User endpoint (any authenticated user)
    @router.get("/items")
    async def list_items(current_user: CurrentUser = Depends(get_current_user)):
        return {"user_id": current_user.id}
    
    # Admin-only endpoint
    @router.post("/items")
    async def create_item(admin: CurrentUser = Depends(require_admin)):
        return {"created_by": admin.id}
"""

from datetime import datetime, timedelta
from typing import Optional, Union, Any

import jwt
import logfire
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.config import settings
from src.database import get_db

logger = logfire

# Bearer token extractor
bearer_scheme = HTTPBearer(auto_error=False)


class TokenPayload(BaseModel):
    """JWT Token payload structure (compatible with external systems)."""
    sub: int | str  # user_id
    exp: datetime
    iat: Optional[datetime] = None
    type: Optional[str] = None  # "refresh" for refresh tokens


class CurrentUser(BaseModel):
    """Current authenticated user (from database)."""
    id: int
    username: Optional[str] = None
    is_admin: bool = False
    is_active: bool = True
    
    @classmethod
    def from_db_user(cls, user) -> "CurrentUser":
        """Create CurrentUser from database User model."""
        return cls(
            id=user.id,
            username=user.username,
            is_admin=user.is_admin,
            is_active=user.is_active,
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db)
) -> CurrentUser:
    """
    Extract and validate current user from JWT token, then query database.
    
    Use this dependency for any endpoint that requires authentication:
    
        @router.get("/my-items")
        async def my_items(current_user: CurrentUser = Depends(get_current_user)):
            return service.get_items(user_id=current_user.id)
    
    Raises:
        HTTPException 401: If token is missing, expired, invalid, or user not found
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    
    try:
        # Log the received token (partially for security)
        token_preview = f"{token[:10]}...{token[-10:]}" if len(token) > 20 else token[:10]
        logger.debug(f"Validating token: {token_preview}")

        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_sub": False}  # sub can be int or str
        )
        logger.debug(f"Decoded payload: {payload}")
        
        token_data = TokenPayload(**payload)
        user_id = int(token_data.sub) if isinstance(token_data.sub, str) else token_data.sub
        logger.debug(f"Validated token for user_id={user_id}")
        
        # Query user from database
        from src.models.user_management import User
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            logger.warning(f"User not found: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            logger.warning(f"User is inactive: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User is inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return CurrentUser.from_db_user(user)
    
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except ValueError as e:
        logger.error(f"Token payload validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected token validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db)
) -> CurrentUser | None:
    """
    Optional authentication - returns None if no token provided.
    
    Use for endpoints that work differently for authenticated vs anonymous users.
    
        @router.get("/public-items")
        async def public_items(current_user: CurrentUser | None = Depends(get_current_user_optional)):
            if current_user:
                return service.get_items(user_id=current_user.id)
            return service.get_public_items()
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


async def require_admin(
    current_user: CurrentUser = Depends(get_current_user)
) -> CurrentUser:
    """
    Require admin role for access.
    
    Use this dependency for admin-only endpoints:
    
        @router.delete("/items/{id}")
        async def delete_item(item_id: int, admin: CurrentUser = Depends(require_admin)):
            return service.delete(item_id)
    
    Raises:
        HTTPException 403: If user is not admin
    """
    if not current_user.is_admin:
        logger.warning(f"Access denied: user {current_user.id} is not admin")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


# ===== Token Creation (for testing or internal use) =====

def create_access_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token (compatible with external system format).
    
    Args:
        subject: Token subject (typically user ID)
        expires_delta: Optional expiration delta, defaults to settings value
        
    Returns:
        JWT token as string
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token.
    
    Args:
        subject: Token subject (typically user ID)
        expires_delta: Optional expiration delta, defaults to settings value
        
    Returns:
        JWT token as string
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_REFRESH_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

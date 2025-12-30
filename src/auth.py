"""JWT Authentication and Authorization module.

Provides dependency injection for FastAPI endpoints with role-based access control.

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

from datetime import datetime
from typing import Optional

import jwt
import logfire
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from src.config import settings

logger = logfire

# Bearer token extractor
bearer_scheme = HTTPBearer(auto_error=False)


class TokenPayload(BaseModel):
    """JWT Token payload structure."""
    sub: int | str  # user_id
    exp: datetime
    iat: Optional[datetime] = None
    role: str = "user"  # "user" | "admin"
    permissions: list[str] = []


class CurrentUser(BaseModel):
    """Current authenticated user (parsed from JWT)."""
    id: int
    role: str = "user"
    is_admin: bool = False
    permissions: list[str] = []
    
    @classmethod
    def from_token(cls, payload: TokenPayload) -> "CurrentUser":
        """Create CurrentUser from token payload."""
        user_id = payload.sub if isinstance(payload.sub, int) else int(payload.sub)
        is_admin = payload.role == "admin"
        return cls(
            id=user_id,
            role=payload.role,
            is_admin=is_admin,
            permissions=payload.permissions,
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)
) -> CurrentUser:
    """
    Extract and validate current user from JWT token.
    
    Use this dependency for any endpoint that requires authentication:
    
        @router.get("/my-items")
        async def my_items(current_user: CurrentUser = Depends(get_current_user)):
            return service.get_items(user_id=current_user.id)
    
    Raises:
        HTTPException 401: If token is missing, expired, or invalid
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
        logger.debug(f"Validated token data: user={token_data.sub}, role={token_data.role}")
        
        return CurrentUser.from_token(token_data)
    
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
    except Exception as e:
        logger.error(f"Unexpected token validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)
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
        return await get_current_user(credentials)
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


def create_access_token(
    user_id: int,
    role: str = "user",
    permissions: list[str] | None = None,
    expires_minutes: int | None = None,
) -> str:
    """
    Create a JWT access token.
    
    Args:
        user_id: User ID to encode in token
        role: User role ("user" or "admin")
        permissions: Optional list of permission strings
        expires_minutes: Token expiry in minutes (uses config default if not specified)
    
    Returns:
        Encoded JWT token string
    """
    from datetime import timedelta
    
    if expires_minutes is None:
        expires_minutes = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    
    payload = {
        "sub": str(user_id),  # RFC 7519 requires sub to be a string
        "role": role,
        "permissions": permissions or [],
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

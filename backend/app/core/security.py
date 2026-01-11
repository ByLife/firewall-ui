"""
Security utilities - Password hashing, JWT tokens, etc.
"""

from datetime import datetime, timedelta
from typing import Optional, Any
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """Decode a JWT access token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


class TokenData:
    """Token data container"""
    def __init__(self, user_id: int, username: str, role: str):
        self.user_id = user_id
        self.username = username
        self.role = role


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Get current user from JWT token"""
    from app.core.database import async_session_maker
    from app.models.user import User
    from sqlalchemy import select
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    
    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise credentials_exception
    
    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise credentials_exception
    
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if user is None:
            raise credentials_exception
        
        if not bool(user.is_active):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled"
            )
        
        return user


async def get_current_admin(current_user = Depends(get_current_user)):
    """Require admin role"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


async def get_current_operator(current_user = Depends(get_current_user)):
    """Require operator or admin role"""
    if current_user.role not in ["admin", "operator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operator access required"
        )
    return current_user


# Permission definitions
PERMISSIONS = {
    "admin": [
        "users:read", "users:write", "users:delete",
        "firewall:read", "firewall:write",
        "routes:read", "routes:write",
        "ports:read", "ports:scan",
        "docker:read", "docker:write",
        "audit:read"
    ],
    "operator": [
        "firewall:read", "firewall:write",
        "routes:read", "routes:write",
        "ports:read", "ports:scan",
        "docker:read"
    ],
    "viewer": [
        "firewall:read",
        "routes:read",
        "ports:read",
        "docker:read"
    ]
}


def has_permission(user_role: str, permission: str) -> bool:
    """Check if a role has a specific permission"""
    role_permissions = PERMISSIONS.get(user_role, [])
    return permission in role_permissions


def require_permission(permission: str):
    """Decorator factory for permission checking"""
    async def permission_checker(current_user = Depends(get_current_user)):
        if not has_permission(current_user.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required"
            )
        return current_user
    return permission_checker

"""
Authentication API Routes
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.security import (
    verify_password, 
    create_access_token, 
    get_current_user,
    get_password_hash
)
from app.core.config import settings
from app.models.user import User
from app.models.audit import AuditLog
from app.schemas import Token, LoginRequest, UserResponse, UserPasswordUpdate

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Login and get access token"""
    # Find user
    result = await db.execute(
        select(User).where(User.username == form_data.username)
    )
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        # Log failed attempt
        audit = AuditLog(
            action="LOGIN_FAILED",
            resource_type="auth",
            description=f"Failed login attempt for user: {form_data.username}",
            ip_address=request.client.host if request.client else None,
            status="failed"
        )
        db.add(audit)
        await db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    
    # Create access token
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "username": user.username,
            "role": user.role
        },
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    # Log successful login
    audit = AuditLog(
        user_id=user.id,
        username=user.username,
        action="LOGIN",
        resource_type="auth",
        description="User logged in successfully",
        ip_address=request.client.host if request.client else None,
        status="success"
    )
    db.add(audit)
    await db.commit()
    
    return Token(access_token=access_token, token_type="bearer")


@router.post("/login/json", response_model=Token)
async def login_json(
    request: Request,
    credentials: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """Login with JSON body"""
    # Find user
    result = await db.execute(
        select(User).where(User.username == credentials.username)
    )
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    
    # Create access token
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "username": user.username,
            "role": user.role
        }
    )
    
    await db.commit()
    
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return current_user


@router.post("/change-password")
async def change_password(
    password_update: UserPasswordUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Change current user's password"""
    if not verify_password(password_update.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Update password
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one()
    user.hashed_password = get_password_hash(password_update.new_password)
    
    await db.commit()
    
    return {"message": "Password updated successfully"}


@router.post("/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Logout (for audit purposes - JWT tokens cannot be invalidated server-side)"""
    audit = AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        action="LOGOUT",
        resource_type="auth",
        description="User logged out",
        ip_address=request.client.host if request.client else None,
        status="success"
    )
    db.add(audit)
    await db.commit()
    
    return {"message": "Logged out successfully"}

"""Audit log API routes."""
from typing import Optional, List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.security import get_current_user
from ..models.user import User
from ..models.audit import AuditLog

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
async def get_audit_logs(
    action: Optional[str] = Query(None, description="Filter by action type"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    resource: Optional[str] = Query(None, description="Filter by resource type"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get audit logs with optional filters."""
    query = select(AuditLog).order_by(AuditLog.created_at.desc())
    
    if action:
        query = query.where(AuditLog.action.ilike(f"%{action}%"))
    
    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    
    if resource:
        query = query.where(AuditLog.resource.ilike(f"%{resource}%"))
    
    if start_date:
        query = query.where(AuditLog.created_at >= start_date)
    
    if end_date:
        query = query.where(AuditLog.created_at <= end_date)
    
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    return [
        {
            "id": log.id,
            "user_id": log.user_id,
            "action": log.action,
            "resource": log.resource,
            "resource_id": log.resource_id,
            "details": log.details,
            "ip_address": log.ip_address,
            "created_at": log.created_at.isoformat() if log.created_at else None
        }
        for log in logs
    ]


@router.get("/actions")
async def get_audit_actions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of unique action types in audit logs."""
    query = select(AuditLog.action).distinct()
    result = await db.execute(query)
    actions = result.scalars().all()
    return list(actions)


@router.get("/resource-types")
async def get_resource_types(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of unique resource types in audit logs."""
    query = select(AuditLog.resource).distinct().where(AuditLog.resource.isnot(None))
    result = await db.execute(query)
    resources = result.scalars().all()
    return list(resources)


@router.get("/summary")
async def get_audit_summary(
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get summary of audit activity for specified days."""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Total count
    total_query = select(func.count(AuditLog.id)).where(
        AuditLog.created_at >= start_date
    )
    total_result = await db.execute(total_query)
    total_count = total_result.scalar() or 0
    
    # Count by action type
    action_query = select(
        AuditLog.action,
        func.count(AuditLog.id).label("count")
    ).where(
        AuditLog.created_at >= start_date
    ).group_by(AuditLog.action)
    
    action_result = await db.execute(action_query)
    actions = action_result.all()
    
    # Count by user
    user_query = select(
        AuditLog.user_id,
        func.count(AuditLog.id).label("count")
    ).where(
        AuditLog.created_at >= start_date
    ).group_by(AuditLog.user_id)
    
    user_result = await db.execute(user_query)
    users = user_result.all()
    
    return {
        "period_days": days,
        "total_events": total_count,
        "by_action": [
            {"action": action, "count": count}
            for action, count in actions
        ],
        "by_user": [
            {"user_id": user_id, "count": count}
            for user_id, count in users
        ]
    }


async def log_audit(
    db: AsyncSession,
    user_id: int,
    action: str,
    resource: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None
):
    """Helper function to create an audit log entry."""
    log = AuditLog(
        user_id=user_id,
        action=action,
        resource=resource,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address
    )
    db.add(log)
    await db.commit()
    return log

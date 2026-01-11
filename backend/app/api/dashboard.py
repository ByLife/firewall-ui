"""
Dashboard and Audit API Routes
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.security import require_permission, get_current_admin
from app.models.user import User
from app.models.audit import AuditLog
from app.connectors import connector_manager, ConnectorStatus
from app.schemas import AuditLogResponse, DashboardStatsResponse

router = APIRouter(tags=["Dashboard"])


@router.get("/dashboard/stats")
async def get_dashboard_stats(
    current_user: User = Depends(require_permission("firewall:read"))
):
    """Get dashboard statistics"""
    stats = {
        "total_firewall_rules": 0,
        "total_routes": 0,
        "listening_ports": 0,
        "docker_containers": 0,
        "active_connections": 0
    }
    
    # Get firewall rules count
    preferred_fw = await connector_manager.get_preferred_firewall()
    if preferred_fw:
        fw_connector = connector_manager.get_connector(preferred_fw)
        rules = await fw_connector.get_rules()
        stats["total_firewall_rules"] = len(rules)
    
    # Get routes count
    network_connector = connector_manager.get_connector("network")
    network_info = await network_connector.check_availability()
    if network_info.status == ConnectorStatus.AVAILABLE:
        routes = await network_connector.get_all_routes()
        stats["total_routes"] = len(routes)
    
    # Get listening ports count
    port_connector = connector_manager.get_connector("portscanner")
    ports = await port_connector.get_listening_ports()
    stats["listening_ports"] = len(ports)
    
    # Get Docker container count
    docker_connector = connector_manager.get_connector("docker")
    docker_info = await docker_connector.check_availability()
    if docker_info.status == ConnectorStatus.AVAILABLE:
        status = await docker_connector.get_status()
        stats["docker_containers"] = status.get("containers_running", 0)
    
    return stats


@router.get("/dashboard/connectors")
async def get_connector_status(
    current_user: User = Depends(require_permission("firewall:read"))
):
    """Get status of all connectors"""
    results = await connector_manager.check_all_availability()
    
    return [
        {
            "name": info.name,
            "type": info.type,
            "status": info.status.value,
            "version": info.version,
            "message": info.message
        }
        for info in results
    ]


@router.get("/dashboard/overview")
async def get_system_overview(
    current_user: User = Depends(require_permission("firewall:read"))
):
    """Get complete system overview"""
    overview = {
        "firewalls": [],
        "network": {},
        "ports": {},
        "docker": {},
        "npm": {}
    }
    
    # Firewall status
    for name, connector in connector_manager.get_firewall_connectors().items():
        info = await connector.check_availability()
        if info.status == ConnectorStatus.AVAILABLE:
            status = await connector.get_status()
            overview["firewalls"].append({
                "name": name,
                "available": True,
                "version": info.version,
                "status": status
            })
        else:
            overview["firewalls"].append({
                "name": name,
                "available": False
            })
    
    # Network status
    network_connector = connector_manager.get_connector("network")
    network_info = await network_connector.check_availability()
    if network_info.status == ConnectorStatus.AVAILABLE:
        overview["network"] = await network_connector.get_status()
        overview["network"]["available"] = True
    else:
        overview["network"]["available"] = False
    
    # Port scanner status
    port_connector = connector_manager.get_connector("portscanner")
    port_info = await port_connector.check_availability()
    if port_info.status == ConnectorStatus.AVAILABLE:
        ports = await port_connector.get_listening_ports()
        overview["ports"] = {
            "available": True,
            "listening_count": len(ports)
        }
    
    # Docker status
    docker_connector = connector_manager.get_connector("docker")
    docker_info = await docker_connector.check_availability()
    if docker_info.status == ConnectorStatus.AVAILABLE:
        overview["docker"] = await docker_connector.get_status()
    else:
        overview["docker"] = {"available": False}
    
    # NPM status
    npm_connector = connector_manager.get_connector("npm")
    npm_info = await npm_connector.check_availability()
    if npm_info.status == ConnectorStatus.AVAILABLE:
        overview["npm"] = await npm_connector.get_status()
    else:
        overview["npm"] = {"available": False}
    
    return overview


# ============ Audit Logs ============

@router.get("/audit", response_model=List[AuditLogResponse])
async def get_audit_logs(
    skip: int = 0,
    limit: int = 100,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    user_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(require_permission("audit:read")),
    db: AsyncSession = Depends(get_db)
):
    """Get audit logs with filtering"""
    query = select(AuditLog)
    
    if action:
        query = query.where(AuditLog.action == action)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    if start_date:
        query = query.where(AuditLog.created_at >= start_date)
    if end_date:
        query = query.where(AuditLog.created_at <= end_date)
    
    query = query.order_by(desc(AuditLog.created_at)).offset(skip).limit(limit)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    return logs


@router.get("/audit/actions")
async def get_audit_actions(
    current_user: User = Depends(require_permission("audit:read")),
    db: AsyncSession = Depends(get_db)
):
    """Get list of unique audit actions"""
    result = await db.execute(
        select(AuditLog.action).distinct()
    )
    actions = [row[0] for row in result.all()]
    return actions


@router.get("/audit/resource-types")
async def get_audit_resource_types(
    current_user: User = Depends(require_permission("audit:read")),
    db: AsyncSession = Depends(get_db)
):
    """Get list of unique resource types"""
    result = await db.execute(
        select(AuditLog.resource_type).distinct()
    )
    types = [row[0] for row in result.all()]
    return types


@router.get("/audit/summary")
async def get_audit_summary(
    days: int = 7,
    current_user: User = Depends(require_permission("audit:read")),
    db: AsyncSession = Depends(get_db)
):
    """Get audit summary for the last N days"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    result = await db.execute(
        select(AuditLog).where(AuditLog.created_at >= start_date)
    )
    logs = result.scalars().all()
    
    summary = {
        "total_actions": len(logs),
        "by_action": {},
        "by_resource_type": {},
        "by_user": {},
        "by_status": {"success": 0, "failed": 0}
    }
    
    for log in logs:
        # By action
        if log.action not in summary["by_action"]:
            summary["by_action"][log.action] = 0
        summary["by_action"][log.action] += 1
        
        # By resource type
        if log.resource_type not in summary["by_resource_type"]:
            summary["by_resource_type"][log.resource_type] = 0
        summary["by_resource_type"][log.resource_type] += 1
        
        # By user
        username = log.username or "anonymous"
        if username not in summary["by_user"]:
            summary["by_user"][username] = 0
        summary["by_user"][username] += 1
        
        # By status
        if log.status == "success":
            summary["by_status"]["success"] += 1
        else:
            summary["by_status"]["failed"] += 1
    
    return summary

"""
Firewall API Routes
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional

from app.core.database import get_db
from app.core.security import require_permission, get_current_user
from app.models.user import User
from app.models.audit import AuditLog
from app.connectors import connector_manager, ConnectorStatus
from app.schemas import (
    UFWRuleCreate, 
    IptablesRuleCreate, 
    FirewalldRuleCreate,
    FirewallRuleResponse,
    FirewallStatusResponse
)

router = APIRouter(prefix="/firewall", tags=["Firewall"])


@router.get("/status")
async def get_firewall_status(
    current_user: User = Depends(require_permission("firewall:read"))
):
    """Get status of all available firewall backends"""
    results = []
    
    for name, connector in connector_manager.get_firewall_connectors().items():
        info = await connector.check_availability()
        
        if info.status == ConnectorStatus.AVAILABLE:
            status_data = await connector.get_status()
            results.append({
                "backend": name,
                "available": True,
                "version": info.version,
                "status": status_data
            })
        else:
            results.append({
                "backend": name,
                "available": False,
                "message": info.message
            })
    
    return results


@router.get("/backends")
async def get_available_backends(
    current_user: User = Depends(require_permission("firewall:read"))
):
    """Get list of available firewall backends"""
    available = await connector_manager.get_available_firewalls()
    preferred = await connector_manager.get_preferred_firewall()
    
    return {
        "available": available,
        "preferred": preferred
    }


# ============ UFW Routes ============

@router.get("/ufw/status")
async def get_ufw_status(
    current_user: User = Depends(require_permission("firewall:read"))
):
    """Get UFW status"""
    connector = connector_manager.get_connector("ufw")
    info = await connector.check_availability()
    
    if info.status != ConnectorStatus.AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"UFW not available: {info.message}"
        )
    
    return await connector.get_status()


@router.get("/ufw/rules")
async def get_ufw_rules(
    current_user: User = Depends(require_permission("firewall:read"))
):
    """Get all UFW rules"""
    connector = connector_manager.get_connector("ufw")
    return await connector.get_rules()


@router.post("/ufw/rules")
async def add_ufw_rule(
    rule: UFWRuleCreate,
    request: Request,
    current_user: User = Depends(require_permission("firewall:write")),
    db: AsyncSession = Depends(get_db)
):
    """Add a new UFW rule"""
    connector = connector_manager.get_connector("ufw")
    
    result = await connector.add_rule(rule.model_dump())
    
    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        action="CREATE",
        resource_type="firewall_rule",
        description=f"Added UFW rule: {rule.action} {rule.port}",
        details=rule.model_dump(),
        ip_address=request.client.host if request.client else None,
        status="success" if result.get("success") else "failed",
        error_message=result.get("error")
    )
    db.add(audit)
    await db.commit()
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to add rule")
        )
    
    return result


@router.delete("/ufw/rules/{rule_id}")
async def delete_ufw_rule(
    rule_id: str,
    request: Request,
    current_user: User = Depends(require_permission("firewall:write")),
    db: AsyncSession = Depends(get_db)
):
    """Delete a UFW rule"""
    connector = connector_manager.get_connector("ufw")
    
    success = await connector.delete_rule(rule_id)
    
    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        action="DELETE",
        resource_type="firewall_rule",
        resource_id=rule_id,
        description=f"Deleted UFW rule #{rule_id}",
        ip_address=request.client.host if request.client else None,
        status="success" if success else "failed"
    )
    db.add(audit)
    await db.commit()
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to delete rule"
        )
    
    return {"message": "Rule deleted successfully"}


@router.post("/ufw/enable")
async def enable_ufw(
    request: Request,
    current_user: User = Depends(require_permission("firewall:write")),
    db: AsyncSession = Depends(get_db)
):
    """Enable UFW"""
    connector = connector_manager.get_connector("ufw")
    success = await connector.enable()
    
    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        action="EXECUTE",
        resource_type="firewall",
        description="Enabled UFW",
        ip_address=request.client.host if request.client else None,
        status="success" if success else "failed"
    )
    db.add(audit)
    await db.commit()
    
    return {"success": success}


@router.post("/ufw/disable")
async def disable_ufw(
    request: Request,
    current_user: User = Depends(require_permission("firewall:write")),
    db: AsyncSession = Depends(get_db)
):
    """Disable UFW"""
    connector = connector_manager.get_connector("ufw")
    success = await connector.disable()
    
    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        action="EXECUTE",
        resource_type="firewall",
        description="Disabled UFW",
        ip_address=request.client.host if request.client else None,
        status="success" if success else "failed"
    )
    db.add(audit)
    await db.commit()
    
    return {"success": success}


@router.get("/ufw/apps")
async def get_ufw_apps(
    current_user: User = Depends(require_permission("firewall:read"))
):
    """Get UFW application list"""
    connector = connector_manager.get_connector("ufw")
    return await connector.get_app_list()


# ============ iptables Routes ============

@router.get("/iptables/status")
async def get_iptables_status(
    current_user: User = Depends(require_permission("firewall:read"))
):
    """Get iptables status"""
    connector = connector_manager.get_connector("iptables")
    info = await connector.check_availability()
    
    if info.status != ConnectorStatus.AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"iptables not available: {info.message}"
        )
    
    return await connector.get_status()


@router.get("/iptables/rules")
async def get_iptables_rules(
    table: str = "filter",
    current_user: User = Depends(require_permission("firewall:read"))
):
    """Get iptables rules for a specific table"""
    connector = connector_manager.get_connector("iptables")
    return await connector.get_rules(table)


@router.post("/iptables/rules")
async def add_iptables_rule(
    rule: IptablesRuleCreate,
    request: Request,
    current_user: User = Depends(require_permission("firewall:write")),
    db: AsyncSession = Depends(get_db)
):
    """Add a new iptables rule"""
    connector = connector_manager.get_connector("iptables")
    
    result = await connector.add_rule(rule.model_dump())
    
    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        action="CREATE",
        resource_type="firewall_rule",
        description=f"Added iptables rule: {rule.chain} {rule.target}",
        details=rule.model_dump(),
        ip_address=request.client.host if request.client else None,
        status="success" if result.get("success") else "failed",
        error_message=result.get("error")
    )
    db.add(audit)
    await db.commit()
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to add rule")
        )
    
    return result


@router.delete("/iptables/rules/{rule_id:path}")
async def delete_iptables_rule(
    rule_id: str,
    request: Request,
    current_user: User = Depends(require_permission("firewall:write")),
    db: AsyncSession = Depends(get_db)
):
    """Delete an iptables rule (rule_id format: table:chain:num)"""
    connector = connector_manager.get_connector("iptables")
    
    success = await connector.delete_rule(rule_id)
    
    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        action="DELETE",
        resource_type="firewall_rule",
        resource_id=rule_id,
        description=f"Deleted iptables rule {rule_id}",
        ip_address=request.client.host if request.client else None,
        status="success" if success else "failed"
    )
    db.add(audit)
    await db.commit()
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to delete rule"
        )
    
    return {"message": "Rule deleted successfully"}


# ============ firewalld Routes ============

@router.get("/firewalld/status")
async def get_firewalld_status(
    current_user: User = Depends(require_permission("firewall:read"))
):
    """Get firewalld status"""
    connector = connector_manager.get_connector("firewalld")
    info = await connector.check_availability()
    
    if info.status != ConnectorStatus.AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"firewalld not available: {info.message}"
        )
    
    return await connector.get_status()


@router.get("/firewalld/zones")
async def get_firewalld_zones(
    current_user: User = Depends(require_permission("firewall:read"))
):
    """Get all firewalld zones"""
    connector = connector_manager.get_connector("firewalld")
    return await connector.get_zones()


@router.get("/firewalld/rules")
async def get_firewalld_rules(
    current_user: User = Depends(require_permission("firewall:read"))
):
    """Get all firewalld rules"""
    connector = connector_manager.get_connector("firewalld")
    return await connector.get_rules()


@router.post("/firewalld/rules")
async def add_firewalld_rule(
    rule: FirewalldRuleCreate,
    request: Request,
    current_user: User = Depends(require_permission("firewall:write")),
    db: AsyncSession = Depends(get_db)
):
    """Add a new firewalld rule"""
    connector = connector_manager.get_connector("firewalld")
    
    result = await connector.add_rule(rule.model_dump())
    
    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        action="CREATE",
        resource_type="firewall_rule",
        description=f"Added firewalld rule: {rule.type}",
        details=rule.model_dump(),
        ip_address=request.client.host if request.client else None,
        status="success" if result.get("success") else "failed",
        error_message=result.get("error")
    )
    db.add(audit)
    await db.commit()
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to add rule")
        )
    
    return result


@router.get("/firewalld/services")
async def get_firewalld_services(
    current_user: User = Depends(require_permission("firewall:read"))
):
    """Get available firewalld services"""
    connector = connector_manager.get_connector("firewalld")
    return await connector.get_services()


# ============ nftables Routes ============

@router.get("/nftables/status")
async def get_nftables_status(
    current_user: User = Depends(require_permission("firewall:read"))
):
    """Get nftables status"""
    connector = connector_manager.get_connector("nftables")
    info = await connector.check_availability()
    
    if info.status != ConnectorStatus.AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"nftables not available: {info.message}"
        )
    
    return await connector.get_status()


@router.get("/nftables/rules")
async def get_nftables_rules(
    current_user: User = Depends(require_permission("firewall:read"))
):
    """Get all nftables rules"""
    connector = connector_manager.get_connector("nftables")
    return await connector.get_rules()


@router.get("/nftables/tables")
async def get_nftables_tables(
    current_user: User = Depends(require_permission("firewall:read"))
):
    """Get all nftables tables"""
    connector = connector_manager.get_connector("nftables")
    return await connector.get_tables()

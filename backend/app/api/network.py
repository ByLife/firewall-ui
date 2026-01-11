"""
Network API Routes - Routes, Interfaces, IP Rules
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional

from app.core.database import get_db
from app.core.security import require_permission
from app.models.user import User
from app.models.audit import AuditLog
from app.connectors import connector_manager, ConnectorStatus
from app.schemas import RouteCreate, RuleCreate, RouteResponse, InterfaceResponse

router = APIRouter(prefix="/network", tags=["Network"])


@router.get("/status")
async def get_network_status(
    current_user: User = Depends(require_permission("routes:read"))
):
    """Get network status"""
    connector = connector_manager.get_connector("network")
    info = await connector.check_availability()
    
    if info.status != ConnectorStatus.AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Network tools not available: {info.message}"
        )
    
    return await connector.get_status()


# ============ Interfaces ============

@router.get("/interfaces")
async def get_interfaces(
    current_user: User = Depends(require_permission("routes:read"))
):
    """Get all network interfaces"""
    connector = connector_manager.get_connector("network")
    return await connector.get_interfaces()


@router.get("/interfaces/{interface}/stats")
async def get_interface_stats(
    interface: str,
    current_user: User = Depends(require_permission("routes:read"))
):
    """Get statistics for a specific interface"""
    connector = connector_manager.get_connector("network")
    return await connector.get_link_stats(interface)


# ============ Routes ============

@router.get("/routes")
async def get_routes(
    table: str = "all",
    current_user: User = Depends(require_permission("routes:read"))
):
    """Get routing table"""
    connector = connector_manager.get_connector("network")
    
    if table == "all":
        return await connector.get_all_routes()
    else:
        return await connector.get_routes(table)


@router.post("/routes")
async def add_route(
    route: RouteCreate,
    request: Request,
    current_user: User = Depends(require_permission("routes:write")),
    db: AsyncSession = Depends(get_db)
):
    """Add a new route"""
    connector = connector_manager.get_connector("network")
    
    result = await connector.add_route(route.model_dump())
    
    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        action="CREATE",
        resource_type="route",
        description=f"Added route to {route.destination}",
        details=route.model_dump(),
        ip_address=request.client.host if request.client else None,
        status="success" if result.get("success") else "failed",
        error_message=result.get("error")
    )
    db.add(audit)
    await db.commit()
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to add route")
        )
    
    return result


@router.delete("/routes", response_model=None)
async def delete_route(
    destination: str,
    gateway: Optional[str] = None,
    device: Optional[str] = None,
    table: str = "main",
    current_user: User = Depends(require_permission("routes:write")),
    db: AsyncSession = Depends(get_db)
):
    """Delete a route"""
    connector = connector_manager.get_connector("network")
    
    route = {
        "destination": destination,
        "gateway": gateway,
        "device": device,
        "table": table
    }
    
    success = await connector.delete_route(route)
    
    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        action="DELETE",
        resource_type="route",
        description=f"Deleted route to {destination}",
        details=route,
        ip_address=request.client.host if request.client else None,
        status="success" if success else "failed"
    )
    db.add(audit)
    await db.commit()
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to delete route"
        )
    
    return {"message": "Route deleted successfully"}


# ============ IP Rules (Policy Routing) ============

@router.get("/rules")
async def get_ip_rules(
    current_user: User = Depends(require_permission("routes:read"))
):
    """Get IP routing rules (policy routing)"""
    connector = connector_manager.get_connector("network")
    return await connector.get_rules()


@router.post("/rules")
async def add_ip_rule(
    rule: RuleCreate,
    request: Request,
    current_user: User = Depends(require_permission("routes:write")),
    db: AsyncSession = Depends(get_db)
):
    """Add a new IP routing rule"""
    connector = connector_manager.get_connector("network")
    
    rule_data = {
        "priority": rule.priority,
        "from": rule.from_addr,
        "to": rule.to_addr,
        "table": rule.table,
        "fwmark": rule.fwmark
    }
    
    result = await connector.add_rule(rule_data)
    
    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        action="CREATE",
        resource_type="ip_rule",
        description=f"Added IP rule to table {rule.table}",
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


@router.delete("/rules")
async def delete_ip_rule(
    priority: int = None,
    from_addr: str = None,
    to_addr: str = None,
    table: str = None,
    request: Request = None,
    current_user: User = Depends(require_permission("routes:write")),
    db: AsyncSession = Depends(get_db)
):
    """Delete an IP routing rule"""
    connector = connector_manager.get_connector("network")
    
    rule = {
        "priority": priority,
        "from": from_addr,
        "to": to_addr,
        "table": table
    }
    
    success = await connector.delete_rule(rule)
    
    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        action="DELETE",
        resource_type="ip_rule",
        description=f"Deleted IP rule",
        details=rule,
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


# ============ ARP Table ============

@router.get("/arp")
async def get_arp_table(
    current_user: User = Depends(require_permission("routes:read"))
):
    """Get ARP table (neighbor cache)"""
    connector = connector_manager.get_connector("network")
    return await connector.get_arp_table()


# ============ Route Graph Data ============

@router.get("/graph")
async def get_network_graph(
    current_user: User = Depends(require_permission("routes:read"))
):
    """Get network topology data for graph visualization"""
    connector = connector_manager.get_connector("network")
    
    interfaces = await connector.get_interfaces()
    routes = await connector.get_all_routes()
    
    nodes = []
    edges = []
    
    # Add this host as central node
    nodes.append({
        "id": "localhost",
        "label": "This Host",
        "type": "host",
        "color": "#4CAF50"
    })
    
    # Add interfaces as nodes
    for iface in interfaces:
        if iface["name"] != "lo":
            node_id = f"iface_{iface['name']}"
            nodes.append({
                "id": node_id,
                "label": iface["name"],
                "type": "interface",
                "color": "#2196F3",
                "data": {
                    "state": iface["state"],
                    "mac": iface["mac"],
                    "ipv4": iface["ipv4"],
                    "ipv6": iface["ipv6"]
                }
            })
            
            # Connect interface to localhost
            edges.append({
                "source": "localhost",
                "target": node_id,
                "type": "interface"
            })
    
    # Add gateways and networks as nodes
    seen_networks = set()
    
    for route in routes:
        if route.get("gateway"):
            gateway_id = f"gw_{route['gateway']}"
            if gateway_id not in seen_networks:
                nodes.append({
                    "id": gateway_id,
                    "label": route["gateway"],
                    "type": "gateway",
                    "color": "#FF9800"
                })
                seen_networks.add(gateway_id)
            
            # Connect via interface
            if route.get("device"):
                edges.append({
                    "source": f"iface_{route['device']}",
                    "target": gateway_id,
                    "label": route.get("destination", "default"),
                    "type": "route"
                })
        
        # Add destination networks
        dest = route.get("destination", "default")
        if dest and dest != "default" and dest not in seen_networks:
            net_id = f"net_{dest}"
            nodes.append({
                "id": net_id,
                "label": dest,
                "type": "network",
                "color": "#9C27B0"
            })
            seen_networks.add(dest)
            
            if route.get("gateway"):
                edges.append({
                    "source": f"gw_{route['gateway']}",
                    "target": net_id,
                    "type": "route"
                })
            elif route.get("device"):
                edges.append({
                    "source": f"iface_{route['device']}",
                    "target": net_id,
                    "type": "direct"
                })
    
    return {
        "nodes": nodes,
        "edges": edges
    }

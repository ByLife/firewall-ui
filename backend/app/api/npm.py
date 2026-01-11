"""
Nginx Proxy Manager API Routes
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.core.security import require_permission
from app.models.user import User
from app.models.audit import AuditLog
from app.connectors import connector_manager, ConnectorStatus
from app.schemas import ProxyHostCreate, StreamCreate

router = APIRouter(prefix="/npm", tags=["Nginx Proxy Manager"])


@router.get("/status")
async def get_npm_status(
    current_user: User = Depends(require_permission("docker:read"))
):
    """Get NPM connection status"""
    connector = connector_manager.get_connector("npm")
    info = await connector.check_availability()
    
    if info.status != ConnectorStatus.AVAILABLE:
        return {
            "available": False,
            "message": info.message
        }
    
    return await connector.get_status()


@router.get("/proxy-hosts")
async def get_proxy_hosts(
    current_user: User = Depends(require_permission("docker:read"))
):
    """Get all proxy hosts"""
    connector = connector_manager.get_connector("npm")
    info = await connector.check_availability()
    
    if info.status != ConnectorStatus.AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"NPM not available: {info.message}"
        )
    
    return await connector.get_proxy_hosts()


@router.get("/proxy-hosts/{host_id}")
async def get_proxy_host(
    host_id: int,
    current_user: User = Depends(require_permission("docker:read"))
):
    """Get a specific proxy host"""
    connector = connector_manager.get_connector("npm")
    return await connector.get_proxy_host(host_id)


@router.post("/proxy-hosts")
async def create_proxy_host(
    host: ProxyHostCreate,
    request: Request,
    current_user: User = Depends(require_permission("docker:write")),
    db: AsyncSession = Depends(get_db)
):
    """Create a new proxy host"""
    connector = connector_manager.get_connector("npm")
    
    result = await connector.create_proxy_host(host.model_dump())
    
    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        action="CREATE",
        resource_type="npm_proxy_host",
        description=f"Created proxy host for {host.domain_names}",
        details=host.model_dump(),
        ip_address=request.client.host if request.client else None,
        status="success" if "error" not in result else "failed",
        error_message=result.get("error")
    )
    db.add(audit)
    await db.commit()
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error")
        )
    
    return result


@router.delete("/proxy-hosts/{host_id}")
async def delete_proxy_host(
    host_id: int,
    request: Request,
    current_user: User = Depends(require_permission("docker:write")),
    db: AsyncSession = Depends(get_db)
):
    """Delete a proxy host"""
    connector = connector_manager.get_connector("npm")
    
    result = await connector.delete_proxy_host(host_id)
    
    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        action="DELETE",
        resource_type="npm_proxy_host",
        resource_id=str(host_id),
        description=f"Deleted proxy host #{host_id}",
        ip_address=request.client.host if request.client else None,
        status="success" if "error" not in result else "failed"
    )
    db.add(audit)
    await db.commit()
    
    return result


@router.get("/streams")
async def get_streams(
    current_user: User = Depends(require_permission("docker:read"))
):
    """Get all stream (TCP/UDP) proxies"""
    connector = connector_manager.get_connector("npm")
    return await connector.get_streams()


@router.post("/streams")
async def create_stream(
    stream: StreamCreate,
    request: Request,
    current_user: User = Depends(require_permission("docker:write")),
    db: AsyncSession = Depends(get_db)
):
    """Create a new stream proxy"""
    connector = connector_manager.get_connector("npm")
    
    result = await connector.create_stream(stream.model_dump())
    
    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        action="CREATE",
        resource_type="npm_stream",
        description=f"Created stream proxy on port {stream.incoming_port}",
        details=stream.model_dump(),
        ip_address=request.client.host if request.client else None,
        status="success" if "error" not in result else "failed"
    )
    db.add(audit)
    await db.commit()
    
    return result


@router.get("/redirections")
async def get_redirections(
    current_user: User = Depends(require_permission("docker:read"))
):
    """Get all redirection hosts"""
    connector = connector_manager.get_connector("npm")
    return await connector.get_redirection_hosts()


@router.get("/certificates")
async def get_certificates(
    current_user: User = Depends(require_permission("docker:read"))
):
    """Get all SSL certificates"""
    connector = connector_manager.get_connector("npm")
    return await connector.get_certificates()


@router.get("/access-lists")
async def get_access_lists(
    current_user: User = Depends(require_permission("docker:read"))
):
    """Get all access lists"""
    connector = connector_manager.get_connector("npm")
    return await connector.get_access_lists()


@router.get("/ports")
async def get_npm_ports(
    current_user: User = Depends(require_permission("docker:read"))
):
    """Get all ports used by NPM"""
    connector = connector_manager.get_connector("npm")
    return await connector.get_all_ports()

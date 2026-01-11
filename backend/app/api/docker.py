"""
Docker API Routes
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional

from app.core.security import require_permission
from app.models.user import User
from app.connectors import connector_manager, ConnectorStatus

router = APIRouter(prefix="/docker", tags=["Docker"])


@router.get("/status")
async def get_docker_status(
    current_user: User = Depends(require_permission("docker:read"))
):
    """Get Docker daemon status"""
    connector = connector_manager.get_connector("docker")
    info = await connector.check_availability()
    
    if info.status != ConnectorStatus.AVAILABLE:
        return {
            "available": False,
            "message": info.message
        }
    
    return await connector.get_status()


@router.get("/containers")
async def get_containers(
    all: bool = True,
    current_user: User = Depends(require_permission("docker:read"))
):
    """Get all Docker containers"""
    connector = connector_manager.get_connector("docker")
    info = await connector.check_availability()
    
    if info.status != ConnectorStatus.AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Docker not available: {info.message}"
        )
    
    return await connector.get_containers(all=all)


@router.get("/containers/{container_id}")
async def get_container(
    container_id: str,
    current_user: User = Depends(require_permission("docker:read"))
):
    """Get detailed information about a container"""
    connector = connector_manager.get_connector("docker")
    return await connector.inspect_container(container_id)


@router.get("/containers/{container_id}/logs")
async def get_container_logs(
    container_id: str,
    tail: int = 100,
    current_user: User = Depends(require_permission("docker:read"))
):
    """Get container logs"""
    connector = connector_manager.get_connector("docker")
    logs = await connector.get_container_logs(container_id, tail)
    return {"logs": logs}


@router.get("/containers/{container_id}/ports")
async def get_container_ports(
    container_id: str,
    current_user: User = Depends(require_permission("docker:read"))
):
    """Get port mappings for a specific container"""
    connector = connector_manager.get_connector("docker")
    return await connector.get_container_ports(container_id)


@router.get("/networks")
async def get_networks(
    current_user: User = Depends(require_permission("docker:read"))
):
    """Get all Docker networks"""
    connector = connector_manager.get_connector("docker")
    info = await connector.check_availability()
    
    if info.status != ConnectorStatus.AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Docker not available: {info.message}"
        )
    
    return await connector.get_networks()


@router.get("/ports")
async def get_docker_exposed_ports(
    current_user: User = Depends(require_permission("docker:read"))
):
    """Get all ports exposed by Docker containers"""
    connector = connector_manager.get_connector("docker")
    info = await connector.check_availability()
    
    if info.status != ConnectorStatus.AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Docker not available: {info.message}"
        )
    
    return await connector.get_exposed_ports()

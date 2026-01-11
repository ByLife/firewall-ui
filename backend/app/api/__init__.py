"""
API Router - Combines all API routes
"""

from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.firewall import router as firewall_router
from app.api.network import router as network_router
from app.api.ports import router as ports_router
from app.api.docker import router as docker_router
from app.api.npm import router as npm_router
from app.api.dashboard import router as dashboard_router
from app.api.audit import router as audit_router

api_router = APIRouter()

# Include all routers
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(firewall_router)
api_router.include_router(network_router)
api_router.include_router(ports_router)
api_router.include_router(docker_router)
api_router.include_router(npm_router)
api_router.include_router(dashboard_router)
api_router.include_router(audit_router)


@api_router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

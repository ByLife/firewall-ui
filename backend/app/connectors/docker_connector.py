"""
Docker Connector
"""

import asyncio
import shutil
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from dataclasses import dataclass

from app.connectors.base import BaseConnector, ConnectorInfo, ConnectorStatus
from app.core.config import settings

if TYPE_CHECKING:
    import docker


class DockerConnector(BaseConnector):
    """Connector for Docker containers and networks"""
    
    name = "docker"
    type = "container"
    
    def __init__(self):
        self.client: Optional[Any] = None
        self.docker_available = shutil.which("docker") is not None
        self._init_client()
    
    def _init_client(self):
        """Initialize Docker client"""
        if not self.docker_available:
            self.client = None
            self._init_error = "Docker command not found"
            return
            
        try:
            import docker
            # Try different connection methods
            try:
                # First try unix socket directly
                self.client = docker.DockerClient(base_url='unix://var/run/docker.sock')
                self.client.ping()
            except Exception:
                # Fallback to from_env()
                self.client = docker.from_env()
                self.client.ping()
            self._init_error = None
        except docker.errors.DockerException as e:
            self.client = None
            self._init_error = f"Docker error: {str(e)}"
        except Exception as e:
            self.client = None
            self._init_error = f"Failed to connect to Docker: {str(e)}"
    
    async def check_availability(self) -> ConnectorInfo:
        """Check if Docker is available"""
        if not self.docker_available:
            return ConnectorInfo(
                name=self.name,
                type=self.type,
                status=ConnectorStatus.UNAVAILABLE,
                message="Docker command not found in PATH"
            )
        
        if self.client is None:
            # Try to reinitialize
            self._init_client()
            
        if self.client is None:
            return ConnectorInfo(
                name=self.name,
                type=self.type,
                status=ConnectorStatus.UNAVAILABLE,
                message=getattr(self, '_init_error', "Docker client not initialized")
            )
        
        try:
            loop = asyncio.get_event_loop()
            version = await loop.run_in_executor(None, lambda: self.client.version())
            
            return ConnectorInfo(
                name=self.name,
                type=self.type,
                status=ConnectorStatus.AVAILABLE,
                version=version.get("Version", "unknown")
            )
        except Exception as e:
            return ConnectorInfo(
                name=self.name,
                type=self.type,
                status=ConnectorStatus.ERROR,
                message=str(e)
            )
    
    async def get_status(self) -> Dict[str, Any]:
        """Get Docker status"""
        if self.client is None:
            return {"available": False, "error": "Docker client not initialized"}
        
        try:
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, lambda: self.client.info())
            
            return {
                "available": True,
                "containers_running": info.get("ContainersRunning", 0),
                "containers_paused": info.get("ContainersPaused", 0),
                "containers_stopped": info.get("ContainersStopped", 0),
                "images": info.get("Images", 0),
                "docker_root_dir": info.get("DockerRootDir"),
                "server_version": info.get("ServerVersion")
            }
        except Exception as e:
            return {"available": False, "error": str(e)}
    
    async def get_containers(self, all: bool = True) -> List[Dict[str, Any]]:
        """Get all containers"""
        if self.client is None:
            return []
        
        try:
            loop = asyncio.get_event_loop()
            containers = await loop.run_in_executor(
                None, 
                lambda: self.client.containers.list(all=all)
            )
            
            result = []
            for container in containers:
                ports = container.attrs.get("NetworkSettings", {}).get("Ports", {}) or {}
                port_mappings = []
                
                for container_port, host_bindings in ports.items():
                    if host_bindings:
                        for binding in host_bindings:
                            port_mappings.append({
                                "container_port": container_port,
                                "host_ip": binding.get("HostIp", "0.0.0.0"),
                                "host_port": binding.get("HostPort")
                            })
                
                networks = container.attrs.get("NetworkSettings", {}).get("Networks", {}) or {}
                network_info = []
                for net_name, net_data in networks.items():
                    network_info.append({
                        "name": net_name,
                        "ip": net_data.get("IPAddress"),
                        "gateway": net_data.get("Gateway"),
                        "mac": net_data.get("MacAddress")
                    })
                
                result.append({
                    "id": container.short_id,
                    "name": container.name,
                    "image": container.image.tags[0] if container.image.tags else container.image.short_id,
                    "status": container.status,
                    "ports": port_mappings,
                    "networks": network_info,
                    "created": container.attrs.get("Created"),
                    "labels": container.labels
                })
            
            return result
        except Exception as e:
            return [{"error": str(e)}]
    
    async def get_networks(self) -> List[Dict[str, Any]]:
        """Get all Docker networks"""
        if self.client is None:
            return []
        
        try:
            loop = asyncio.get_event_loop()
            networks = await loop.run_in_executor(
                None,
                lambda: self.client.networks.list()
            )
            
            result = []
            for network in networks:
                ipam = network.attrs.get("IPAM", {})
                config = ipam.get("Config", [{}])
                
                containers = network.attrs.get("Containers", {}) or {}
                connected = []
                for container_id, container_info in containers.items():
                    connected.append({
                        "id": container_id[:12],
                        "name": container_info.get("Name"),
                        "ipv4": container_info.get("IPv4Address"),
                        "ipv6": container_info.get("IPv6Address")
                    })
                
                result.append({
                    "id": network.short_id,
                    "name": network.name,
                    "driver": network.attrs.get("Driver"),
                    "scope": network.attrs.get("Scope"),
                    "internal": network.attrs.get("Internal", False),
                    "subnet": config[0].get("Subnet") if config else None,
                    "gateway": config[0].get("Gateway") if config else None,
                    "containers": connected
                })
            
            return result
        except Exception as e:
            return [{"error": str(e)}]
    
    async def get_container_ports(self, container_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get port mappings for containers"""
        containers = await self.get_containers()
        
        all_ports = []
        for container in containers:
            if container_id and container.get("id") != container_id:
                continue
            
            for port in container.get("ports", []):
                all_ports.append({
                    "container_id": container.get("id"),
                    "container_name": container.get("name"),
                    "container_port": port.get("container_port"),
                    "host_ip": port.get("host_ip"),
                    "host_port": port.get("host_port"),
                    "image": container.get("image"),
                    "status": container.get("status")
                })
        
        return all_ports
    
    async def inspect_container(self, container_id: str) -> Dict[str, Any]:
        """Get detailed information about a container"""
        if self.client is None:
            return {"error": "Docker client not initialized"}
        
        try:
            loop = asyncio.get_event_loop()
            container = await loop.run_in_executor(
                None,
                lambda: self.client.containers.get(container_id)
            )
            
            return container.attrs
        except Exception as e:
            return {"error": str(e)}
    
    async def get_container_logs(self, container_id: str, tail: int = 100) -> str:
        """Get container logs"""
        if self.client is None:
            return "Docker client not initialized"
        
        try:
            loop = asyncio.get_event_loop()
            container = await loop.run_in_executor(
                None,
                lambda: self.client.containers.get(container_id)
            )
            
            logs = await loop.run_in_executor(
                None,
                lambda: container.logs(tail=tail, timestamps=True)
            )
            
            return logs.decode('utf-8', errors='replace')
        except Exception as e:
            return str(e)
    
    async def get_exposed_ports(self) -> List[Dict[str, Any]]:
        """Get all ports exposed by running containers"""
        containers = await self.get_containers(all=False)  # Only running containers
        
        exposed = []
        for container in containers:
            for port in container.get("ports", []):
                if port.get("host_port"):
                    exposed.append({
                        "port": int(port.get("host_port")),
                        "protocol": port.get("container_port", "/tcp").split("/")[-1],
                        "container": container.get("name"),
                        "container_id": container.get("id"),
                        "container_port": port.get("container_port"),
                        "host_ip": port.get("host_ip")
                    })
        
        return exposed

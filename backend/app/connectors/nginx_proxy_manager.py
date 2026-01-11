"""
Nginx Proxy Manager Connector
"""

import asyncio
from typing import List, Dict, Any, Optional
import httpx

from app.connectors.base import BaseConnector, ConnectorInfo, ConnectorStatus
from app.core.config import settings


class NginxProxyManagerConnector(BaseConnector):
    """Connector for Nginx Proxy Manager API"""
    
    name = "nginx-proxy-manager"
    type = "proxy"
    
    def __init__(self, base_url: Optional[str] = None, email: Optional[str] = None, password: Optional[str] = None):
        self.base_url = (base_url or settings.NPM_URL).rstrip('/')
        self.email = email or settings.NPM_EMAIL
        self.password = password or settings.NPM_PASSWORD
        self.token = None
        self._client = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=30.0,
                verify=False  # NPM often uses self-signed certs
            )
        return self._client
    
    async def _authenticate(self) -> bool:
        """Authenticate with NPM API"""
        if not self.base_url or not self.email or not self.password:
            return False
        
        try:
            client = await self._get_client()
            response = await client.post(
                "/api/tokens",
                json={
                    "identity": self.email,
                    "secret": self.password
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("token")
                return True
            return False
        except Exception:
            return False
    
    async def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make an authenticated request to NPM API"""
        if not self.token:
            if not await self._authenticate():
                return {"error": "Authentication failed"}
        
        client = await self._get_client()
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.token}"
        
        try:
            response = await client.request(method, endpoint, headers=headers, **kwargs)
            
            if response.status_code == 401:
                # Token expired, re-authenticate
                if await self._authenticate():
                    headers["Authorization"] = f"Bearer {self.token}"
                    response = await client.request(method, endpoint, headers=headers, **kwargs)
                else:
                    return {"error": "Authentication failed"}
            
            if response.status_code >= 400:
                return {"error": response.text, "status_code": response.status_code}
            
            return response.json() if response.text else {}
        except Exception as e:
            return {"error": str(e)}
    
    async def check_availability(self) -> ConnectorInfo:
        """Check if NPM is available"""
        if not self.base_url:
            return ConnectorInfo(
                name=self.name,
                type=self.type,
                status=ConnectorStatus.UNAVAILABLE,
                message="NPM URL not configured"
            )
        
        try:
            client = await self._get_client()
            response = await client.get("/api/")
            
            if response.status_code in [200, 401]:
                return ConnectorInfo(
                    name=self.name,
                    type=self.type,
                    status=ConnectorStatus.AVAILABLE,
                    message="NPM API accessible"
                )
            else:
                return ConnectorInfo(
                    name=self.name,
                    type=self.type,
                    status=ConnectorStatus.ERROR,
                    message=f"HTTP {response.status_code}"
                )
        except Exception as e:
            return ConnectorInfo(
                name=self.name,
                type=self.type,
                status=ConnectorStatus.ERROR,
                message=str(e)
            )
    
    async def get_status(self) -> Dict[str, Any]:
        """Get NPM status"""
        if not self.base_url:
            return {"available": False, "error": "NPM URL not configured"}
        
        authenticated = await self._authenticate()
        
        return {
            "available": authenticated,
            "base_url": self.base_url,
            "authenticated": authenticated
        }
    
    async def get_proxy_hosts(self) -> List[Dict[str, Any]]:
        """Get all proxy hosts"""
        result = await self._request("GET", "/api/nginx/proxy-hosts")
        
        if isinstance(result, dict) and "error" in result:
            return [result]
        
        if not isinstance(result, list):
            return []
        
        hosts = []
        for host in result:
            if isinstance(host, dict):
                hosts.append({
                    "id": host.get("id"),
                    "domain_names": host.get("domain_names", []),
                    "forward_host": host.get("forward_host"),
                    "forward_port": host.get("forward_port"),
                    "forward_scheme": host.get("forward_scheme", "http"),
                    "ssl_enabled": host.get("ssl_forced", False) or bool(host.get("certificate_id")),
                    "enabled": host.get("enabled", True),
                    "access_list_id": host.get("access_list_id"),
                    "advanced_config": host.get("advanced_config", ""),
                    "meta": host.get("meta", {})
                })
        
        return hosts
    
    async def get_proxy_host(self, host_id: int) -> Dict[str, Any]:
        """Get a specific proxy host"""
        return await self._request("GET", f"/api/nginx/proxy-hosts/{host_id}")
    
    async def create_proxy_host(self, host: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new proxy host
        
        Args:
            host: Dictionary with keys:
                - domain_names: list of domain names
                - forward_host: backend host/IP
                - forward_port: backend port
                - forward_scheme: http/https
                - ssl_forced: force SSL
                - block_exploits: block common exploits
                - caching_enabled: enable caching
        """
        payload = {
            "domain_names": host.get("domain_names", []),
            "forward_host": host.get("forward_host"),
            "forward_port": host.get("forward_port"),
            "forward_scheme": host.get("forward_scheme", "http"),
            "ssl_forced": host.get("ssl_forced", False),
            "block_exploits": host.get("block_exploits", True),
            "caching_enabled": host.get("caching_enabled", False),
            "allow_websocket_upgrade": host.get("allow_websocket_upgrade", True),
            "access_list_id": host.get("access_list_id", 0),
            "advanced_config": host.get("advanced_config", ""),
            "meta": host.get("meta", {"letsencrypt_agree": False})
        }
        
        return await self._request("POST", "/api/nginx/proxy-hosts", json=payload)
    
    async def update_proxy_host(self, host_id: int, host: Dict[str, Any]) -> Dict[str, Any]:
        """Update a proxy host"""
        return await self._request("PUT", f"/api/nginx/proxy-hosts/{host_id}", json=host)
    
    async def delete_proxy_host(self, host_id: int) -> Dict[str, Any]:
        """Delete a proxy host"""
        return await self._request("DELETE", f"/api/nginx/proxy-hosts/{host_id}")
    
    async def get_redirection_hosts(self) -> List[Dict[str, Any]]:
        """Get all redirection hosts"""
        result = await self._request("GET", "/api/nginx/redirection-hosts")
        
        if isinstance(result, dict) and "error" in result:
            return [result]
        
        if isinstance(result, list):
            return result
        return []
    
    async def get_streams(self) -> List[Dict[str, Any]]:
        """Get all stream (TCP/UDP) proxies"""
        result = await self._request("GET", "/api/nginx/streams")
        
        if isinstance(result, dict) and "error" in result:
            return [result]
        
        if not isinstance(result, list):
            return []
        
        streams = []
        for stream in result:
            if isinstance(stream, dict):
                streams.append({
                    "id": stream.get("id"),
                    "incoming_port": stream.get("incoming_port"),
                    "forwarding_host": stream.get("forwarding_host"),
                    "forwarding_port": stream.get("forwarding_port"),
                    "tcp_forwarding": stream.get("tcp_forwarding", True),
                    "udp_forwarding": stream.get("udp_forwarding", False),
                    "enabled": stream.get("enabled", True)
                })
        
        return streams
    
    async def create_stream(self, stream: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new stream proxy"""
        payload = {
            "incoming_port": stream.get("incoming_port"),
            "forwarding_host": stream.get("forwarding_host"),
            "forwarding_port": stream.get("forwarding_port"),
            "tcp_forwarding": stream.get("tcp_forwarding", True),
            "udp_forwarding": stream.get("udp_forwarding", False)
        }
        
        return await self._request("POST", "/api/nginx/streams", json=payload)
    
    async def get_certificates(self) -> List[Dict[str, Any]]:
        """Get all SSL certificates"""
        result = await self._request("GET", "/api/nginx/certificates")
        
        if isinstance(result, dict) and "error" in result:
            return [result]
        
        if isinstance(result, list):
            return result
        return []
    
    async def get_access_lists(self) -> List[Dict[str, Any]]:
        """Get all access lists"""
        result = await self._request("GET", "/api/nginx/access-lists")
        
        if isinstance(result, dict) and "error" in result:
            return [result]
        
        if isinstance(result, list):
            return result
        return []
    
    async def get_dead_hosts(self) -> List[Dict[str, Any]]:
        """Get all 404 hosts"""
        result = await self._request("GET", "/api/nginx/dead-hosts")
        
        if isinstance(result, dict) and "error" in result:
            return [result]
        
        if isinstance(result, list):
            return result
        return []
    
    async def get_users(self) -> List[Dict[str, Any]]:
        """Get all NPM users"""
        result = await self._request("GET", "/api/users")
        
        if isinstance(result, dict) and "error" in result:
            return [result]
        
        if isinstance(result, list):
            return result
        return []
    
    async def get_audit_log(self) -> List[Dict[str, Any]]:
        """Get NPM audit log"""
        result = await self._request("GET", "/api/audit-log")
        
        if isinstance(result, dict) and "error" in result:
            return [result]
        
        if isinstance(result, list):
            return result
        return []
    
    async def get_all_ports(self) -> List[Dict[str, Any]]:
        """Get all ports being used by NPM (proxy hosts and streams)"""
        ports = []
        
        # Proxy hosts (typically 80/443)
        hosts = await self.get_proxy_hosts()
        for host in hosts:
            if "error" not in host:
                for domain in host.get("domain_names", []):
                    ports.append({
                        "type": "proxy",
                        "domain": domain,
                        "forward_host": host.get("forward_host"),
                        "forward_port": host.get("forward_port"),
                        "ssl": host.get("ssl_enabled", False)
                    })
        
        # Stream proxies (custom ports)
        streams = await self.get_streams()
        for stream in streams:
            if "error" not in stream:
                ports.append({
                    "type": "stream",
                    "incoming_port": stream.get("incoming_port"),
                    "forward_host": stream.get("forwarding_host"),
                    "forward_port": stream.get("forwarding_port"),
                    "tcp": stream.get("tcp_forwarding", True),
                    "udp": stream.get("udp_forwarding", False)
                })
        
        return ports
    
    async def close(self):
        """Close the HTTP client"""
        if self._client:
            await self._client.aclose()

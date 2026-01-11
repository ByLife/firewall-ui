"""
Connectors Module
Provides unified access to all connectors
"""

from typing import Dict, List, Any, Optional, cast
from app.connectors.base import BaseConnector, ConnectorInfo, ConnectorStatus
from app.connectors.ufw import UFWConnector
from app.connectors.iptables import IptablesConnector
from app.connectors.nftables import NftablesConnector
from app.connectors.firewalld import FirewalldConnector
from app.connectors.network import NetworkConnector
from app.connectors.port_scanner import PortScannerConnector
from app.connectors.docker_connector import DockerConnector
from app.connectors.nginx_proxy_manager import NginxProxyManagerConnector


class ConnectorManager:
    """Manages all available connectors"""
    
    def __init__(self):
        self._connectors: Dict[str, BaseConnector] = {}
        self._init_connectors()
    
    def _init_connectors(self):
        """Initialize all connectors"""
        self._connectors = {
            "ufw": UFWConnector(),
            "iptables": IptablesConnector(),
            "nftables": NftablesConnector(),
            "firewalld": FirewalldConnector(),
            "network": NetworkConnector(),
            "portscanner": PortScannerConnector(),
            "docker": DockerConnector(),
            "npm": NginxProxyManagerConnector()
        }
    
    def get_connector(self, name: str) -> Optional[BaseConnector]:
        """Get a specific connector by name"""
        return self._connectors.get(name)
    
    def get_firewall_connectors(self) -> Dict[str, BaseConnector]:
        """Get all firewall connectors"""
        return {
            name: conn for name, conn in self._connectors.items()
            if conn.type == "firewall"
        }
    
    async def check_all_availability(self) -> List[ConnectorInfo]:
        """Check availability of all connectors"""
        results = []
        for name, connector in self._connectors.items():
            info = await connector.check_availability()
            results.append(info)
        return results
    
    async def get_available_firewalls(self) -> List[str]:
        """Get list of available firewall backends"""
        available = []
        for name, connector in self.get_firewall_connectors().items():
            info = await connector.check_availability()
            if info.status == ConnectorStatus.AVAILABLE:
                available.append(name)
        return available
    
    async def get_preferred_firewall(self) -> Optional[str]:
        """Get the preferred (first available) firewall backend"""
        # Order of preference
        preferred_order = ["ufw", "firewalld", "nftables", "iptables"]
        
        for name in preferred_order:
            connector = self._connectors.get(name)
            if connector:
                info = await connector.check_availability()
                if info.status == ConnectorStatus.AVAILABLE:
                    return name
        
        return None


# Global connector manager instance
connector_manager = ConnectorManager()


# Convenience functions
async def get_firewall_rules(backend: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get firewall rules from specified or preferred backend"""
    if not backend:
        backend = await connector_manager.get_preferred_firewall()
    
    if not backend:
        return []
    
    connector = connector_manager.get_connector(backend)
    if connector and hasattr(connector, 'get_rules'):
        return await connector.get_rules()  # type: ignore
    
    return []


async def get_network_routes() -> List[Dict[str, Any]]:
    """Get all network routes"""
    connector = connector_manager.get_connector("network")
    if connector and hasattr(connector, 'get_all_routes'):
        return await connector.get_all_routes()  # type: ignore
    return []


async def get_listening_ports() -> List[Dict[str, Any]]:
    """Get all listening ports"""
    connector = connector_manager.get_connector("portscanner")
    if connector and hasattr(connector, 'get_listening_ports'):
        return await connector.get_listening_ports()  # type: ignore
    return []

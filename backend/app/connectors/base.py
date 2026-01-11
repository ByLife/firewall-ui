"""
Base Connector Class
All connectors inherit from this base class
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class ConnectorStatus(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    ERROR = "error"


@dataclass
class ConnectorInfo:
    """Information about a connector"""
    name: str
    type: str
    status: ConnectorStatus
    version: Optional[str] = None
    message: Optional[str] = None


class BaseConnector(ABC):
    """Base class for all connectors"""
    
    name: str = "base"
    type: str = "unknown"
    
    @abstractmethod
    async def check_availability(self) -> ConnectorInfo:
        """Check if the connector is available on this system"""
        pass
    
    @abstractmethod
    async def get_status(self) -> Dict[str, Any]:
        """Get current status"""
        pass


class BaseFirewallConnector(BaseConnector):
    """Base class for firewall connectors"""
    
    type: str = "firewall"
    
    @abstractmethod
    async def get_rules(self) -> List[Dict[str, Any]]:
        """Get all firewall rules"""
        pass
    
    @abstractmethod
    async def add_rule(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new firewall rule"""
        pass
    
    @abstractmethod
    async def delete_rule(self, rule_id: str) -> bool:
        """Delete a firewall rule"""
        pass
    
    @abstractmethod
    async def enable(self) -> bool:
        """Enable the firewall"""
        pass
    
    @abstractmethod
    async def disable(self) -> bool:
        """Disable the firewall"""
        pass


class BaseNetworkConnector(BaseConnector):
    """Base class for network connectors"""
    
    type: str = "network"
    
    @abstractmethod
    async def get_interfaces(self) -> List[Dict[str, Any]]:
        """Get network interfaces"""
        pass
    
    @abstractmethod
    async def get_routes(self) -> List[Dict[str, Any]]:
        """Get routing table"""
        pass
    
    @abstractmethod
    async def add_route(self, route: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new route"""
        pass
    
    @abstractmethod
    async def delete_route(self, route: Dict[str, Any]) -> bool:
        """Delete a route"""
        pass

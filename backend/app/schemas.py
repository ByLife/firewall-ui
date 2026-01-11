"""
Pydantic Schemas for API
"""

from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


# ============ Auth Schemas ============

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: int
    username: str
    role: str


class LoginRequest(BaseModel):
    username: str
    password: str


# ============ User Schemas ============

class UserRole(str, Enum):
    admin = "admin"
    operator = "operator"
    viewer = "viewer"


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)
    role: UserRole = UserRole.viewer


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserPasswordUpdate(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)


class UserResponse(UserBase):
    id: int
    role: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============ Firewall Schemas ============

class FirewallRuleBase(BaseModel):
    action: str = Field(..., pattern="^(allow|deny|reject|drop|accept|limit)$")
    direction: str = Field(default="in", pattern="^(in|out|fwd)$")
    protocol: Optional[str] = Field(default="any", pattern="^(tcp|udp|icmp|any|all)$")
    port: Optional[str] = None
    from_ip: Optional[str] = "any"
    to_ip: Optional[str] = "any"
    comment: Optional[str] = None


class UFWRuleCreate(FirewallRuleBase):
    app: Optional[str] = None


class IptablesRuleCreate(BaseModel):
    table: str = "filter"
    chain: str = "INPUT"
    target: str = "ACCEPT"
    protocol: Optional[str] = None
    source: Optional[str] = None
    destination: Optional[str] = None
    dport: Optional[int] = None
    sport: Optional[int] = None
    in_interface: Optional[str] = None
    out_interface: Optional[str] = None
    position: Optional[int] = None


class FirewalldRuleCreate(BaseModel):
    zone: Optional[str] = None
    type: str = "port"  # port, service, rich
    port: Optional[str] = None
    protocol: Optional[str] = "tcp"
    service: Optional[str] = None
    rich_rule: Optional[str] = None
    permanent: bool = True


class FirewallRuleResponse(BaseModel):
    id: str
    backend: str
    action: Optional[str] = None
    direction: Optional[str] = None
    protocol: Optional[str] = None
    port: Optional[str] = None
    source: Optional[str] = None
    destination: Optional[str] = None
    raw: Optional[str] = None


class FirewallStatusResponse(BaseModel):
    backend: str
    enabled: bool
    details: Dict[str, Any]


# ============ Network Schemas ============

class RouteBase(BaseModel):
    destination: str
    gateway: Optional[str] = None
    device: Optional[str] = None
    metric: Optional[int] = None
    table: str = "main"


class RouteCreate(RouteBase):
    type: Optional[str] = None


class RouteResponse(RouteBase):
    id: str
    protocol: Optional[str] = None
    scope: Optional[str] = None
    prefsrc: Optional[str] = None


class RuleCreate(BaseModel):
    priority: Optional[int] = None
    from_addr: Optional[str] = Field(None, alias="from")
    to_addr: Optional[str] = Field(None, alias="to")
    table: str
    fwmark: Optional[str] = None


class InterfaceResponse(BaseModel):
    name: str
    state: str
    mac: Optional[str] = None
    mtu: Optional[int] = None
    ipv4: List[Dict[str, Any]] = []
    ipv6: List[Dict[str, Any]] = []


# ============ Port Scan Schemas ============

class PortScanRequest(BaseModel):
    target: str
    ports: Optional[List[int]] = None
    timeout: float = 1.0
    use_nmap: bool = False


class PortScanResult(BaseModel):
    host: str
    port: int
    protocol: str
    state: str
    service: Optional[str] = None
    timestamp: Optional[str] = None


# ============ Docker Schemas ============

class ContainerResponse(BaseModel):
    id: str
    name: str
    image: str
    status: str
    ports: List[Dict[str, Any]]
    networks: List[Dict[str, Any]]


class NetworkResponse(BaseModel):
    id: str
    name: str
    driver: Optional[str] = None
    subnet: Optional[str] = None
    gateway: Optional[str] = None
    containers: List[Dict[str, Any]] = []


# ============ NPM Schemas ============

class ProxyHostCreate(BaseModel):
    domain_names: List[str]
    forward_host: str
    forward_port: int
    forward_scheme: str = "http"
    ssl_forced: bool = False
    block_exploits: bool = True
    caching_enabled: bool = False


class StreamCreate(BaseModel):
    incoming_port: int
    forwarding_host: str
    forwarding_port: int
    tcp_forwarding: bool = True
    udp_forwarding: bool = False


# ============ Audit Schemas ============

class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    username: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    description: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


# ============ Dashboard Schemas ============

class SystemStatusResponse(BaseModel):
    firewalls: List[Dict[str, Any]]
    network: Dict[str, Any]
    docker: Dict[str, Any]
    npm: Dict[str, Any]


class DashboardStatsResponse(BaseModel):
    total_firewall_rules: int
    total_routes: int
    listening_ports: int
    docker_containers: int
    active_connections: int

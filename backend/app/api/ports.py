"""
Port Scanning API Routes
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict

from app.core.database import get_db
from app.core.security import require_permission
from app.models.user import User
from app.models.audit import AuditLog
from app.connectors import connector_manager, ConnectorStatus
from app.schemas import PortScanRequest, PortScanResult

router = APIRouter(prefix="/ports", tags=["Ports"])


@router.get("/listening")
async def get_listening_ports(
    current_user: User = Depends(require_permission("ports:read"))
):
    """Get all listening ports on the local system"""
    connector = connector_manager.get_connector("portscanner")
    return await connector.get_listening_ports()


@router.get("/public-ip")
async def get_public_ip(
    current_user: User = Depends(require_permission("ports:read"))
):
    """Get the public IP address of this system"""
    connector = connector_manager.get_connector("portscanner")
    public_ip = await connector.get_public_ip()
    
    if not public_ip:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not determine public IP"
        )
    
    return {"public_ip": public_ip}


@router.post("/scan")
async def scan_ports(
    scan_request: PortScanRequest,
    request: Request,
    current_user: User = Depends(require_permission("ports:scan")),
    db: AsyncSession = Depends(get_db)
):
    """Scan ports on a target host"""
    connector = connector_manager.get_connector("portscanner")
    
    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        action="EXECUTE",
        resource_type="port_scan",
        description=f"Port scan on {scan_request.target}",
        details=scan_request.model_dump(),
        ip_address=request.client.host if request.client else None,
        status="success"
    )
    db.add(audit)
    await db.commit()
    
    if scan_request.use_nmap:
        # Use nmap if requested
        ports_str = ",".join(str(p) for p in scan_request.ports) if scan_request.ports else "1-1000"
        return await connector.scan_with_nmap(scan_request.target, ports_str)
    else:
        # Use socket-based scanning
        return await connector.scan_ports(
            scan_request.target, 
            scan_request.ports, 
            scan_request.timeout
        )


@router.get("/scan/{target}")
async def quick_scan(
    target: str,
    ports: Optional[str] = None,
    current_user: User = Depends(require_permission("ports:scan"))
):
    """Quick port scan on common ports"""
    connector = connector_manager.get_connector("portscanner")
    
    port_list = None
    if ports:
        port_list = [int(p.strip()) for p in ports.split(",")]
    
    return await connector.scan_ports(target, port_list)


@router.post("/scan-public")
async def scan_public_ports(
    ports: Optional[List[int]] = None,
    request: Request = None,
    current_user: User = Depends(require_permission("ports:scan")),
    db: AsyncSession = Depends(get_db)
):
    """Scan open ports on the public IP"""
    connector = connector_manager.get_connector("portscanner")
    
    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        action="EXECUTE",
        resource_type="port_scan",
        description="Scan public IP ports",
        ip_address=request.client.host if request.client else None,
        status="success"
    )
    db.add(audit)
    await db.commit()
    
    return await connector.scan_public_ports(ports)


@router.get("/exposed")
async def get_exposed_ports(
    current_user: User = Depends(require_permission("ports:read"))
):
    """Get all ports exposed by running services (combining multiple sources)"""
    portscanner = connector_manager.get_connector("portscanner")
    docker = connector_manager.get_connector("docker")
    npm = connector_manager.get_connector("npm")
    
    result = {
        "system_ports": [],
        "docker_ports": [],
        "npm_ports": []
    }
    
    # System listening ports
    result["system_ports"] = await portscanner.get_listening_ports()
    
    # Docker exposed ports
    docker_info = await docker.check_availability()
    if docker_info.status == ConnectorStatus.AVAILABLE:
        result["docker_ports"] = await docker.get_exposed_ports()
    
    # Nginx Proxy Manager ports
    npm_info = await npm.check_availability()
    if npm_info.status == ConnectorStatus.AVAILABLE:
        result["npm_ports"] = await npm.get_all_ports()
    
    return result


@router.get("/summary")
async def get_port_summary(
    current_user: User = Depends(require_permission("ports:read"))
):
    """Get a summary of all exposed/listening ports"""
    portscanner = connector_manager.get_connector("portscanner")
    docker = connector_manager.get_connector("docker")
    
    listening = await portscanner.get_listening_ports()
    
    # Get Docker exposed ports
    docker_ports = []
    docker_info = await docker.check_availability()
    if docker_info.status == ConnectorStatus.AVAILABLE:
        docker_ports = await docker.get_exposed_ports()
    
    # Combine and deduplicate
    all_ports = set()
    port_details = {}
    
    for port_info in listening:
        port = port_info.get("port")
        if port:
            all_ports.add(port)
            port_details[port] = {
                "port": port,
                "protocol": port_info.get("protocol", "tcp"),
                "source": "system",
                "ip": port_info.get("ip", "0.0.0.0")
            }
    
    for port_info in docker_ports:
        port = port_info.get("port")
        if port:
            all_ports.add(port)
            if port in port_details:
                port_details[port]["container"] = port_info.get("container")
            else:
                port_details[port] = {
                    "port": port,
                    "protocol": port_info.get("protocol", "tcp"),
                    "source": "docker",
                    "container": port_info.get("container")
                }
    
    return {
        "total_ports": len(all_ports),
        "ports": sorted(port_details.values(), key=lambda x: x["port"])
    }


@router.post("/block")
async def block_port(
    port: int,
    protocol: str = "tcp",
    interface: Optional[str] = None,
    request: Request = None,
    current_user: User = Depends(require_permission("firewall:write")),
    db: AsyncSession = Depends(get_db)
):
    """Block a port, optionally on a specific interface
    
    Args:
        port: Port number to block
        protocol: tcp or udp (default: tcp)
        interface: Network interface name (optional, e.g., 'eth0', 'ens6'). If not specified, blocks on all interfaces.
    """
    # Try to use the preferred firewall backend
    available = await connector_manager.get_available_firewalls()
    
    if not available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No firewall backend available"
        )
    
    result = None
    backend_used = None
    rules_added = []
    
    if "iptables" in available:
        connector = connector_manager.get_connector("iptables")
        backend_used = "iptables"
        
        # Rule 1: Block in INPUT chain (for non-Docker services)
        rule_input = {
            "table": "filter",
            "chain": "INPUT",
            "target": "DROP",
            "protocol": protocol,
            "dport": port,
            "position": 1
        }
        if interface and interface != "all":
            rule_input["in_interface"] = interface
        
        result1 = await connector.add_rule(rule_input)
        rules_added.append({"chain": "INPUT", "result": result1})
        
        # Rule 2: Block in DOCKER-USER chain (for Docker containers)
        # DOCKER-USER is processed before Docker's NAT rules
        rule_docker = {
            "table": "filter",
            "chain": "DOCKER-USER",
            "target": "DROP",
            "protocol": protocol,
            "dport": port,
            "position": 1
        }
        if interface and interface != "all":
            rule_docker["in_interface"] = interface
        
        result2 = await connector.add_rule(rule_docker)
        rules_added.append({"chain": "DOCKER-USER", "result": result2})
        
        # Consider success if at least one rule was added
        result = {
            "success": result1.get("success") or result2.get("success"),
            "message": f"Rules added to INPUT and DOCKER-USER chains",
            "details": rules_added
        }
    
    # Fallback to UFW if iptables not available
    elif "ufw" in available:
        connector = connector_manager.get_connector("ufw")
        backend_used = "ufw"
        
        rule = {
            "action": "deny",
            "direction": "in",
            "port": str(port),
            "protocol": protocol,
            "comment": f"Blocked by firewall-ui"
        }
        
        if interface and interface != "all":
            rule["interface"] = interface
        
        result = await connector.add_rule(rule)
    
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not add firewall rule"
        )
    
    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        action="CREATE",
        resource_type="firewall_rule",
        description=f"Blocked port {port}/{protocol}" + (f" on {interface}" if interface else ""),
        details={
            "port": port,
            "protocol": protocol,
            "interface": interface,
            "backend": backend_used
        },
        ip_address=request.client.host if request.client else None,
        status="success" if result.get("success") else "failed",
        error_message=result.get("error")
    )
    db.add(audit)
    await db.commit()
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to block port")
        )
    
    return {
        "success": True,
        "message": f"Port {port}/{protocol} blocked" + (f" on {interface}" if interface else ""),
        "backend": backend_used,
        "details": result
    }


@router.get("/by-interface")
async def get_ports_by_interface(
    current_user: User = Depends(require_permission("ports:read"))
):
    """Get listening ports grouped by network interface"""
    portscanner = connector_manager.get_connector("portscanner")
    network_connector = connector_manager.get_connector("iproute2")
    
    listening = await portscanner.get_listening_ports()
    
    # Get network interfaces
    interfaces = []
    try:
        interfaces = await network_connector.get_interfaces()
    except Exception:
        pass
    
    # Group ports by interface
    by_interface: Dict[str, List] = {"all": [], "unknown": []}
    
    # Initialize with known interfaces
    for iface in interfaces:
        iface_name = iface.get("name", "")
        if iface_name and iface_name not in by_interface:
            by_interface[iface_name] = []
    
    for port_info in listening:
        iface = port_info.get("interface", "unknown")
        if iface not in by_interface:
            by_interface[iface] = []
        by_interface[iface].append(port_info)
    
    # Build result with interface details
    result = []
    for iface_name, ports in by_interface.items():
        if not ports and iface_name not in ["all", "unknown"]:
            continue  # Skip interfaces with no listening ports
        
        # Find interface details
        iface_details = next(
            (i for i in interfaces if i.get("name") == iface_name),
            None
        )
        
        result.append({
            "interface": iface_name,
            "state": iface_details.get("state") if iface_details else None,
            "ipv4": iface_details.get("ipv4", []) if iface_details else [],
            "ipv6": iface_details.get("ipv6", []) if iface_details else [],
            "ports": sorted(ports, key=lambda x: x.get("port", 0)),
            "port_count": len(ports)
        })
    
    # Sort: 'all' first, then by port count desc
    result.sort(key=lambda x: (x["interface"] != "all", -x["port_count"]))
    
    return result


@router.get("/firewall-status")
async def get_firewall_debug_status(
    current_user: User = Depends(require_permission("firewall:read"))
):
    """Get detailed firewall status for debugging"""
    available = await connector_manager.get_available_firewalls()
    
    result = {
        "available_backends": available,
        "ufw": None,
        "iptables": None
    }
    
    # Check UFW
    if "ufw" in available:
        try:
            ufw = connector_manager.get_connector("ufw")
            ufw_status = await ufw.get_status()
            ufw_rules = await ufw.get_rules()
            result["ufw"] = {
                "status": ufw_status,
                "rules": ufw_rules
            }
        except Exception as e:
            result["ufw"] = {"error": str(e)}
    
    # Check iptables
    if "iptables" in available:
        try:
            iptables = connector_manager.get_connector("iptables")
            iptables_rules = await iptables.get_rules("filter")
            result["iptables"] = {
                "rules": iptables_rules
            }
        except Exception as e:
            result["iptables"] = {"error": str(e)}
    
    return result
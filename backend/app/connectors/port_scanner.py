"""
Port Scanner Connector
"""

import asyncio
import socket
import subprocess
import shutil
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from app.connectors.base import BaseConnector, ConnectorInfo, ConnectorStatus


@dataclass
class PortScanResult:
    """Result of a port scan"""
    ip: str
    port: int
    protocol: str
    state: str
    service: Optional[str] = None
    banner: Optional[str] = None


class PortScannerConnector(BaseConnector):
    """Port scanner using multiple methods"""
    
    name = "portscanner"
    type = "scanner"
    
    COMMON_PORTS = [
        21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445, 993, 995,
        1723, 3306, 3389, 5432, 5900, 8080, 8443, 8888
    ]
    
    def __init__(self):
        self.nmap_path = shutil.which("nmap")
        self.ss_path = shutil.which("ss")
        self.netstat_path = shutil.which("netstat")
    
    async def check_availability(self) -> ConnectorInfo:
        """Check if port scanning is available"""
        tools = []
        if self.nmap_path:
            tools.append("nmap")
        if self.ss_path:
            tools.append("ss")
        if self.netstat_path:
            tools.append("netstat")
        
        if tools:
            return ConnectorInfo(
                name=self.name,
                type=self.type,
                status=ConnectorStatus.AVAILABLE,
                message=f"Available tools: {', '.join(tools)}"
            )
        else:
            return ConnectorInfo(
                name=self.name,
                type=self.type,
                status=ConnectorStatus.UNAVAILABLE,
                message="No port scanning tools available"
            )
    
    async def get_status(self) -> Dict[str, Any]:
        """Get scanner status"""
        return {
            "nmap_available": self.nmap_path is not None,
            "ss_available": self.ss_path is not None,
            "netstat_available": self.netstat_path is not None
        }
    
    async def get_listening_ports(self) -> List[Dict[str, Any]]:
        """Get all listening ports on the local system with process and interface info"""
        if self.ss_path:
            return await self._get_ports_ss()
        elif self.netstat_path:
            return await self._get_ports_netstat()
        return []
    
    async def _get_interface_for_ip(self, ip: str) -> Optional[str]:
        """Get the network interface that an IP belongs to"""
        if ip in ("0.0.0.0", "::", "*", ""):
            return "all"  # Listening on all interfaces
        
        try:
            ip_path = shutil.which("ip")
            if ip_path:
                process = await asyncio.create_subprocess_exec(
                    ip_path, "addr", "show",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await process.communicate()
                output = stdout.decode()
                
                # Parse ip addr output to find interface for IP
                current_iface = None
                for line in output.split('\n'):
                    # Interface line: "2: eth0: <BROADCAST,..."
                    if ': ' in line and not line.startswith(' '):
                        parts = line.split(': ')
                        if len(parts) >= 2:
                            current_iface = parts[1].split('@')[0]
                    # IP line: "    inet 192.168.1.10/24..."
                    elif 'inet ' in line or 'inet6 ' in line:
                        if ip in line:
                            return current_iface
        except Exception:
            pass
        return None
    
    async def _get_ports_ss(self) -> List[Dict[str, Any]]:
        """Get listening ports using ss command with process info"""
        if not self.ss_path:
            return []
        
        # Use -tulnp for process info (requires root)
        process = await asyncio.create_subprocess_exec(
            "sudo", self.ss_path, "-tulnp",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        ports = []
        lines = stdout.decode().strip().split('\n')
        
        # Get interface mapping
        interface_cache: Dict[str, str] = {}
        
        for line in lines[1:]:  # Skip header
            parts = line.split()
            if len(parts) >= 5:
                state = parts[0]
                local_addr = parts[4]
                
                # Parse address and port
                ip = ""
                port = ""
                if local_addr.startswith('['):
                    # IPv6
                    match = local_addr.rsplit(']:', 1)
                    if len(match) == 2:
                        ip = match[0][1:]  # Remove leading [
                        port = match[1]
                else:
                    # IPv4
                    match = local_addr.rsplit(':', 1)
                    if len(match) == 2:
                        ip = match[0]
                        port = match[1]
                    else:
                        continue
                
                protocol = "tcp" if "tcp" in parts[0].lower() else "udp"
                
                # Extract process info: users:(("nginx",pid=1234,fd=5))
                process_name = None
                pid = None
                if len(parts) >= 7:
                    proc_info = parts[6] if len(parts) > 6 else ""
                    # Parse process info
                    import re
                    proc_match = re.search(r'\(\("([^"]+)",pid=(\d+)', proc_info)
                    if proc_match:
                        process_name = proc_match.group(1)
                        pid = int(proc_match.group(2))
                
                # Get interface for IP
                clean_ip = ip if ip != "*" else "0.0.0.0"
                if clean_ip not in interface_cache:
                    interface_cache[clean_ip] = await self._get_interface_for_ip(clean_ip) or "unknown"
                
                ports.append({
                    "ip": clean_ip,
                    "address": clean_ip,  # Alias for frontend
                    "port": int(port) if port != "*" and port.isdigit() else 0,
                    "protocol": protocol,
                    "state": "LISTEN",
                    "process": process_name,
                    "program": process_name,  # Alias for frontend
                    "pid": pid,
                    "interface": interface_cache[clean_ip],
                    "is_public": clean_ip in ("0.0.0.0", "::", "")
                })
        
        return ports
    
    async def _get_ports_netstat(self) -> List[Dict[str, Any]]:
        """Get listening ports using netstat command"""
        if not self.netstat_path:
            return []
        process = await asyncio.create_subprocess_exec(
            self.netstat_path, "-tuln",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        ports = []
        lines = stdout.decode().strip().split('\n')
        
        for line in lines[2:]:  # Skip headers
            parts = line.split()
            if len(parts) >= 4:
                protocol = parts[0].lower()
                local_addr = parts[3]
                
                # Parse address and port
                if ':' in local_addr:
                    addr_parts = local_addr.rsplit(':', 1)
                    ip = addr_parts[0]
                    port = addr_parts[1]
                    
                    ports.append({
                        "ip": ip if ip != "0.0.0.0" and ip != "::" else "0.0.0.0",
                        "port": int(port) if port.isdigit() else 0,
                        "protocol": protocol.replace('6', ''),
                        "state": parts[-1] if len(parts) >= 6 else "LISTEN"
                    })
        
        return ports
    
    async def scan_port(self, host: str, port: int, timeout: float = 1.0) -> Dict[str, Any]:
        """Scan a single port on a host"""
        loop = asyncio.get_event_loop()
        
        try:
            # TCP connect scan
            future = loop.run_in_executor(
                None,
                self._tcp_connect,
                host, port, timeout
            )
            is_open = await asyncio.wait_for(future, timeout=timeout + 0.5)
            
            return {
                "host": host,
                "port": port,
                "protocol": "tcp",
                "state": "open" if is_open else "closed",
                "timestamp": datetime.utcnow().isoformat()
            }
        except asyncio.TimeoutError:
            return {
                "host": host,
                "port": port,
                "protocol": "tcp",
                "state": "filtered",
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "host": host,
                "port": port,
                "protocol": "tcp",
                "state": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def _tcp_connect(self, host: str, port: int, timeout: float) -> bool:
        """Attempt TCP connection to a port"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            result = sock.connect_ex((host, port))
            return result == 0
        finally:
            sock.close()
    
    async def scan_ports(self, host: str, ports: Optional[List[int]] = None, 
                         timeout: float = 1.0) -> List[Dict[str, Any]]:
        """Scan multiple ports on a host"""
        if ports is None:
            ports = self.COMMON_PORTS
        
        # Scan ports concurrently in batches
        batch_size = 50
        results = []
        
        for i in range(0, len(ports), batch_size):
            batch = ports[i:i + batch_size]
            tasks = [self.scan_port(host, port, timeout) for port in batch]
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)
        
        return results
    
    async def scan_with_nmap(self, target: str, ports: str = "1-1000", 
                              options: Optional[List[str]] = None) -> Dict[str, Any]:
        """Scan using nmap if available"""
        if not self.nmap_path:
            return {"error": "nmap not available"}
        
        args = [self.nmap_path, "-p", ports]
        
        if options:
            args.extend(options)
        else:
            args.extend(["-sT", "-sV", "--open"])
        
        args.append(target)
        
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            return {"error": stderr.decode()}
        
        # Parse nmap output
        output = stdout.decode()
        return self._parse_nmap_output(output)
    
    def _parse_nmap_output(self, output: str) -> Dict[str, Any]:
        """Parse nmap output"""
        import re
        
        result = {
            "host": None,
            "state": None,
            "ports": [],
            "raw": output
        }
        
        lines = output.split('\n')
        
        for line in lines:
            # Host status
            if "Nmap scan report for" in line:
                match = re.search(r'for (\S+)', line)
                if match:
                    result["host"] = match.group(1)
            
            # Host state
            if "Host is up" in line:
                result["state"] = "up"
            
            # Port info: 22/tcp   open  ssh     OpenSSH 8.2
            port_match = re.match(r'(\d+)/(\w+)\s+(\w+)\s+(\S+)\s*(.*)', line)
            if port_match:
                result["ports"].append({
                    "port": int(port_match.group(1)),
                    "protocol": port_match.group(2),
                    "state": port_match.group(3),
                    "service": port_match.group(4),
                    "version": port_match.group(5).strip() if port_match.group(5) else None
                })
        
        return result
    
    async def get_public_ip(self) -> Optional[str]:
        """Get the public IP address of this system"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get('https://api.ipify.org?format=json', timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('ip')
        except Exception:
            pass
        
        # Fallback: try to get from socket
        try:
            process = await asyncio.create_subprocess_shell(
                "curl -s https://api.ipify.org",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()
            if stdout:
                return stdout.decode().strip()
        except Exception:
            pass
        
        return None
    
    async def scan_public_ports(self, ports: Optional[List[int]] = None) -> List[Dict[str, Any]]:
        """Scan open ports on the public IP"""
        public_ip = await self.get_public_ip()
        
        if not public_ip:
            return [{"error": "Could not determine public IP"}]
        
        return await self.scan_ports(public_ip, ports)

"""
UFW (Uncomplicated Firewall) Connector
"""

import asyncio
import re
import shutil
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from app.connectors.base import BaseFirewallConnector, ConnectorInfo, ConnectorStatus


@dataclass
class UFWRule:
    """Represents a UFW rule"""
    id: str
    action: str  # ALLOW, DENY, REJECT, LIMIT
    direction: str  # IN, OUT
    from_ip: str
    to_ip: str
    port: Optional[str]
    protocol: Optional[str]  # tcp, udp, any
    app: Optional[str]
    comment: Optional[str]
    enabled: bool = True


class UFWConnector(BaseFirewallConnector):
    """Connector for UFW (Uncomplicated Firewall)"""
    
    name = "ufw"
    type = "firewall"
    
    def __init__(self):
        self.ufw_path = shutil.which("ufw")
    
    async def _run_command(self, *args) -> tuple[int, str, str]:
        """Run a UFW command and return output"""
        cmd = ["sudo", self.ufw_path] + list(args)
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        return process.returncode or 0, stdout.decode(), stderr.decode()
    
    async def check_availability(self) -> ConnectorInfo:
        """Check if UFW is available"""
        if not self.ufw_path:
            return ConnectorInfo(
                name=self.name,
                type=self.type,
                status=ConnectorStatus.UNAVAILABLE,
                message="UFW not found in PATH"
            )
        
        try:
            returncode, stdout, stderr = await self._run_command("version")
            if returncode == 0:
                version_match = re.search(r'ufw (\d+\.\d+(?:\.\d+)?)', stdout)
                version = version_match.group(1) if version_match else "unknown"
                return ConnectorInfo(
                    name=self.name,
                    type=self.type,
                    status=ConnectorStatus.AVAILABLE,
                    version=version
                )
            else:
                return ConnectorInfo(
                    name=self.name,
                    type=self.type,
                    status=ConnectorStatus.ERROR,
                    message=stderr or "Failed to get UFW version"
                )
        except Exception as e:
            return ConnectorInfo(
                name=self.name,
                type=self.type,
                status=ConnectorStatus.ERROR,
                message=str(e)
            )
    
    async def get_status(self) -> Dict[str, Any]:
        """Get UFW status"""
        returncode, stdout, stderr = await self._run_command("status", "verbose")
        
        if returncode != 0:
            return {"error": stderr, "enabled": False}
        
        lines = stdout.strip().split('\n')
        status_info = {
            "enabled": False,
            "default_incoming": "deny",
            "default_outgoing": "allow",
            "default_routed": "disabled",
            "logging": "off"
        }
        
        for line in lines:
            if line.startswith("Status:"):
                status_info["enabled"] = "active" in line.lower()
            elif line.startswith("Default:"):
                parts = line.split()
                for i, part in enumerate(parts):
                    if "incoming" in part.lower():
                        status_info["default_incoming"] = parts[i-1].lower() if i > 0 else "deny"
                    elif "outgoing" in part.lower():
                        status_info["default_outgoing"] = parts[i-1].lower() if i > 0 else "allow"
            elif line.startswith("Logging:"):
                status_info["logging"] = line.split(":")[1].strip().lower()
        
        return status_info
    
    async def get_rules(self) -> List[Dict[str, Any]]:
        """Get all UFW rules"""
        returncode, stdout, stderr = await self._run_command("status", "numbered")
        
        if returncode != 0:
            return []
        
        rules = []
        lines = stdout.strip().split('\n')
        
        # Skip header lines
        in_rules = False
        for line in lines:
            if line.startswith("--"):
                in_rules = True
                continue
            
            if not in_rules or not line.strip():
                continue
            
            # Parse rule line: [ 1] 22/tcp                     ALLOW IN    Anywhere
            rule_match = re.match(
                r'\[\s*(\d+)\]\s+(.+?)\s+(ALLOW|DENY|REJECT|LIMIT)\s+(IN|OUT|FWD)?\s*(.*)',
                line
            )
            
            if rule_match:
                rule_id = rule_match.group(1)
                to_spec = rule_match.group(2).strip()
                action = rule_match.group(3)
                direction = rule_match.group(4) or "IN"
                from_spec = rule_match.group(5).strip() if rule_match.group(5) else "Anywhere"
                
                # Parse port/protocol
                port = None
                protocol = None
                app = None
                
                port_match = re.match(r'(\d+)(?:/(\w+))?', to_spec)
                if port_match:
                    port = port_match.group(1)
                    protocol = port_match.group(2) or "any"
                elif to_spec not in ["Anywhere", ""]:
                    app = to_spec
                
                rules.append({
                    "id": rule_id,
                    "action": action.lower(),
                    "direction": direction.lower(),
                    "port": port,
                    "protocol": protocol,
                    "app": app,
                    "from": from_spec,
                    "to": to_spec,
                    "raw": line.strip()
                })
        
        return rules
    
    async def add_rule(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new UFW rule
        
        Args:
            rule: Dictionary with keys:
                - action: allow, deny, reject, limit
                - direction: in, out (optional, default: in)
                - interface: network interface (optional, e.g., 'eth0', 'ens6')
                - port: port number or range (e.g., "22", "80:443")
                - protocol: tcp, udp, or any (optional)
                - from_ip: source IP/network (optional, default: any)
                - to_ip: destination IP (optional)
                - app: application name (optional, instead of port)
                - comment: rule comment (optional)
        """
        args = []
        
        # Build command arguments
        action = rule.get("action", "allow").lower()
        direction = rule.get("direction", "in").lower()
        interface = rule.get("interface")
        
        # Action
        args.append(action)
        
        # Direction with optional interface: "deny in on eth0"
        if direction == "out":
            if interface and interface != "all":
                args.extend(["out", "on", interface])
            else:
                args.append("out")
        else:
            if interface and interface != "all":
                args.extend(["in", "on", interface])
        
        # From
        from_ip = rule.get("from_ip")
        if from_ip and from_ip != "any":
            args.extend(["from", from_ip])
        
        # To any port X
        to_ip = rule.get("to_ip")
        port = rule.get("port")
        protocol = rule.get("protocol", "").lower()
        app = rule.get("app")
        
        if app:
            # Application-based rule
            args.extend(["to", "any", "app", app])
        elif port:
            # Port-based rule: "to any port 80" or "to any port 80/tcp"
            args.extend(["to", "any", "port", str(port)])
            if protocol and protocol != "any":
                args.extend(["proto", protocol])
        elif to_ip and to_ip != "any":
            args.extend(["to", to_ip])
        
        # Comment
        comment = rule.get("comment")
        if comment:
            args.extend(["comment", comment])
        
        # Execute
        returncode, stdout, stderr = await self._run_command(*args)
        
        if returncode == 0:
            return {"success": True, "message": stdout.strip()}
        else:
            return {"success": False, "error": stderr.strip() or stdout.strip()}
    
    async def delete_rule(self, rule_id: str) -> bool:
        """Delete a UFW rule by its number"""
        # UFW requires confirmation, use --force to skip
        returncode, stdout, stderr = await self._run_command(
            "--force", "delete", rule_id
        )
        return returncode == 0
    
    async def enable(self) -> bool:
        """Enable UFW"""
        returncode, stdout, stderr = await self._run_command("--force", "enable")
        return returncode == 0
    
    async def disable(self) -> bool:
        """Disable UFW"""
        returncode, stdout, stderr = await self._run_command("disable")
        return returncode == 0
    
    async def reset(self) -> bool:
        """Reset UFW to defaults"""
        returncode, stdout, stderr = await self._run_command("--force", "reset")
        return returncode == 0
    
    async def reload(self) -> bool:
        """Reload UFW"""
        returncode, stdout, stderr = await self._run_command("reload")
        return returncode == 0
    
    async def get_app_list(self) -> List[Dict[str, Any]]:
        """Get list of available applications"""
        returncode, stdout, stderr = await self._run_command("app", "list")
        
        if returncode != 0:
            return []
        
        apps = []
        lines = stdout.strip().split('\n')
        
        for line in lines:
            if line.startswith("Available applications:"):
                continue
            app_name = line.strip()
            if app_name:
                apps.append({"name": app_name})
        
        return apps
    
    async def get_app_info(self, app_name: str) -> Dict[str, Any]:
        """Get information about a specific application"""
        returncode, stdout, stderr = await self._run_command("app", "info", app_name)
        
        if returncode != 0:
            return {"error": stderr}
        
        info = {"name": app_name}
        lines = stdout.strip().split('\n')
        
        for line in lines:
            if ":" in line:
                key, value = line.split(":", 1)
                info[key.strip().lower()] = value.strip()
        
        return info

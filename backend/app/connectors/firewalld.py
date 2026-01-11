"""
firewalld Connector
"""

import asyncio
import shutil
from typing import List, Dict, Any

from app.connectors.base import BaseFirewallConnector, ConnectorInfo, ConnectorStatus


class FirewalldConnector(BaseFirewallConnector):
    """Connector for firewalld (dynamic firewall manager)"""
    
    name = "firewalld"
    type = "firewall"
    
    def __init__(self):
        self.firewall_cmd_path = shutil.which("firewall-cmd")
    
    async def _run_command(self, *args) -> tuple[int, str, str]:
        """Run a firewall-cmd command"""
        cmd = ["sudo", self.firewall_cmd_path] + list(args)
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        return process.returncode or 0, stdout.decode(), stderr.decode()
    
    async def check_availability(self) -> ConnectorInfo:
        """Check if firewalld is available"""
        if not self.firewall_cmd_path:
            return ConnectorInfo(
                name=self.name,
                type=self.type,
                status=ConnectorStatus.UNAVAILABLE,
                message="firewall-cmd not found in PATH"
            )
        
        try:
            returncode, stdout, stderr = await self._run_command("--version")
            if returncode == 0:
                version = stdout.strip()
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
                    message=stderr
                )
        except Exception as e:
            return ConnectorInfo(
                name=self.name,
                type=self.type,
                status=ConnectorStatus.ERROR,
                message=str(e)
            )
    
    async def get_status(self) -> Dict[str, Any]:
        """Get firewalld status"""
        state_code, state_out, _ = await self._run_command("--state")
        
        status = {
            "running": state_out.strip() == "running",
            "default_zone": None,
            "active_zones": []
        }
        
        if status["running"]:
            # Get default zone
            _, default_zone, _ = await self._run_command("--get-default-zone")
            status["default_zone"] = default_zone.strip()
            
            # Get active zones
            _, active_zones, _ = await self._run_command("--get-active-zones")
            zones = []
            current_zone = None
            
            for line in active_zones.strip().split('\n'):
                if line and not line.startswith(' '):
                    current_zone = {"name": line.strip(), "interfaces": [], "sources": []}
                    zones.append(current_zone)
                elif current_zone and 'interfaces:' in line:
                    current_zone["interfaces"] = line.split(':')[1].strip().split()
                elif current_zone and 'sources:' in line:
                    current_zone["sources"] = line.split(':')[1].strip().split()
            
            status["active_zones"] = zones
        
        return status
    
    async def get_zones(self) -> List[Dict[str, Any]]:
        """Get all available zones"""
        returncode, stdout, stderr = await self._run_command("--get-zones")
        
        if returncode != 0:
            return []
        
        zones = []
        for zone_name in stdout.strip().split():
            zone_info = await self.get_zone_info(zone_name)
            zones.append(zone_info)
        
        return zones
    
    async def get_zone_info(self, zone: str) -> Dict[str, Any]:
        """Get detailed information about a zone"""
        _, stdout, _ = await self._run_command("--zone", zone, "--list-all")
        
        info = {"name": zone, "services": [], "ports": [], "rich_rules": []}
        
        for line in stdout.strip().split('\n'):
            if 'services:' in line:
                info["services"] = line.split(':')[1].strip().split()
            elif 'ports:' in line:
                info["ports"] = line.split(':')[1].strip().split()
            elif 'rich rules:' in line.lower():
                info["rich_rules"] = [line.split(':', 1)[1].strip()] if ':' in line else []
            elif 'target:' in line:
                info["target"] = line.split(':')[1].strip()
            elif 'interfaces:' in line:
                info["interfaces"] = line.split(':')[1].strip().split()
            elif 'sources:' in line:
                info["sources"] = line.split(':')[1].strip().split()
        
        return info
    
    async def get_rules(self) -> List[Dict[str, Any]]:
        """Get all firewall rules across all zones"""
        rules = []
        zones = await self.get_zones()
        rule_id = 0
        
        for zone in zones:
            zone_name = zone.get("name")
            
            # Add port rules
            for port in zone.get("ports", []):
                if port:
                    port_num, protocol = port.split('/') if '/' in port else (port, 'tcp')
                    rules.append({
                        "id": str(rule_id),
                        "zone": zone_name,
                        "type": "port",
                        "port": port_num,
                        "protocol": protocol,
                        "action": "allow"
                    })
                    rule_id += 1
            
            # Add service rules
            for service in zone.get("services", []):
                if service:
                    rules.append({
                        "id": str(rule_id),
                        "zone": zone_name,
                        "type": "service",
                        "service": service,
                        "action": "allow"
                    })
                    rule_id += 1
            
            # Add rich rules
            for rich_rule in zone.get("rich_rules", []):
                if rich_rule:
                    rules.append({
                        "id": str(rule_id),
                        "zone": zone_name,
                        "type": "rich",
                        "rule": rich_rule,
                        "action": "custom"
                    })
                    rule_id += 1
        
        return rules
    
    async def add_rule(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        """Add a firewalld rule
        
        Args:
            rule: Dictionary with keys:
                - zone: zone name (optional, uses default if not specified)
                - type: port, service, rich
                - port: port number (for type=port)
                - protocol: tcp/udp (for type=port)
                - service: service name (for type=service)
                - rich_rule: rich rule string (for type=rich)
                - permanent: make rule permanent (default: True)
        """
        zone = rule.get("zone")
        rule_type = rule.get("type", "port")
        permanent = rule.get("permanent", True)
        
        args = []
        if permanent:
            args.append("--permanent")
        if zone:
            args.extend(["--zone", zone])
        
        if rule_type == "port":
            port = rule.get("port")
            protocol = rule.get("protocol", "tcp")
            args.extend(["--add-port", f"{port}/{protocol}"])
        elif rule_type == "service":
            service = rule.get("service")
            args.extend(["--add-service", service])
        elif rule_type == "rich":
            rich_rule = rule.get("rich_rule")
            args.extend(["--add-rich-rule", rich_rule])
        else:
            return {"success": False, "error": f"Unknown rule type: {rule_type}"}
        
        returncode, stdout, stderr = await self._run_command(*args)
        
        if returncode == 0:
            # Reload to apply permanent changes
            if permanent:
                await self._run_command("--reload")
            return {"success": True, "message": "Rule added successfully"}
        else:
            return {"success": False, "error": stderr.strip() or stdout.strip()}
    
    async def delete_rule(self, rule_id: str) -> bool:
        """Delete a firewalld rule
        
        Note: rule_id is in format zone:type:value (e.g., public:port:80/tcp)
        """
        parts = rule_id.split(":", 2)
        if len(parts) < 3:
            return False
        
        zone, rule_type, value = parts
        
        args = ["--permanent"]
        if zone:
            args.extend(["--zone", zone])
        
        if rule_type == "port":
            args.extend(["--remove-port", value])
        elif rule_type == "service":
            args.extend(["--remove-service", value])
        elif rule_type == "rich":
            args.extend(["--remove-rich-rule", value])
        else:
            return False
        
        returncode, _, _ = await self._run_command(*args)
        
        if returncode == 0:
            await self._run_command("--reload")
            return True
        return False
    
    async def enable(self) -> bool:
        """Start and enable firewalld"""
        process = await asyncio.create_subprocess_exec(
            "sudo", "systemctl", "start", "firewalld",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
        return process.returncode == 0
    
    async def disable(self) -> bool:
        """Stop firewalld"""
        process = await asyncio.create_subprocess_exec(
            "sudo", "systemctl", "stop", "firewalld",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
        return process.returncode == 0
    
    async def reload(self) -> bool:
        """Reload firewalld"""
        returncode, _, _ = await self._run_command("--reload")
        return returncode == 0
    
    async def get_services(self) -> List[str]:
        """Get all available services"""
        returncode, stdout, _ = await self._run_command("--get-services")
        if returncode == 0:
            return stdout.strip().split()
        return []
    
    async def set_default_zone(self, zone: str) -> bool:
        """Set the default zone"""
        returncode, _, _ = await self._run_command("--set-default-zone", zone)
        return returncode == 0

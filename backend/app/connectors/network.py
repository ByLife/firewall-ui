"""
Network Connector - Routes and Interfaces
"""

import asyncio
import re
import shutil
from typing import List, Dict, Any, Optional

from app.connectors.base import BaseNetworkConnector, ConnectorInfo, ConnectorStatus


class NetworkConnector(BaseNetworkConnector):
    """Connector for Linux network management (ip command)"""
    
    name = "iproute2"
    type = "network"
    
    def __init__(self):
        self.ip_path = shutil.which("ip")
    
    async def _run_command(self, *args, use_json: bool = False) -> tuple[int, str, str]:
        """Run an ip command"""
        cmd = ["sudo", self.ip_path]
        if use_json:
            cmd.append("-j")
        cmd.extend(args)
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        return process.returncode or 0, stdout.decode(), stderr.decode()
    
    async def check_availability(self) -> ConnectorInfo:
        """Check if iproute2 is available"""
        if not self.ip_path:
            return ConnectorInfo(
                name=self.name,
                type=self.type,
                status=ConnectorStatus.UNAVAILABLE,
                message="ip command not found in PATH"
            )
        
        try:
            returncode, stdout, stderr = await self._run_command("-V")
            if returncode == 0:
                version_match = re.search(r'iproute2-(\S+)', stdout)
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
        """Get network status"""
        interfaces = await self.get_interfaces()
        routes = await self.get_routes()
        rules = await self.get_rules()
        
        return {
            "available": True,
            "interface_count": len(interfaces),
            "route_count": len(routes),
            "rule_count": len(rules)
        }
    
    async def get_interfaces(self) -> List[Dict[str, Any]]:
        """Get all network interfaces"""
        import json
        
        returncode, stdout, stderr = await self._run_command("addr", "show", use_json=True)
        
        if returncode != 0:
            return []
        
        try:
            interfaces = json.loads(stdout)
            result = []
            
            for iface in interfaces:
                info = {
                    "name": iface.get("ifname"),
                    "index": iface.get("ifindex"),
                    "state": iface.get("operstate", "unknown"),
                    "mtu": iface.get("mtu"),
                    "mac": iface.get("address"),
                    "type": iface.get("link_type"),
                    "flags": iface.get("flags", []),
                    "ipv4": [],
                    "ipv6": []
                }
                
                for addr_info in iface.get("addr_info", []):
                    addr_data = {
                        "address": addr_info.get("local"),
                        "prefix": addr_info.get("prefixlen"),
                        "broadcast": addr_info.get("broadcast"),
                        "scope": addr_info.get("scope")
                    }
                    
                    if addr_info.get("family") == "inet":
                        info["ipv4"].append(addr_data)
                    elif addr_info.get("family") == "inet6":
                        info["ipv6"].append(addr_data)
                
                result.append(info)
            
            return result
        except json.JSONDecodeError:
            return []
    
    async def get_routes(self, table: str = "main") -> List[Dict[str, Any]]:
        """Get routing table"""
        import json
        
        returncode, stdout, stderr = await self._run_command(
            "route", "show", "table", table, use_json=True
        )
        
        if returncode != 0:
            return []
        
        try:
            routes = json.loads(stdout)
            result = []
            
            for route in routes:
                info = {
                    "id": f"{route.get('dst', 'default')}@{route.get('dev', '')}",
                    "destination": route.get("dst", "default"),
                    "gateway": route.get("gateway"),
                    "device": route.get("dev"),
                    "protocol": route.get("protocol"),
                    "scope": route.get("scope"),
                    "metric": route.get("metric"),
                    "type": route.get("type", "unicast"),
                    "table": table,
                    "prefsrc": route.get("prefsrc"),
                    "flags": route.get("flags", [])
                }
                result.append(info)
            
            return result
        except json.JSONDecodeError:
            return []
    
    async def get_all_routes(self) -> List[Dict[str, Any]]:
        """Get routes from all tables"""
        import json
        
        all_routes = []
        
        # Get routes from all tables
        returncode, stdout, stderr = await self._run_command(
            "route", "show", "table", "all", use_json=True
        )
        
        if returncode == 0:
            try:
                routes = json.loads(stdout)
                for route in routes:
                    info = {
                        "id": f"{route.get('dst', 'default')}@{route.get('dev', '')}@{route.get('table', 'main')}",
                        "destination": route.get("dst", "default"),
                        "gateway": route.get("gateway"),
                        "device": route.get("dev"),
                        "protocol": route.get("protocol"),
                        "scope": route.get("scope"),
                        "metric": route.get("metric"),
                        "type": route.get("type", "unicast"),
                        "table": route.get("table", "main"),
                        "prefsrc": route.get("prefsrc"),
                        "flags": route.get("flags", [])
                    }
                    all_routes.append(info)
            except json.JSONDecodeError:
                pass
        
        return all_routes
    
    async def get_rules(self) -> List[Dict[str, Any]]:
        """Get policy routing rules (ip rule)"""
        import json
        
        returncode, stdout, stderr = await self._run_command("rule", "show", use_json=True)
        
        if returncode != 0:
            return []
        
        try:
            rules = json.loads(stdout)
            result = []
            
            for rule in rules:
                info = {
                    "id": str(rule.get("priority", 0)),
                    "priority": rule.get("priority"),
                    "src": rule.get("src"),
                    "dst": rule.get("dst"),
                    "table": rule.get("table"),
                    "fwmark": rule.get("fwmark"),
                    "action": rule.get("action", "lookup")
                }
                result.append(info)
            
            return result
        except json.JSONDecodeError:
            return []
    
    async def add_route(self, route: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new route
        
        Args:
            route: Dictionary with keys:
                - destination: destination network (e.g., "10.0.0.0/8" or "default")
                - gateway: gateway IP (optional)
                - device: interface name (optional)
                - metric: route metric (optional)
                - table: routing table (optional, default: main)
                - type: route type (optional)
        """
        args = ["route", "add"]
        
        destination = route.get("destination")
        if not destination:
            return {"success": False, "error": "Destination is required"}
        
        args.append(destination)
        
        gateway = route.get("gateway")
        if gateway:
            args.extend(["via", gateway])
        
        device = route.get("device")
        if device:
            args.extend(["dev", device])
        
        metric = route.get("metric")
        if metric:
            args.extend(["metric", str(metric)])
        
        table = route.get("table")
        if table and table != "main":
            args.extend(["table", table])
        
        route_type = route.get("type")
        if route_type:
            args.insert(2, route_type)  # Insert after "add"
        
        returncode, stdout, stderr = await self._run_command(*args)
        
        if returncode == 0:
            return {"success": True, "message": "Route added successfully"}
        else:
            return {"success": False, "error": stderr.strip() or stdout.strip()}
    
    async def delete_route(self, route: Dict[str, Any]) -> bool:
        """Delete a route
        
        Args:
            route: Dictionary with keys matching the route to delete
        """
        args = ["route", "del"]
        
        destination = route.get("destination")
        if not destination:
            return False
        
        args.append(destination)
        
        gateway = route.get("gateway")
        if gateway:
            args.extend(["via", gateway])
        
        device = route.get("device")
        if device:
            args.extend(["dev", device])
        
        table = route.get("table")
        if table and table != "main":
            args.extend(["table", table])
        
        returncode, stdout, stderr = await self._run_command(*args)
        
        return returncode == 0
    
    async def add_rule(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        """Add a policy routing rule
        
        Args:
            rule: Dictionary with keys:
                - priority: rule priority
                - from: source address/network
                - to: destination address/network
                - table: routing table to use
                - fwmark: firewall mark
        """
        args = ["rule", "add"]
        
        priority = rule.get("priority")
        if priority:
            args.extend(["priority", str(priority)])
        
        from_addr = rule.get("from")
        if from_addr:
            args.extend(["from", from_addr])
        
        to_addr = rule.get("to")
        if to_addr:
            args.extend(["to", to_addr])
        
        fwmark = rule.get("fwmark")
        if fwmark:
            args.extend(["fwmark", str(fwmark)])
        
        table = rule.get("table")
        if table:
            args.extend(["table", table])
        
        returncode, stdout, stderr = await self._run_command(*args)
        
        if returncode == 0:
            return {"success": True, "message": "Rule added successfully"}
        else:
            return {"success": False, "error": stderr.strip() or stdout.strip()}
    
    async def delete_rule(self, rule: Dict[str, Any]) -> bool:
        """Delete a policy routing rule"""
        args = ["rule", "del"]
        
        priority = rule.get("priority")
        if priority:
            args.extend(["priority", str(priority)])
        
        from_addr = rule.get("from")
        if from_addr:
            args.extend(["from", from_addr])
        
        to_addr = rule.get("to")
        if to_addr:
            args.extend(["to", to_addr])
        
        table = rule.get("table")
        if table:
            args.extend(["table", table])
        
        returncode, stdout, stderr = await self._run_command(*args)
        
        return returncode == 0
    
    async def get_arp_table(self) -> List[Dict[str, Any]]:
        """Get ARP table"""
        import json
        
        returncode, stdout, stderr = await self._run_command("neigh", "show", use_json=True)
        
        if returncode != 0:
            return []
        
        try:
            neighbors = json.loads(stdout)
            result = []
            
            for neigh in neighbors:
                info = {
                    "ip": neigh.get("dst"),
                    "mac": neigh.get("lladdr"),
                    "device": neigh.get("dev"),
                    "state": neigh.get("state", [])
                }
                result.append(info)
            
            return result
        except json.JSONDecodeError:
            return []
    
    async def get_link_stats(self, interface: str) -> Dict[str, Any]:
        """Get interface statistics"""
        import json
        
        returncode, stdout, stderr = await self._run_command(
            "-s", "link", "show", interface, use_json=True
        )
        
        if returncode != 0:
            return {}
        
        try:
            data = json.loads(stdout)
            if data:
                return data[0].get("stats64", data[0].get("stats", {}))
            return {}
        except json.JSONDecodeError:
            return {}

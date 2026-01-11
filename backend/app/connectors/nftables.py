"""
nftables Connector
"""

import asyncio
import json
import re
import shutil
from typing import List, Dict, Any, Optional

from app.connectors.base import BaseFirewallConnector, ConnectorInfo, ConnectorStatus


class NftablesConnector(BaseFirewallConnector):
    """Connector for nftables (modern replacement for iptables)"""
    
    name = "nftables"
    type = "firewall"
    
    def __init__(self):
        self.nft_path = shutil.which("nft")
    
    async def _run_command(self, *args, use_json: bool = False) -> tuple[int, str, str]:
        """Run an nft command"""
        cmd = ["sudo", self.nft_path]
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
        """Check if nftables is available"""
        if not self.nft_path:
            return ConnectorInfo(
                name=self.name,
                type=self.type,
                status=ConnectorStatus.UNAVAILABLE,
                message="nft not found in PATH"
            )
        
        try:
            returncode, stdout, stderr = await self._run_command("--version")
            if returncode == 0:
                version_match = re.search(r'nftables v(\d+\.\d+\.\d+)', stdout)
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
        """Get nftables status"""
        returncode, stdout, stderr = await self._run_command("list", "ruleset", use_json=True)
        
        if returncode != 0:
            return {"error": stderr, "available": False}
        
        try:
            ruleset = json.loads(stdout)
            tables = []
            
            for item in ruleset.get("nftables", []):
                if "table" in item:
                    tables.append(item["table"])
            
            return {
                "available": True,
                "tables": tables,
                "table_count": len(tables)
            }
        except json.JSONDecodeError:
            return {"error": "Failed to parse nftables output", "available": True}
    
    async def get_rules(self) -> List[Dict[str, Any]]:
        """Get all nftables rules"""
        returncode, stdout, stderr = await self._run_command("list", "ruleset", use_json=True)
        
        if returncode != 0:
            return []
        
        try:
            ruleset = json.loads(stdout)
            rules = []
            rule_id = 0
            
            for item in ruleset.get("nftables", []):
                if "rule" in item:
                    rule = item["rule"]
                    rule["id"] = str(rule_id)
                    rules.append(rule)
                    rule_id += 1
            
            return rules
        except json.JSONDecodeError:
            return []
    
    async def get_tables(self) -> List[Dict[str, Any]]:
        """Get all tables"""
        returncode, stdout, stderr = await self._run_command("list", "tables", use_json=True)
        
        if returncode != 0:
            return []
        
        try:
            result = json.loads(stdout)
            tables = []
            for item in result.get("nftables", []):
                if "table" in item:
                    tables.append(item["table"])
            return tables
        except json.JSONDecodeError:
            return []
    
    async def get_chains(self, table_family: str, table_name: str) -> List[Dict[str, Any]]:
        """Get all chains in a table"""
        returncode, stdout, stderr = await self._run_command(
            "list", "chains", table_family, table_name, use_json=True
        )
        
        if returncode != 0:
            return []
        
        try:
            result = json.loads(stdout)
            chains = []
            for item in result.get("nftables", []):
                if "chain" in item:
                    chains.append(item["chain"])
            return chains
        except json.JSONDecodeError:
            return []
    
    async def add_rule(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        """Add an nftables rule
        
        Args:
            rule: Dictionary with keys:
                - family: ip, ip6, inet, arp, bridge, netdev
                - table: table name
                - chain: chain name
                - rule: rule expression string
                - position: handle to insert after (optional)
        """
        family = rule.get("family", "inet")
        table = rule.get("table")
        chain = rule.get("chain")
        rule_expr = rule.get("rule")
        position = rule.get("position")
        
        if not all([table, chain, rule_expr]):
            return {"success": False, "error": "Missing required fields: table, chain, rule"}
        
        cmd = f"add rule {family} {table} {chain} {rule_expr}"
        if position:
            cmd = f"insert rule {family} {table} {chain} position {position} {rule_expr}"
        
        returncode, stdout, stderr = await self._run_command(cmd)
        
        if returncode == 0:
            return {"success": True, "message": "Rule added successfully"}
        else:
            return {"success": False, "error": stderr.strip() or stdout.strip()}
    
    async def delete_rule(self, rule_id: str) -> bool:
        """Delete an nftables rule by handle
        
        rule_id format: family:table:chain:handle
        """
        parts = rule_id.split(":")
        if len(parts) != 4:
            return False
        
        family, table, chain, handle = parts
        
        returncode, _, _ = await self._run_command(
            "delete", "rule", family, table, chain, "handle", handle
        )
        
        return returncode == 0
    
    async def add_table(self, family: str, name: str) -> Dict[str, Any]:
        """Create a new table"""
        returncode, stdout, stderr = await self._run_command(
            "add", "table", family, name
        )
        
        if returncode == 0:
            return {"success": True, "message": f"Table {name} created"}
        else:
            return {"success": False, "error": stderr.strip()}
    
    async def add_chain(self, family: str, table: str, chain: str, 
                        chain_type: Optional[str] = None, hook: Optional[str] = None, 
                        priority: Optional[int] = None, policy: Optional[str] = None) -> Dict[str, Any]:
        """Create a new chain"""
        
        if chain_type and hook and priority is not None:
            # Base chain
            cmd = f"add chain {family} {table} {chain} {{ type {chain_type} hook {hook} priority {priority};"
            if policy:
                cmd += f" policy {policy};"
            cmd += " }"
        else:
            # Regular chain
            cmd = f"add chain {family} {table} {chain}"
        
        returncode, stdout, stderr = await self._run_command(cmd)
        
        if returncode == 0:
            return {"success": True, "message": f"Chain {chain} created"}
        else:
            return {"success": False, "error": stderr.strip()}
    
    async def enable(self) -> bool:
        """Enable nftables service"""
        process = await asyncio.create_subprocess_exec(
            "sudo", "systemctl", "start", "nftables",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
        return process.returncode == 0
    
    async def disable(self) -> bool:
        """Disable nftables (flush all rules)"""
        returncode, _, _ = await self._run_command("flush", "ruleset")
        return returncode == 0
    
    async def save_rules(self, filepath: str = "/etc/nftables.conf") -> bool:
        """Save current ruleset to file"""
        returncode, stdout, stderr = await self._run_command("list", "ruleset")
        
        if returncode != 0:
            return False
        
        try:
            process = await asyncio.create_subprocess_shell(
                f"echo '{stdout}' | sudo tee {filepath}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            return process.returncode == 0
        except Exception:
            return False
    
    async def load_rules(self, filepath: str = "/etc/nftables.conf") -> bool:
        """Load ruleset from file"""
        returncode, _, _ = await self._run_command("-f", filepath)
        return returncode == 0

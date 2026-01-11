"""
iptables Connector
"""

import asyncio
import re
import shutil
from typing import List, Dict, Any, Optional

from app.connectors.base import BaseFirewallConnector, ConnectorInfo, ConnectorStatus


class IptablesConnector(BaseFirewallConnector):
    """Connector for iptables"""
    
    name = "iptables"
    type = "firewall"
    
    TABLES = ["filter", "nat", "mangle", "raw", "security"]
    CHAINS = {
        "filter": ["INPUT", "FORWARD", "OUTPUT"],
        "nat": ["PREROUTING", "INPUT", "OUTPUT", "POSTROUTING"],
        "mangle": ["PREROUTING", "INPUT", "FORWARD", "OUTPUT", "POSTROUTING"],
        "raw": ["PREROUTING", "OUTPUT"],
        "security": ["INPUT", "FORWARD", "OUTPUT"]
    }
    
    def __init__(self):
        self.iptables_path = shutil.which("iptables")
        self.iptables_save_path = shutil.which("iptables-save")
        self.iptables_restore_path = shutil.which("iptables-restore")
    
    async def _run_command(self, *args, use_sudo: bool = True) -> tuple[int, str, str]:
        """Run an iptables command"""
        cmd = []
        if use_sudo:
            cmd.append("sudo")
        cmd.append(self.iptables_path)
        cmd.extend(args)
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        return process.returncode or 0, stdout.decode(), stderr.decode()
    
    async def check_availability(self) -> ConnectorInfo:
        """Check if iptables is available"""
        if not self.iptables_path:
            return ConnectorInfo(
                name=self.name,
                type=self.type,
                status=ConnectorStatus.UNAVAILABLE,
                message="iptables not found in PATH"
            )
        
        try:
            returncode, stdout, stderr = await self._run_command("--version")
            if returncode == 0:
                version_match = re.search(r'v(\d+\.\d+\.\d+)', stdout)
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
        """Get iptables status"""
        status = {
            "available": self.iptables_path is not None,
            "tables": {}
        }
        
        for table in self.TABLES:
            returncode, stdout, stderr = await self._run_command("-t", table, "-L", "-n", "--line-numbers")
            if returncode == 0:
                chains = self._parse_chains(stdout)
                status["tables"][table] = {
                    "chains": chains,
                    "rule_count": sum(len(c.get("rules", [])) for c in chains.values())
                }
        
        return status
    
    def _parse_chains(self, output: str) -> Dict[str, Any]:
        """Parse iptables -L output into chains and rules"""
        chains = {}
        current_chain = None
        
        for line in output.strip().split('\n'):
            # Chain header: Chain INPUT (policy ACCEPT)
            chain_match = re.match(r'Chain (\w+) \(policy (\w+)', line)
            if chain_match:
                current_chain = chain_match.group(1)
                chains[current_chain] = {
                    "policy": chain_match.group(2),
                    "rules": []
                }
                continue
            
            # Skip column headers
            if line.startswith("num") or line.startswith("target") or not line.strip():
                continue
            
            # Parse rule
            if current_chain and line.strip():
                parts = line.split()
                if len(parts) >= 4:
                    rule = {
                        "num": parts[0] if parts[0].isdigit() else None,
                        "target": parts[1] if not parts[0].isdigit() else parts[1],
                        "protocol": parts[2] if not parts[0].isdigit() else parts[2],
                        "opt": parts[3] if not parts[0].isdigit() else parts[3],
                        "source": parts[4] if len(parts) > 4 else "0.0.0.0/0",
                        "destination": parts[5] if len(parts) > 5 else "0.0.0.0/0",
                        "extra": " ".join(parts[6:]) if len(parts) > 6 else ""
                    }
                    if parts[0].isdigit():
                        rule["num"] = parts[0]
                        rule["target"] = parts[1]
                        rule["protocol"] = parts[2]
                        rule["opt"] = parts[3]
                        rule["source"] = parts[4] if len(parts) > 4 else "0.0.0.0/0"
                        rule["destination"] = parts[5] if len(parts) > 5 else "0.0.0.0/0"
                        rule["extra"] = " ".join(parts[6:]) if len(parts) > 6 else ""
                    
                    chains[current_chain]["rules"].append(rule)
        
        return chains
    
    async def get_rules(self, table: str = "filter") -> List[Dict[str, Any]]:
        """Get all rules for a table"""
        returncode, stdout, stderr = await self._run_command(
            "-t", table, "-L", "-n", "--line-numbers", "-v"
        )
        
        if returncode != 0:
            return []
        
        rules = []
        chains = self._parse_chains(stdout)
        
        for chain_name, chain_data in chains.items():
            for rule in chain_data.get("rules", []):
                rule["chain"] = chain_name
                rule["table"] = table
                rule["id"] = f"{table}:{chain_name}:{rule.get('num', 0)}"
                rules.append(rule)
        
        return rules
    
    async def add_rule(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        """Add an iptables rule
        
        Args:
            rule: Dictionary with keys:
                - table: filter, nat, mangle, raw, security (default: filter)
                - chain: INPUT, OUTPUT, FORWARD, etc.
                - target: ACCEPT, DROP, REJECT, LOG, etc.
                - protocol: tcp, udp, icmp, all
                - source: source IP/network
                - destination: destination IP/network
                - dport: destination port
                - sport: source port
                - in_interface: input interface
                - out_interface: output interface
                - position: insert at position (optional)
        """
        args = []
        
        table = rule.get("table", "filter")
        chain = rule.get("chain", "INPUT")
        position = rule.get("position")
        
        args.extend(["-t", table])
        
        if position:
            args.extend(["-I", chain, str(position)])
        else:
            args.extend(["-A", chain])
        
        # Protocol
        protocol = rule.get("protocol")
        if protocol and protocol != "all":
            args.extend(["-p", protocol])
        
        # Source
        source = rule.get("source")
        if source and source != "0.0.0.0/0":
            args.extend(["-s", source])
        
        # Destination
        destination = rule.get("destination")
        if destination and destination != "0.0.0.0/0":
            args.extend(["-d", destination])
        
        # Interfaces
        in_interface = rule.get("in_interface")
        if in_interface:
            args.extend(["-i", in_interface])
        
        out_interface = rule.get("out_interface")
        if out_interface:
            args.extend(["-o", out_interface])
        
        # Ports (require protocol to be tcp or udp)
        dport = rule.get("dport")
        if dport:
            args.extend(["--dport", str(dport)])
        
        sport = rule.get("sport")
        if sport:
            args.extend(["--sport", str(sport)])
        
        # Target
        target = rule.get("target", "ACCEPT")
        args.extend(["-j", target])
        
        # Execute
        returncode, stdout, stderr = await self._run_command(*args)
        
        if returncode == 0:
            return {"success": True, "message": "Rule added successfully"}
        else:
            return {"success": False, "error": stderr.strip() or stdout.strip()}
    
    async def delete_rule(self, rule_id: str) -> bool:
        """Delete an iptables rule by ID (format: table:chain:num)"""
        parts = rule_id.split(":")
        if len(parts) != 3:
            return False
        
        table, chain, num = parts
        
        returncode, stdout, stderr = await self._run_command(
            "-t", table, "-D", chain, num
        )
        
        return returncode == 0
    
    async def enable(self) -> bool:
        """Not applicable for iptables"""
        return True
    
    async def disable(self) -> bool:
        """Flush all iptables rules (essentially disabling)"""
        success = True
        for table in self.TABLES:
            returncode, _, _ = await self._run_command("-t", table, "-F")
            if returncode != 0:
                success = False
        return success
    
    async def save_rules(self, filepath: str = "/etc/iptables.rules") -> bool:
        """Save current rules to file"""
        if not self.iptables_save_path:
            return False
        
        process = await asyncio.create_subprocess_shell(
            f"sudo {self.iptables_save_path} > {filepath}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
        return process.returncode == 0
    
    async def restore_rules(self, filepath: str = "/etc/iptables.rules") -> bool:
        """Restore rules from file"""
        if not self.iptables_restore_path:
            return False
        
        process = await asyncio.create_subprocess_shell(
            f"sudo {self.iptables_restore_path} < {filepath}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
        return process.returncode == 0
    
    async def set_policy(self, chain: str, policy: str, table: str = "filter") -> bool:
        """Set default policy for a chain"""
        returncode, _, _ = await self._run_command(
            "-t", table, "-P", chain, policy.upper()
        )
        return returncode == 0

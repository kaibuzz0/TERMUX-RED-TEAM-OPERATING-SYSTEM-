#!/usr/bin/env python3
"""
HIVE GATEWAY BRIDGE
HSL: FIRE | PATH: /root/hive-swarm/gateway_bridge.py
ROLE: Bridge between Hermes Gateway and Hive Swarm

Connects messaging platforms (Telegram, Discord, etc.) to the
Hive Swarm orchestration system for bidirectional communication.
"""

import sys
import json
import asyncio
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

HIVE_ROOT = Path("/root/hive-swarm")
REGISTRY = HIVE_ROOT / ".swarm/registry.json"
BRIDGE_LOG = HIVE_ROOT / "logs/gateway_bridge.log"

# HIVE SYMBOLS
SYM = {
    'start': '▶',
    'end': '◀', 
    'hive': '🐝',
    'swarm': '🌐',
    'msg': '💬',
    'gateway': '📡',
    'sync': '♻',
    'alert': '🔔',
    'div': '═'
}

class HiveGatewayBridge:
    """Bridge between Hermes Gateway and Hive Swarm"""
    
    def __init__(self):
        self.hive_root = HIVE_ROOT
        self.registry_path = REGISTRY
        self.connected = False
        self.platforms = []
        
    def status(self) -> Dict:
        """Get bridge status"""
        # Check gateway
        result = subprocess.run(
            ["hermes", "gateway", "status"],
            capture_output=True, text=True, timeout=5
        )
        gateway_running = "✓ Gateway is running" in result.stdout
        
        # Check registry
        registry_status = "present" if self.registry_path.exists() else "missing"
        
        # Check swarm agents
        agents = []
        if self.registry_path.exists():
            try:
                registry = json.loads(self.registry_path.read_text())
                agents = list(registry.get("agents", {}).keys())
            except:
                pass
        
        return {
            "gateway_running": gateway_running,
            "registry_status": registry_status,
            "swarm_agents": agents,
            "hive_root": str(self.hive_root),
            "timestamp": datetime.now().isoformat()
        }
    
    def send_to_swarm(self, message: str, sender: str, platform: str) -> str:
        """Route incoming message to Hive Swarm"""
        # Log the message
        self._log(f"[{platform}] {sender}: {message[:100]}...")
        
        # Parse for Hive commands
        if message.startswith("/hive") or message.startswith("!hive"):
            return self._handle_hive_command(message, sender)
        
        # Check if it's a swarm task request
        if any(kw in message.lower() for kw in ["delegate", "task", "build", "analyze"]):
            return self._create_swarm_task(message, sender, platform)
        
        # Default response
        return f"{SYM['hive']} Message received. Use /hive for commands."
    
    def _handle_hive_command(self, message: str, sender: str) -> str:
        """Handle /hive commands"""
        parts = message.split()
        cmd = parts[1] if len(parts) > 1 else "help"
        
        commands = {
            "status": self._cmd_status,
            "agents": self._cmd_agents,
            "tasks": self._cmd_tasks,
            "help": self._cmd_help,
            "sync": self._cmd_sync,
        }
        
        handler = commands.get(cmd, self._cmd_help)
        return handler(sender)
    
    def _cmd_status(self, sender: str) -> str:
        """Get Hive status"""
        status = self.status()
        
        lines = [
            f"{SYM['hive']} HIVE SWARM STATUS",
            f"{SYM['div']*20}",
            f"Gateway: {'✓ Running' if status['gateway_running'] else '✗ Stopped'}",
            f"Registry: {status['registry_status']}",
            f"Agents: {', '.join(status['swarm_agents']) or 'None'}",
            f"Time: {status['timestamp'][:19]}"
        ]
        
        return '\n'.join(lines)
    
    def _cmd_agents(self, sender: str) -> str:
        """List swarm agents"""
        if not self.registry_path.exists():
            return f"{SYM['alert']} Registry not found. Run hive-swarm.py first."
        
        try:
            registry = json.loads(self.registry_path.read_text())
            agents = registry.get("agents", {})
            
            lines = [f"{SYM['swarm']} SWARM AGENTS", f"{SYM['div']*20}"]
            for agent_id, info in agents.items():
                status = info.get("status", "unknown")
                caps = ", ".join(info.get("capabilities", [])[:3])
                lines.append(f"• {agent_id}: {status} [{caps}]")
            
            return '\n'.join(lines)
        except Exception as e:
            return f"{SYM['alert']} Error: {e}"
    
    def _cmd_tasks(self, sender: str) -> str:
        """List active tasks"""
        if not self.registry_path.exists():
            return f"{SYM['alert']} Registry not found."
        
        try:
            registry = json.loads(self.registry_path.read_text())
            tasks = registry.get("tasks", {})
            
            active = [t for t in tasks.values() if t.get("status") == "assigned"]
            
            lines = [f"{SYM['msg']} ACTIVE TASKS: {len(active)}", f"{SYM['div']*20}"]
            for task in active[:5]:
                desc = task.get("description", "Unknown")[:40]
                assignee = task.get("assigned_to", "?")
                lines.append(f"• [{assignee}] {desc}...")
            
            return '\n'.join(lines)
        except Exception as e:
            return f"{SYM['alert']} Error: {e}"
    
    def _cmd_sync(self, sender: str) -> str:
        """Sync to offline storage"""
        offline = Path("/sdcard/Hermès.Swarm/")
        if not offline.exists():
            return f"{SYM['alert']} Offline storage not found at /sdcard/Hermès.Swarm/"
        
        # Run sync via hive CLI
        result = subprocess.run(
            [sys.executable, str(HIVE_ROOT / "integration/hive_cli.py"), "sync"],
            capture_output=True, text=True, timeout=30
        )
        
        return f"{SYM['sync']} Sync complete\n{result.stdout[:200]}"
    
    def _cmd_help(self, sender: str) -> str:
        """Show help"""
        return f"""{SYM['hive']} HIVE COMMANDS
{SYM['div']*20}
/hive status    - System status
/hive agents    - List swarm agents  
/hive tasks     - Active tasks
/hive sync      - Sync to offline
/hive help      - This message

Direct messages starting with:
"delegate..." or "build..." or "analyze..."
will create Swarm tasks automatically."""
    
    def _create_swarm_task(self, message: str, sender: str, platform: str) -> str:
        """Create a task in the swarm"""
        # Import swarm integration
        sys.path.insert(0, str(HIVE_ROOT))
        try:
            from hive_swarm_integration import HiveSwarmIntegration
            
            swarm = HiveSwarmIntegration()
            task_id = swarm.delegate_task(
                description=message,
                requires_verification=True
            )
            
            return f"{SYM['swarm']} Task created: {task_id[:8]}...\nDelegated to toolsmith for execution."
        except Exception as e:
            return f"{SYM['alert']} Could not create task: {e}"
    
    def _log(self, message: str):
        """Log to bridge log"""
        BRIDGE_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(BRIDGE_LOG, 'a') as f:
            f.write(f"[{datetime.now().isoformat()}] {message}\n")
    
    def notify(self, message: str, channel: str = "telegram"):
        """Send notification through gateway"""
        # This would integrate with hermes messaging
        # For now, we log it
        self._log(f"[NOTIFY:{channel}] {message}")
        print(f"{SYM['alert']} {message}")


def main():
    """CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Hive Gateway Bridge')
    parser.add_argument('command', choices=['status', 'test', 'notify', 'serve'])
    parser.add_argument('--message', '-m', help='Message for notify')
    parser.add_argument('--sender', '-s', default='cli', help='Sender ID')
    parser.add_argument('--platform', '-p', default='cli', help='Platform')
    
    args = parser.parse_args()
    
    bridge = HiveGatewayBridge()
    
    if args.command == 'status':
        status = bridge.status()
        print(json.dumps(status, indent=2))
    
    elif args.command == 'test':
        # Test message handling
        response = bridge.send_to_swarm("/hive status", args.sender, args.platform)
        print(response)
    
    elif args.command == 'notify':
        if args.message:
            bridge.notify(args.message)
        else:
            print("Usage: gateway_bridge.py notify --message 'text'")
    
    elif args.command == 'serve':
        print(f"{SYM['gateway']} Gateway Bridge serving...")
        print("Press Ctrl+C to stop")
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n{SYM['end']} Stopped")


if __name__ == "__main__":
    main()

# --- HIVE FOOTER ---
# ::SealConfirmed::
# ΩΩΩ
# --- END FOOTER ---

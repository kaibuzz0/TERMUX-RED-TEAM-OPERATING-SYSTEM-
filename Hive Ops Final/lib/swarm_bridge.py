#!/usr/bin/env python3
"""
HIVE OPS FINAL - Swarm Integration Module
Bridges hive command with swarm-core orchestration
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

HIVE_SWARM = Path('/root/hive-swarm')
HIVE_HOME = Path('/root/hive')

class SwarmBridge:
    """Bridge between Hive Ops Final and Swarm Core."""
    
    VERSION = "5.0"
    
    def __init__(self):
        self.registry_file = HIVE_HOME / 'state' / 'swarm_registry.json'
        self.agents_dir = HIVE_SWARM / 'swarm-core' / 'agents'
        self._ensure_structure()
    
    def _ensure_structure(self):
        """Ensure swarm structure exists."""
        (HIVE_HOME / 'state').mkdir(parents=True, exist_ok=True)
        (HIVE_HOME / 'logs').mkdir(parents=True, exist_ok=True)
    
    def get_status(self) -> Dict:
        """Get unified swarm status."""
        status = {
            'version': self.VERSION,
            'timestamp': datetime.now().isoformat(),
            'agents': {},
            'registry': None,
            'integration': 'active'
        }
        
        # Check agents
        for agent_file in ['architect_agent.py', 'assistant_agent.py', 'swarm_orchestrator.py']:
            agent_path = self.agents_dir / agent_file if 'agent' in agent_file else HIVE_SWARM / 'swarm-core' / agent_file
            status['agents'][agent_file.replace('.py', '')] = {
                'exists': agent_path.exists(),
                'path': str(agent_path)
            }
        
        # Check registry
        if self.registry_file.exists():
            try:
                with open(self.registry_file) as f:
                    status['registry'] = json.load(f)
            except:
                status['registry'] = {'error': 'corrupted'}
        
        return status
    
    def list_agents(self) -> List[str]:
        """List available agents."""
        agents = []
        if self.agents_dir.exists():
            for f in self.agents_dir.glob('*_agent.py'):
                agents.append(f.stem.replace('_agent', ''))
        return agents
    
    def spawn_task(self, agent: str, task: str, context: Optional[Dict] = None) -> Tuple[bool, str]:
        """Spawn a task through an agent."""
        agent_file = self.agents_dir / f"{agent}_agent.py"
        
        if not agent_file.exists():
            # Try swarm orchestrator
            orch = HIVE_SWARM / 'swarm-core' / 'swarm_orchestrator.py'
            if orch.exists():
                cmd = [sys.executable, str(orch), 'delegate', agent, task]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                return result.returncode == 0, result.stdout or result.stderr
            return False, f"Agent {agent} not found"
        
        # Direct agent execution
        cmd = [sys.executable, str(agent_file), task]
        if context:
            cmd.extend(['--context', json.dumps(context)])
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return result.returncode == 0, result.stdout or result.stderr
    
    def health_check(self) -> Tuple[bool, List[str]]:
        """Check swarm health."""
        issues = []
        
        # Check core files
        core_files = [
            HIVE_SWARM / 'swarm-core' / 'swarm_orchestrator.py',
            HIVE_SWARM / 'swarm-core' / 'hive_swarm_integration.py',
        ]
        
        for f in core_files:
            if not f.exists():
                issues.append(f"Missing: {f}")
        
        # Check agents
        if not self.agents_dir.exists():
            issues.append("Agents directory missing")
        
        return len(issues) == 0, issues
    
    def register_event(self, event_type: str, data: Dict):
        """Register event to swarm registry."""
        registry = {'events': [], 'version': self.VERSION}
        
        if self.registry_file.exists():
            try:
                with open(self.registry_file) as f:
                    registry = json.load(f)
            except:
                pass
        
        event = {
            'type': event_type,
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        
        registry['events'].append(event)
        # Keep last 100 events
        registry['events'] = registry['events'][-100:]
        
        with open(self.registry_file, 'w') as f:
            json.dump(registry, f, indent=2)
    
    def get_verification_chain(self) -> Dict:
        """Get current verification chain status."""
        return {
            'chain': [
                {'role': 'User', 'status': '✓'},
                {'role': 'Main AI', 'status': '✓'},
                {'role': 'Swarm', 'status': '✓'},
                {'role': 'Agent', 'status': 'active'},
                {'role': 'Architect Review', 'status': 'pending'},
                {'role': 'Assistant Verification', 'status': 'pending'},
                {'role': 'Delivery', 'status': 'pending'}
            ],
            'status': 'SWARM 🧠 ✓ ⚡ 🔧'
        }


def main():
    """CLI entry for swarm operations."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Hive Swarm Bridge')
    parser.add_argument('command', choices=['status', 'health', 'agents', 'spawn'])
    parser.add_argument('--agent', help='Agent name for spawn')
    parser.add_argument('--task', help='Task for spawn')
    
    args = parser.parse_args()
    
    bridge = SwarmBridge()
    
    if args.command == 'status':
        status = bridge.get_status()
        print(json.dumps(status, indent=2))
    
    elif args.command == 'health':
        ok, issues = bridge.health_check()
        print(f"Health: {'OK' if ok else 'FAIL'}")
        for issue in issues:
            print(f"  - {issue}")
        return 0 if ok else 1
    
    elif args.command == 'agents':
        agents = bridge.list_agents()
        print(f"Available agents: {', '.join(agents)}")
    
    elif args.command == 'spawn':
        if not args.agent or not args.task:
            print("Usage: --agent <name> --task <task>")
            return 1
        ok, result = bridge.spawn_task(args.agent, args.task)
        print(result)
        return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

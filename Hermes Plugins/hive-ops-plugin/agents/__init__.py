"""
HIVE AGENT DEFINITIONS
Agents that integrate with Hermes' delegate_task system
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from pathlib import Path
import subprocess
import json

@dataclass
class AgentCapability:
    """Agent capability specification."""
    name: str
    patterns: List[str]
    handler: str
    verification: bool
    priority: int

class HiveAgentRegistry:
    """
    Agent registry that maps to Hive Ops components.
    
    Each agent maps to a specific Hive DevAI component
    and can be invoked through Hermes' delegation system.
    """
    
    AGENTS = {
        'stealth_agent': AgentCapability(
            name='stealth_agent',
            patterns=['stego', 'hide', 'whitespace', 'obfuscate'],
            handler='hivedev',
            verification=True,
            priority=1
        ),
        'network_agent': AgentCapability(
            name='network_agent',
            patterns=['tor', 'proxy', 'socks', 'net', 'tunnel'],
            handler='hivedev-net',
            verification=True,
            priority=1
        ),
        'crypto_agent': AgentCapability(
            name='crypto_agent',
            patterns=['vault', 'encrypt', 'decrypt', 'cipher', 'e8'],
            handler='hivedev-vault',
            verification=True,
            priority=1
        ),
        'forensics_agent': AgentCapability(
            name='forensics_agent',
            patterns=['wipe', 'clean', 'sanitize', 'secure-delete', 'forensics'],
            handler='hivedev-forensics',
            verification=True,
            priority=1
        ),
        'integrity_agent': AgentCapability(
            name='integrity_agent',
            patterns=['verify', 'check', 'hash', 'tamper', 'integrity'],
            handler='hivedev-integrity',
            verification=True,
            priority=1
        ),
        'backup_agent': AgentCapability(
            name='backup_agent',
            patterns=['backup', 'restore', 'archive', 'exfil'],
            handler='hivedev-backup',
            verification=True,
            priority=1
        ),
        'spoofing_agent': AgentCapability(
            name='spoofing_agent',
            patterns=['spoof', 'mac', 'identity', 'fingerprint', 'hardware'],
            handler='hivedev-spoof',
            verification=True,
            priority=1
        ),
        'temporal_agent': AgentCapability(
            name='temporal_agent',
            patterns=['deadman', 'timelock', 'delay', 'timeout', 'temporal'],
            handler='hivedev-temporal',
            verification=True,
            priority=1
        ),
        'exfil_agent': AgentCapability(
            name='exfil_agent',
            patterns=['exfil', 'tunnel', 'dns', 'icmp', 'covert', 'channel'],
            handler='hivedev-exfil',
            verification=True,
            priority=1
        ),
        'duress_agent': AgentCapability(
            name='duress_agent',
            patterns=['duress', 'panic', 'self-destruct', 'kill-switch'],
            handler='hivedev-duress',
            verification=True,
            priority=0  # High priority - immediate execution
        ),
        'comms_agent': AgentCapability(
            name='comms_agent',
            patterns=['irc', 'covert', 'c2', 'channel', 'comms'],
            handler='hivedev-comms',
            verification=True,
            priority=1
        ),
        'volume_agent': AgentCapability(
            name='volume_agent',
            patterns=['volume', 'hidden', 'deniability', 'plausible'],
            handler='hivedev-volume',
            verification=True,
            priority=1
        ),
        'orchestrator': AgentCapability(
            name='orchestrator',
            patterns=['hive', 'swarm', 'orchestrate', 'delegate'],
            handler='swarm_orchestrator',
            verification=True,
            priority=0
        ),
    }
    
    def __init__(self):
        self.active_agents = set()
    
    def match_agent(self, task_description: str) -> Optional[str]:
        """Match task to appropriate agent."""
        desc_lower = task_description.lower()
        
        # Check each agent's patterns
        for agent_id, capability in self.AGENTS.items():
            if any(pattern in desc_lower for pattern in capability.patterns):
                return agent_id
        
        return None
    
    def get_agent_handler(self, agent_id: str) -> Optional[str]:
        """Get handler binary for agent."""
        agent = self.AGENTS.get(agent_id)
        if agent:
            return agent.handler
        return None
    
    def delegate_task(self, agent_id: str, task: str, context: Dict = None) -> Dict[str, Any]:
        """
        Delegate task to Hive agent.
        
        This is the main entry point from Hermes' delegate_task.
        """
        handler = self.get_agent_handler(agent_id)
        if not handler:
            return {
                'success': False,
                'error': f'Unknown agent: {agent_id}'
            }
        
        # Build command
        hive_path = Path(__file__).parent.parent.parent / 'Hive Ops DevAI' / 'bin'
        binary = hive_path / handler
        
        cmd = ['python3', str(binary)]
        
        # Parse task for subcommand
        if 'status' in task.lower():
            cmd.append('status')
        elif 'check' in task.lower():
            cmd.append('check')
        elif 'init' in task.lower() or 'create' in task.lower():
            cmd.append('init' if 'duress' in handler else 'create')
        elif 'verify' in task.lower():
            cmd.append('verify')
        else:
            cmd.append('status')
        
        # Execute
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'agent': agent_id,
                'handler': handler
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'agent': agent_id
            }
    
    def get_all_agents(self) -> List[Dict[str, Any]]:
        """Get list of all available agents."""
        return [
            {
                'id': aid,
                'name': cap.name,
                'patterns': cap.patterns,
                'handler': cap.handler,
                'priority': cap.priority
            }
            for aid, cap in self.AGENTS.items()
        ]
    
    def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """Check if agent is available."""
        agent = self.AGENTS.get(agent_id)
        if not agent:
            return {'exists': False}
        
        hive_path = Path(__file__).parent.parent.parent / 'Hive Ops DevAI' / 'bin'
        binary = hive_path / agent.handler
        
        return {
            'exists': binary.exists(),
            'path': str(binary),
            'handler': agent.handler,
            'patterns': agent.patterns
        }

# Export for Hermes
def create_agent_registry():
    """Factory for agent registry."""
    return HiveAgentRegistry()

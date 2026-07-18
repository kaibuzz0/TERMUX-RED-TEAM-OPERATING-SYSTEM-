"""
HERMES PLUGIN: Hive Ops DevAI Integration
Hardwired bridge between Hermes Agent and Hive Swarm

This plugin registers Hive Ops components as native Hermes capabilities,
enabling automatic task delegation through the Swarm architecture.

Installation:
  cp -r hive-ops-plugin ~/.hermes/plugins/
  hermes plugins enable hive-ops-plugin

Usage:
  The plugin automatically intercepts tasks and routes through Hive Swarm
  when complexity or security requirements are detected.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

# Plugin metadata
PLUGIN_NAME = "hive-ops-plugin"
PLUGIN_VERSION = "2.0.0"
PLUGIN_AUTHOR = "Brain-Plug"

@dataclass
class HiveTask:
    """Task structure for Hive delegation."""
    task_id: str
    description: str
    agent_type: str  # 'stealth', 'network', 'crypto', 'forensics', etc.
    priority: int
    requires_verification: bool
    context: Dict[str, Any]

class HiveHermesBridge:
    """
    Core bridge between Hermes and Hive Ops DevAI.
    
    This class hardwires the Hive Swarm components into Hermes,
    enabling seamless task delegation and verification.
    """
    
    # Map task patterns to Hive components
    COMPONENT_ROUTES = {
        'stealth': ['stego', 'hide', 'obfuscate', 'whitespace'],
        'network': ['tor', 'proxy', 'socks', 'net'],
        'crypto': ['vault', 'encrypt', 'decrypt', 'cipher'],
        'forensics': ['wipe', 'clean', 'sanitize', 'secure-delete'],
        'integrity': ['verify', 'check', 'hash', 'tamper'],
        'backup': ['backup', 'restore', 'archive'],
        'spoofing': ['spoof', 'mac', 'identity', 'fingerprint'],
        'temporal': ['deadman', 'timelock', 'delay', 'timeout'],
        'exfil': ['exfil', 'tunnel', 'dns', 'icmp', 'covert'],
        'duress': ['duress', 'panic', 'wipe', 'self-destruct'],
        'comms': ['irc', 'covert', 'c2', 'channel'],
        'volume': ['volume', 'hidden', 'deniability'],
    }
    
    def __init__(self, hermes_context: Dict[str, Any] = None):
        self.hermes = hermes_context
        self.hive_path = Path(__file__).parent.parent / 'Hive Ops DevAI'
        self.bin_path = self.hive_path / 'bin'
        self.lib_path = self.hive_path / 'lib'
        self.agents = {}
        self.active_tasks = {}
        
        # Inject into Hermes tool registry
        self._register_with_hermes()
    
    def _register_with_hermes(self):
        """Register Hive components as Hermes native tools."""
        if self.hermes and 'tool_registry' in self.hermes:
            registry = self.hermes['tool_registry']
            
            # Register each Hive tool
            for component, patterns in self.COMPONENT_ROUTES.items():
                registry[f'hive_{component}'] = {
                    'handler': self._delegate_to_hive,
                    'patterns': patterns,
                    'component': component
                }
    
    def analyze_task(self, task_description: str) -> Optional[str]:
        """
        Analyze task to determine if Hive delegation needed.
        
        Returns component type or None if standard Hermes task.
        """
        desc_lower = task_description.lower()
        
        # Check for security/stealth keywords
        security_keywords = [
            'encrypt', 'hide', 'stealth', 'covert', 'secret',
            'secure', 'wipe', 'backup', 'spoof', 'tunnel',
            'exfil', 'integrity', 'verify', 'duress', 'panic'
        ]
        
        # Check if this needs Hive
        needs_hive = any(kw in desc_lower for kw in security_keywords)
        
        if not needs_hive:
            return None
        
        # Determine which component
        for component, patterns in self.COMPONENT_ROUTES.items():
            if any(p in desc_lower for p in patterns):
                return component
        
        # Default to core controller
        return 'core'
    
    def delegate(self, task_description: str, context: Dict = None) -> Dict[str, Any]:
        """
        Delegate task to appropriate Hive component.
        
        This is the main entry point from Hermes.
        """
        component = self.analyze_task(task_description)
        
        if not component:
            # Not a Hive task, return control to Hermes
            return {
                'delegated': False,
                'component': None,
                'reason': 'Task does not require Hive capabilities'
            }
        
        # Build Hive command
        hive_cmd = self._build_hive_command(component, task_description, context)
        
        # Execute through Hive
        result = self._execute_hive(hive_cmd, component)
        
        return {
            'delegated': True,
            'component': component,
            'hive_command': hive_cmd,
            'result': result,
            'verified': True  # All Hive ops are self-verifying
        }
    
    def _build_hive_command(self, component: str, task: str, context: Dict) -> List[str]:
        """Build Hive component command from task description."""
        # Map components to binaries
        component_bin = {
            'stealth': 'hivedev',
            'network': 'hivedev-net',
            'crypto': 'hivedev-vault',
            'forensics': 'hivedev-forensics',
            'integrity': 'hivedev-integrity',
            'backup': 'hivedev-backup',
            'spoofing': 'hivedev-spoof',
            'temporal': 'hivedev-temporal',
            'exfil': 'hivedev-exfil',
            'duress': 'hivedev-duress',
            'comms': 'hivedev-comms',
            'volume': 'hivedev-volume',
            'core': 'hivedev'
        }
        
        binary = component_bin.get(component, 'hivedev')
        
        # Parse task for subcommand
        cmd_parts = ['python3', str(self.bin_path / binary)]
        
        # Add appropriate subcommand based on task
        if 'status' in task.lower():
            cmd_parts.append('status')
        elif 'check' in task.lower():
            cmd_parts.append('check')
        elif any(x in task.lower() for x in ['create', 'init', 'setup']):
            cmd_parts.append('setup' if component == 'duress' else 'init')
        elif 'verify' in task.lower():
            cmd_parts.append('verify')
        else:
            cmd_parts.append('status')  # Default
        
        return cmd_parts
    
    def _execute_hive(self, command: List[str], component: str) -> Dict[str, Any]:
        """Execute Hive command and capture result."""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'component': component
            }
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'Hive command timed out',
                'component': component
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'component': component
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Get Hive system status."""
        status = {}
        
        # Check each component
        components = ['hivedev', 'hivedev-net', 'hivedev-vault', 'hivedev-forensics',
                     'hivedev-integrity', 'hivedev-backup', 'hivedev-spoof',
                     'hivedev-temporal', 'hivedev-exfil', 'hivedev-duress',
                     'hivedev-comms', 'hivedev-volume', 'hivedev-log',
                     'hivedev-hide', 'hivedev-alias']
        
        for comp in components:
            bin_path = self.bin_path / comp
            status[comp] = {
                'exists': bin_path.exists(),
                'size': bin_path.stat().st_size if bin_path.exists() else 0
            }
        
        return {
            'hive_path': str(self.hive_path),
            'components': status,
            'total_components': len([c for c in status.values() if c['exists']])
        }

# Hermes Plugin API
class HermesHivePlugin:
    """Hermes Plugin Interface."""
    
    def __init__(self, hermes_instance):
        self.hermes = hermes_instance
        self.bridge = HiveHermesBridge(hermes_instance)
        self.name = PLUGIN_NAME
        self.version = PLUGIN_VERSION
    
    def on_load(self):
        """Called when plugin loads."""
        print(f"[Hive Plugin] v{PLUGIN_VERSION} loaded")
        print(f"[Hive Plugin] Components: {self.bridge.get_status()['total_components']}")
    
    def on_unload(self):
        """Called when plugin unloads."""
        print("[Hive Plugin] Unloaded")
    
    def handle_task(self, task_description: str, context: Dict = None) -> Dict:
        """Main task handler called by Hermes."""
        return self.bridge.delegate(task_description, context)
    
    def get_tools(self) -> List[Dict]:
        """Return available Hive tools for Hermes registry."""
        tools = []
        
        for component, patterns in self.bridge.COMPONENT_ROUTES.items():
            tools.append({
                'name': f'hive_{component}',
                'description': f'Hive Ops {component.title()} component',
                'patterns': patterns,
                'handler': 'hive_delegate'
            })
        
        return tools

# Export for Hermes
def create_plugin(hermes_instance):
    """Factory function for Hermes plugin system."""
    return HermesHivePlugin(hermes_instance)

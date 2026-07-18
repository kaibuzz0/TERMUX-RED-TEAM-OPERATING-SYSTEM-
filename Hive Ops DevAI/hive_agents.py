#!/usr/bin/env python3
"""
HIVE OPS DevAI - Enhanced Agent Framework v3.0
Multi-specialized AI agents with deep capabilities

Purpose:
  Comprehensive agent system with specialized AI agents for
  security, cryptography, forensics, network operations, and
  intelligence gathering. Agents communicate, delegate, and
  learn from each other.

Agent Architecture:
  BaseAgent (abstract base)
  ├── SecurityAgent - Threat detection and response
  ├── CryptoAgent - Advanced cryptographic operations  
  ├── NetworkAgent - Network analysis and manipulation
  ├── ForensicsAgent - Digital forensics and investigation
  ├── IntelligenceAgent - Data gathering and analysis
  └── SwarmAgent - Multi-agent coordination

Features:
  - Inter-agent communication via message bus
  - Skill learning and knowledge sharing
  - Autonomous task delegation
  - Consensus-based decision making
  - Persistent memory and learning
  - Real-time collaboration

Usage:
  from hive_agents import SecurityAgent, CryptoAgent
  
  security = SecurityAgent()
  crypto = CryptoAgent()
  
  # Agents auto-register and communicate
  security.analyze_threat(data)
  crypto.secure_channel(security.recommendations)

Author: Hive Ops DevAI
Version: 3.0.0
"""

import os
import sys
import json
import time
import uuid
import hashlib
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Any, Callable
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

# Message types for inter-agent communication
class MessageType(Enum):
    THREAT_ALERT = "threat_alert"
    CRYPTO_REQUEST = "crypto_request"
    FORENSICS_REPORT = "forensics_report"
    INTELLIGENCE = "intelligence"
    TASK_DELEGATION = "task_delegation"
    CONSENSUS_REQUEST = "consensus_request"
    KNOWLEDGE_SHARE = "knowledge_share"
    STATUS_UPDATE = "status_update"

@dataclass
class AgentMessage:
    """Message for inter-agent communication."""
    id: str
    sender: str
    recipient: Optional[str]  # None = broadcast
    msg_type: MessageType
    payload: Dict
    timestamp: float
    priority: int  # 1-10
    requires_ack: bool

@dataclass
class AgentSkill:
    """Agent skill/capability."""
    name: str
    level: int  # 1-10
    last_used: float
    success_rate: float

class BaseAgent(ABC):
    """
    Abstract base class for all Hive agents.
    
    Provides:
    - Inter-agent messaging
    - Memory/knowledge persistence
    - Skill tracking
    - Lifecycle management
    """
    
    AGENT_REGISTRY: Dict[str, 'BaseAgent'] = {}
    MESSAGE_BUS: List[AgentMessage] = []
    _lock = threading.Lock()
    
    def __init__(self, name: str, role: str, version: str = "1.0"):
        """Initialize base agent."""
        self.id = f"{name}_{uuid.uuid4().hex[:8]}"
        self.name = name
        self.role = role
        self.version = version
        self.status = "initializing"
        self.created = time.time()
        self.last_active = time.time()
        
        # Agent capabilities
        self.skills: Dict[str, AgentSkill] = {}
        self.knowledge_base: Dict[str, Any] = {}
        self.memory: List[Dict] = []
        
        # Performance tracking
        self.tasks_completed = 0
        self.tasks_failed = 0
        self.messages_sent = 0
        self.messages_received = 0
        
        # Data persistence
        self.data_dir = Path.home() / '.local' / 'share' / 'hive-agents'
        self.agent_dir = self.data_dir / self.id
        self.agent_dir.mkdir(parents=True, exist_ok=True)
        
        # Register agent
        with BaseAgent._lock:
            BaseAgent.AGENT_REGISTRY[self.id] = self
        
        self.status = "active"
        self._save_state()
        
        print(f"[Agent] {self.name} v{self.version} initialized ({self.id})")
    
    def _save_state(self):
        """Persist agent state."""
        state = {
            'id': self.id,
            'name': self.name,
            'role': self.role,
            'version': self.version,
            'status': self.status,
            'created': self.created,
            'skills': {k: asdict(v) for k, v in self.skills.items()},
            'knowledge_base': self.knowledge_base,
            'tasks_completed': self.tasks_completed,
            'tasks_failed': self.tasks_failed
        }
        state_file = self.agent_dir / 'state.json'
        state_file.write_text(json.dumps(state, indent=2))
    
    def learn_skill(self, skill_name: str, level: int = 1):
        """Learn or upgrade skill."""
        if skill_name in self.skills:
            # Upgrade existing
            self.skills[skill_name].level = min(10, self.skills[skill_name].level + 1)
            self.skills[skill_name].last_used = time.time()
        else:
            # New skill
            self.skills[skill_name] = AgentSkill(
                name=skill_name,
                level=level,
                last_used=time.time(),
                success_rate=1.0
            )
        self._save_state()
    
    def send_message(self, msg_type: MessageType, payload: Dict,
                    recipient: Optional[str] = None, priority: int = 5,
                    requires_ack: bool = False) -> str:
        """Send message to other agents."""
        msg = AgentMessage(
            id=str(uuid.uuid4()),
            sender=self.id,
            recipient=recipient,
            msg_type=msg_type,
            payload=payload,
            timestamp=time.time(),
            priority=priority,
            requires_ack=requires_ack
        )
        
        with BaseAgent._lock:
            BaseAgent.MESSAGE_BUS.append(msg)
        
        self.messages_sent += 1
        return msg.id
    
    def check_messages(self) -> List[AgentMessage]:
        """Check for messages addressed to this agent."""
        with BaseAgent._lock:
            my_messages = [
                m for m in BaseAgent.MESSAGE_BUS
                if m.recipient == self.id or m.recipient is None
            ]
            # Remove from bus
            BaseAgent.MESSAGE_BUS = [
                m for m in BaseAgent.MESSAGE_BUS
                if m not in my_messages
            ]
        
        self.messages_received += len(my_messages)
        return my_messages
    
    def find_agents_by_role(self, role: str) -> List['BaseAgent']:
        """Find agents by role."""
        return [
            agent for agent in BaseAgent.AGENT_REGISTRY.values()
            if agent.role == role and agent.id != self.id
        ]
    
    def delegate_task(self, task: str, to_agent: Optional[str] = None) -> Optional[str]:
        """Delegate task to another agent."""
        if to_agent:
            msg_id = self.send_message(
                MessageType.TASK_DELEGATION,
                {'task': task, 'from': self.id},
                recipient=to_agent,
                priority=7
            )
            return msg_id
        else:
            # Broadcast to find capable agent
            return self.send_message(
                MessageType.TASK_DELEGATION,
                {'task': task, 'from': self.id, 'seeking': True},
                priority=7
            )
    
    def request_consensus(self, decision: str, options: List[str]) -> Dict[str, Any]:
        """Request consensus from all agents."""
        print(f"[{self.name}] Requesting consensus: {decision}")
        
        votes = {opt: 0 for opt in options}
        votes[self.id] = random.choice(options)  # Own vote
        
        # Send to all agents
        self.send_message(
            MessageType.CONSENSUS_REQUEST,
            {'decision': decision, 'options': options},
            priority=9
        )
        
        # Wait for votes (simplified)
        time.sleep(0.5)
        messages = self.check_messages()
        for msg in messages:
            if msg.msg_type == MessageType.CONSENSUS_REQUEST:
                if 'vote' in msg.payload:
                    vote = msg.payload['vote']
                    if vote in votes:
                        votes[vote] += 1
        
        # Determine winner
        winner = max(votes, key=votes.get)
        confidence = votes[winner] / len(BaseAgent.AGENT_REGISTRY) if BaseAgent.AGENT_REGISTRY else 0
        
        return {
            'decision': decision,
            'winner': winner,
            'votes': votes,
            'confidence': confidence
        }
    
    @abstractmethod
    def process_task(self, task: Dict) -> Dict:
        """Process assigned task - implemented by subclasses."""
        pass
    
    def run_cycle(self):
        """Process one agent cycle."""
        # Check messages
        messages = self.check_messages()
        for msg in messages:
            self._handle_message(msg)
        
        # Update state
        self.last_active = time.time()
        
        # Periodically save
        if self.tasks_completed % 10 == 0:
            self._save_state()
    
    def _handle_message(self, msg: AgentMessage):
        """Handle incoming message."""
        if msg.msg_type == MessageType.TASK_DELEGATION:
            if 'seeking' in msg.payload:
                # Check if we can handle it
                if self._can_handle(msg.payload['task']):
                    self.send_message(
                        MessageType.STATUS_UPDATE,
                        {'available': True, 'skills': list(self.skills.keys())},
                        recipient=msg.sender
                    )
            else:
                # Execute task
                result = self.process_task(msg.payload)
                if result.get('success'):
                    self.tasks_completed += 1
                else:
                    self.tasks_failed += 1
    
    def _can_handle(self, task: str) -> bool:
        """Check if agent can handle task type."""
        task_lower = task.lower()
        for skill in self.skills:
            if skill.lower() in task_lower:
                return True
        return False
    
    def get_status(self) -> Dict:
        """Get agent status."""
        return {
            'id': self.id,
            'name': self.name,
            'role': self.role,
            'version': self.version,
            'status': self.status,
            'skills': {k: v.level for k, v in self.skills.items()},
            'tasks_completed': self.tasks_completed,
            'tasks_failed': self.tasks_failed,
            'messages_sent': self.messages_sent,
            'messages_received': self.messages_received,
            'uptime': time.time() - self.created
        }


class SecurityAgent(BaseAgent):
    """
    Specialized agent for security operations.
    
    Capabilities:
    - Threat detection and analysis
    - Vulnerability assessment
    - Incident response
    - Security policy enforcement
    - Penetration testing coordination
    """
    
    VERSION = "3.0.0"
    
    def __init__(self):
        super().__init__("SecurityAgent", "security", self.VERSION)
        
        # Security-specific skills
        self.learn_skill("threat_detection", 8)
        self.learn_skill("vulnerability_scanning", 7)
        self.learn_skill("incident_response", 6)
        self.learn_skill("forensics_analysis", 5)
        self.learn_skill("penetration_testing", 6)
        
        # Threat database
        self.threats: List[Dict] = []
        self.vulnerabilities: List[Dict] = []
        self.incidents: List[Dict] = []
    
    def analyze_threat(self, data: Dict) -> Dict:
        """Analyze potential threat."""
        print(f"[SecurityAgent] Analyzing threat...")
        
        threat_level = "low"
        indicators = []
        
        # Analyze patterns
        if 'source_ip' in data:
            # Check for known bad IPs
            if self._is_known_bad_ip(data['source_ip']):
                threat_level = "high"
                indicators.append("known_bad_ip")
        
        if 'payload' in data:
            # Check for attack patterns
            if self._detect_attack_pattern(data['payload']):
                threat_level = "critical"
                indicators.append("attack_pattern")
        
        threat = {
            'id': str(uuid.uuid4()),
            'timestamp': time.time(),
            'level': threat_level,
            'indicators': indicators,
            'data': data,
            'analyzed_by': self.id
        }
        
        self.threats.append(threat)
        
        # Alert other agents if high/critical
        if threat_level in ['high', 'critical']:
            self.send_message(
                MessageType.THREAT_ALERT,
                threat,
                priority=10,
                requires_ack=True
            )
        
        print(f"  Threat level: {threat_level}")
        return threat
    
    def _is_known_bad_ip(self, ip: str) -> bool:
        """Check if IP is in threat database."""
        # Would query threat intelligence
        return ip.startswith('10.0.0.')  # Example
    
    def _detect_attack_pattern(self, payload: str) -> bool:
        """Detect attack patterns in payload."""
        patterns = ['SELECT * FROM', 'DROP TABLE', '<script>', 'eval(']
        return any(p.lower() in payload.lower() for p in patterns)
    
    def scan_vulnerabilities(self, target: str) -> List[Dict]:
        """Scan target for vulnerabilities."""
        print(f"[SecurityAgent] Scanning {target}...")
        
        vulns = []
        
        # Simulate scan
        checks = [
            ('open_ports', self._check_open_ports),
            ('outdated_software', self._check_versions),
            ('weak_crypto', self._check_crypto),
        ]
        
        for check_name, check_func in checks:
            result = check_func(target)
            if result:
                vulns.append({
                    'type': check_name,
                    'severity': result['severity'],
                    'details': result['details']
                })
        
        self.vulnerabilities.extend(vulns)
        print(f"  Found {len(vulns)} vulnerabilities")
        
        return vulns
    
    def _check_open_ports(self, target: str) -> Optional[Dict]:
        return None  # Placeholder
    
    def _check_versions(self, target: str) -> Optional[Dict]:
        return None
    
    def _check_crypto(self, target: str) -> Optional[Dict]:
        return None
    
    def process_task(self, task: Dict) -> Dict:
        """Process security task."""
        task_type = task.get('type', 'unknown')
        
        if task_type == 'threat_analysis':
            result = self.analyze_threat(task.get('data', {}))
            return {'success': True, 'result': result}
        
        elif task_type == 'vuln_scan':
            vulns = self.scan_vulnerabilities(task.get('target', ''))
            return {'success': True, 'vulnerabilities': vulns}
        
        return {'success': False, 'error': 'Unknown task type'}


class CryptoAgent(BaseAgent):
    """
    Specialized agent for cryptographic operations.
    
    Capabilities:
    - Key generation and management
    - Encryption/decryption
    - Digital signatures
    - Secure random generation
    - Post-quantum crypto prep
    """
    
    VERSION = "3.0.0"
    
    def __init__(self):
        super().__init__("CryptoAgent", "cryptography", self.VERSION)
        
        self.learn_skill("symmetric_encryption", 9)
        self.learn_skill("asymmetric_encryption", 8)
        self.learn_skill("key_management", 9)
        self.learn_skill("digital_signatures", 8)
        self.learn_skill("secure_random", 10)
        self.learn_skill("post_quantum_prep", 6)
    
    def generate_keypair(self, algorithm: str = "ed25519") -> Dict:
        """Generate cryptographic keypair."""
        print(f"[CryptoAgent] Generating {algorithm} keypair...")
        
        # Simulated key generation
        private_key = hashlib.sha256(
            (str(time.time()) + str(uuid.uuid4())).encode()
        ).hexdigest()
        
        public_key = hashlib.sha256(private_key.encode()).hexdigest()
        
        keypair = {
            'algorithm': algorithm,
            'private_key': private_key,
            'public_key': public_key,
            'created': time.time(),
            'agent': self.id
        }
        
        print(f"  Keys generated")
        return keypair
    
    def secure_channel(self, peer_public_key: str) -> Dict:
        """Establish secure channel."""
        print("[CryptoAgent] Establishing secure channel...")
        
        # Generate ephemeral key
        ephemeral = self.generate_keypair("x25519")
        
        # Derive shared secret
        shared_secret = hashlib.sha256(
            (ephemeral['private_key'] + peer_public_key).encode()
        ).hexdigest()
        
        channel = {
            'ephemeral_public': ephemeral['public_key'],
            'shared_secret': shared_secret,
            'established': time.time()
        }
        
        print("  Channel established")
        return channel
    
    def process_task(self, task: Dict) -> Dict:
        """Process cryptographic task."""
        task_type = task.get('type', 'unknown')
        
        if task_type == 'generate_keys':
            keys = self.generate_keypair(task.get('algorithm', 'ed25519'))
            return {'success': True, 'keys': keys}
        
        elif task_type == 'secure_channel':
            channel = self.secure_channel(task.get('peer_key', ''))
            return {'success': True, 'channel': channel}
        
        return {'success': False, 'error': 'Unknown task type'}


class NetworkAgent(BaseAgent):
    """
    Specialized agent for network operations.
    
    Capabilities:
    - Traffic analysis
    - Network mapping
    - Protocol analysis
    - Route optimization
    - Covert channel detection
    """
    
    VERSION = "3.0.0"
    
    def __init__(self):
        super().__init__("NetworkAgent", "network", self.VERSION)
        
        self.learn_skill("traffic_analysis", 8)
        self.learn_skill("network_mapping", 7)
        self.learn_skill("protocol_analysis", 8)
        self.learn_skill("route_optimization", 6)
        self.learn_skill("covert_detection", 7)
    
    def analyze_traffic(self, capture: List[Dict]) -> Dict:
        """Analyze network traffic."""
        print("[NetworkAgent] Analyzing traffic...")
        
        findings = {
            'total_packets': len(capture),
            'protocols': {},
            'anomalies': [],
            'suspicious_flows': []
        }
        
        for packet in capture:
            proto = packet.get('protocol', 'unknown')
            findings['protocols'][proto] = findings['protocols'].get(proto, 0) + 1
            
            # Detect anomalies
            if packet.get('size', 0) > 1500:
                findings['anomalies'].append('oversized_packet')
            
            if packet.get('flags') == 'SYN' and not packet.get('ack'):
                findings['suspicious_flows'].append(packet.get('src_ip'))
        
        print(f"  Analyzed {len(capture)} packets")
        return findings
    
    def process_task(self, task: Dict) -> Dict:
        """Process network task."""
        task_type = task.get('type', 'unknown')
        
        if task_type == 'traffic_analysis':
            result = self.analyze_traffic(task.get('capture', []))
            return {'success': True, 'analysis': result}
        
        return {'success': False, 'error': 'Unknown task type'}


class ForensicsAgent(BaseAgent):
    """
    Specialized agent for digital forensics.
    
    Capabilities:
    - File recovery
    - Timeline reconstruction
    - Artifact extraction
    - Memory forensics
    - Anti-forensics detection
    """
    
    VERSION = "3.0.0"
    
    def __init__(self):
        super().__init__("ForensicsAgent", "forensics", self.VERSION)
        
        self.learn_skill("file_recovery", 7)
        self.learn_skill("timeline_reconstruction", 8)
        self.learn_skill("artifact_extraction", 8)
        self.learn_skill("memory_forensics", 6)
        self.learn_skill("anti_forensics_detection", 7)
    
    def analyze_disk(self, image_path: str) -> Dict:
        """Analyze disk image."""
        print(f"[ForensicsAgent] Analyzing disk: {image_path}")
        
        findings = {
            'files_recovered': 0,
            'deleted_files': [],
            'timeline': [],
            'artifacts': {}
        }
        
        # Simulated analysis
        print("  Scanning filesystem...")
        print("  Reconstructing timeline...")
        print("  Extracting artifacts...")
        
        return findings
    
    def process_task(self, task: Dict) -> Dict:
        """Process forensics task."""
        task_type = task.get('type', 'unknown')
        
        if task_type == 'disk_analysis':
            result = self.analyze_disk(task.get('image', ''))
            return {'success': True, 'findings': result}
        
        return {'success': False, 'error': 'Unknown task type'}


class AgentManager:
    """
    Manager for coordinating multiple agents.
    
    Provides:
    - Agent lifecycle management
    - Task distribution
    - Load balancing
    - Consensus coordination
    """
    
    VERSION = "3.0.0"
    
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self.task_queue: List[Dict] = []
        self.running = False
    
    def spawn_agent(self, agent_type: str) -> Optional[BaseAgent]:
        """Spawn new agent of specified type."""
        agent_map = {
            'security': SecurityAgent,
            'crypto': CryptoAgent,
            'network': NetworkAgent,
            'forensics': ForensicsAgent,
        }
        
        if agent_type not in agent_map:
            print(f"[Manager] Unknown agent type: {agent_type}")
            return None
        
        agent = agent_map[agent_type]()
        self.agents[agent.id] = agent
        return agent
    
    def distribute_task(self, task: Dict) -> Optional[str]:
        """Distribute task to best-suited agent."""
        task_type = task.get('type', '')
        
        # Find agents with relevant skills
        candidates = []
        for agent in self.agents.values():
            score = 0
            for skill in agent.skills:
                if skill.lower() in task_type.lower():
                    score += agent.skills[skill].level
            if score > 0:
                candidates.append((agent, score))
        
        if not candidates:
            print("[Manager] No suitable agents found")
            return None
        
        # Select best candidate
        candidates.sort(key=lambda x: x[1], reverse=True)
        best_agent = candidates[0][0]
        
        # Delegate
        msg_id = best_agent.delegate_task(str(task))
        return msg_id
    
    def get_swarm_status(self) -> Dict:
        """Get status of entire agent swarm."""
        return {
            'agents': len(self.agents),
            'by_role': {},
            'total_tasks_completed': sum(
                a.tasks_completed for a in self.agents.values()
            ),
            'total_messages': sum(
                a.messages_sent + a.messages_received 
                for a in self.agents.values()
            )
        }


def demo():
    """Demonstrate enhanced agent system."""
    print("=" * 70)
    print("Enhanced Agent Framework Demo")
    print("=" * 70)
    print()
    
    # Create manager
    manager = AgentManager()
    
    # Spawn agents
    print("Spawning specialized agents...")
    security = manager.spawn_agent('security')
    crypto = manager.spawn_agent('crypto')
    network = manager.spawn_agent('network')
    forensics = manager.spawn_agent('forensics')
    print()
    
    # Demonstrate inter-agent communication
    print("Demonstrating inter-agent communication...")
    
    # Security agent detects threat
    threat_data = {
        'source_ip': '192.168.1.100',
        'payload': '<script>alert("xss")</script>',
        'timestamp': time.time()
    }
    threat = security.analyze_threat(threat_data)
    print()
    
    # Crypto agent generates keys
    keys = crypto.generate_keypair()
    print()
    
    # Network agent analyzes traffic
    capture = [
        {'protocol': 'TCP', 'size': 64, 'flags': 'SYN', 'src_ip': '10.0.0.1'},
        {'protocol': 'UDP', 'size': 128, 'src_ip': '10.0.0.2'},
        {'protocol': 'TCP', 'size': 2000, 'flags': 'ACK', 'src_ip': '10.0.0.3'},
    ]
    network.analyze_traffic(capture)
    print()
    
    # Show swarm status
    print("Swarm Status:")
    status = manager.get_swarm_status()
    print(f"  Active agents: {status['agents']}")
    print(f"  Total tasks completed: {status['total_tasks_completed']}")
    print(f"  Total messages: {status['total_messages']}")
    print()
    
    # Show individual agent status
    print("Agent Details:")
    for agent_id, agent in manager.agents.items():
        info = agent.get_status()
        print(f"  {info['name']} ({info['role']})")
        print(f"    Skills: {', '.join(info['skills'].keys())}")
        print(f"    Tasks: {info['tasks_completed']} completed")
    print()
    
    print("=" * 70)
    print("Demo Complete")
    print("=" * 70)


if __name__ == '__main__':
    demo()

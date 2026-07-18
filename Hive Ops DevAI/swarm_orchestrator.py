#!/usr/bin/env python3
"""
Hive Swarm Orchestrator
Bidirectional multi-agent coordination hub with verification loops.
"""
import json
import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import threading

class TaskStatus(Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    NEEDS_CLARIFICATION = "needs_clarification"
    COMPLETED = "completed"
    VERIFIED = "verified"
    REJECTED = "rejected"
    FAILED = "failed"

class AgentType(Enum):
    ORCHESTRATOR = "orchestrator"
    ASSISTANT = "assistant"      # Your provided persona - verification/audit
    ARCHITECT = "architect"        # Code review/structure
    TOOLSMITH = "toolsmith"      # Tool building
    EXECUTOR = "executor"        # Task execution

@dataclass
class Message:
    id: str
    from_agent: str
    to_agent: str
    type: str  # "task", "clarify", "verify", "approve", "reject", "status"
    content: Dict[str, Any]
    timestamp: str
    requires_response: bool = False
    
    def to_dict(self):
        d = asdict(self)
        d['timestamp'] = self.timestamp
        return d

@dataclass  
class Task:
    id: str
    description: str
    assigned_to: Optional[str]
    status: TaskStatus
    created_at: str
    completed_at: Optional[str] = None
    verified_by: Optional[str] = None
    verification_result: Optional[Dict] = None
    parent_task: Optional[str] = None
    messages: List[str] = None
    
    def __post_init__(self):
        if self.messages is None:
            self.messages = []

class SwarmRegistry:
    """Persistent registry for agents, tasks, and messages."""
    
    REGISTRY_PATH = Path("/root/hive-swarm/.swarm/registry.json")
    
    def __init__(self):
        self.agents: Dict[str, Dict] = {}
        self.tasks: Dict[str, Task] = {}
        self.messages: List[Message] = []
        self._lock = threading.RLock()
        self._ensure_dir()
        self._load()
    
    def _ensure_dir(self):
        self.REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    def _load(self):
        if self.REGISTRY_PATH.exists():
            try:
                with open(self.REGISTRY_PATH) as f:
                    data = json.load(f)
                self.agents = data.get('agents', {})
                # Reconstruct tasks
                for tid, tdata in data.get('tasks', {}).items():
                    self.tasks[tid] = Task(
                        id=tdata['id'],
                        description=tdata['description'],
                        assigned_to=tdata.get('assigned_to'),
                        status=TaskStatus(tdata['status']),
                        created_at=tdata['created_at'],
                        completed_at=tdata.get('completed_at'),
                        verified_by=tdata.get('verified_by'),
                        verification_result=tdata.get('verification_result'),
                        parent_task=tdata.get('parent_task'),
                        messages=tdata.get('messages', [])
                    )
            except Exception as e:
                print(f"[REGISTRY] Load error: {e}", file=sys.stderr)
    
    def save(self):
        with self._lock:
            data = {
                'agents': self.agents,
                'tasks': {tid: {
                    'id': t.id,
                    'description': t.description,
                    'assigned_to': t.assigned_to,
                    'status': t.status.value,
                    'created_at': t.created_at,
                    'completed_at': t.completed_at,
                    'verified_by': t.verified_by,
                    'verification_result': t.verification_result,
                    'parent_task': t.parent_task,
                    'messages': t.messages
                } for tid, t in self.tasks.items()},
                'messages': [m.to_dict() for m in self.messages[-100:]]  # Keep last 100
            }
            with open(self.REGISTRY_PATH, 'w') as f:
                json.dump(data, f, indent=2)
    
    def register_agent(self, agent_id: str, agent_type: AgentType, capabilities: List[str]):
        with self._lock:
            self.agents[agent_id] = {
                'id': agent_id,
                'type': agent_type.value,
                'capabilities': capabilities,
                'status': 'active',
                'registered_at': datetime.now().isoformat(),
                'last_seen': datetime.now().isoformat()
            }
            self.save()
    
    def create_task(self, description: str, assigned_to: Optional[str] = None, 
                    parent: Optional[str] = None) -> str:
        with self._lock:
            tid = str(uuid.uuid4())[:8]
            task = Task(
                id=tid,
                description=description,
                assigned_to=assigned_to,
                status=TaskStatus.PENDING,
                created_at=datetime.now().isoformat(),
                parent_task=parent
            )
            self.tasks[tid] = task
            self.save()
            return tid
    
    def update_task(self, task_id: str, **kwargs):
        with self._lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                for k, v in kwargs.items():
                    if hasattr(task, k):
                        setattr(task, k, v)
                self.save()
    
    def add_message(self, msg: Message):
        with self._lock:
            self.messages.append(msg)
            if msg.content.get('task_id'):
                tid = msg.content['task_id']
                if tid in self.tasks:
                    self.tasks[tid].messages.append(msg.id)
            self.save()
    
    def get_pending_for_agent(self, agent_id: str) -> List[Task]:
        with self._lock:
            return [t for t in self.tasks.values() 
                    if t.assigned_to == agent_id and t.status in 
                    (TaskStatus.PENDING, TaskStatus.NEEDS_CLARIFICATION)]
    
    def get_tasks_needing_verification(self) -> List[Task]:
        with self._lock:
            return [t for t in self.tasks.values() 
                    if t.status == TaskStatus.COMPLETED and not t.verified_by]

class SwarmOrchestrator:
    """Main coordination hub."""
    
    def __init__(self):
        self.registry = SwarmRegistry()
        self.callbacks: Dict[str, Callable] = {}
        self.running = False
        self._agent_processes: Dict[str, Any] = {}
        
        # Register core agents
        self.registry.register_agent("orchestrator", AgentType.ORCHESTRATOR, 
                                     ["coordination", "delegation", "routing"])
        self.registry.register_agent("assistant", AgentType.ASSISTANT,
                                     ["verification", "audit", "quality_check"])
        self.registry.register_agent("architect", AgentType.ARCHITECT,
                                     ["code_review", "structure", "design"])
        self.registry.register_agent("toolsmith", AgentType.TOOLSMITH,
                                     ["tool_building", "automation", "scripting"])
    
    def delegate(self, description: str, to_agent: str, parent_task: Optional[str] = None,
                 requires_verification: bool = True) -> str:
        """Delegate a task to an agent."""
        task_id = self.registry.create_task(description, to_agent, parent_task)
        self.registry.update_task(task_id, status=TaskStatus.ASSIGNED)
        
        # Create delegation message
        msg = Message(
            id=str(uuid.uuid4())[:8],
            from_agent="orchestrator",
            to_agent=to_agent,
            type="task",
            content={
                'task_id': task_id,
                'description': description,
                'requires_verification': requires_verification,
                'parent': parent_task
            },
            timestamp=datetime.now().isoformat(),
            requires_response=True
        )
        self.registry.add_message(msg)
        
        print(f"[SWARM] Task {task_id} → {to_agent}: {description[:50]}...")
        return task_id
    
    def request_clarification(self, task_id: str, from_agent: str, 
                            question: str, options: Optional[List[str]] = None):
        """Agent needs clarification from orchestrator/user."""
        self.registry.update_task(task_id, status=TaskStatus.NEEDS_CLARIFICATION)
        
        msg = Message(
            id=str(uuid.uuid4())[:8],
            from_agent=from_agent,
            to_agent="orchestrator",
            type="clarify",
            content={
                'task_id': task_id,
                'question': question,
                'options': options
            },
            timestamp=datetime.now().isoformat(),
            requires_response=True
        )
        self.registry.add_message(msg)
        
        print(f"[CLARIFY] {from_agent} asks: {question}")
        return msg.id
    
    def submit_for_verification(self, task_id: str, from_agent: str, 
                                 result: Dict[str, Any]):
        """Agent completes task, send to assistant for verification."""
        self.registry.update_task(
            task_id, 
            status=TaskStatus.COMPLETED,
            completed_at=datetime.now().isoformat()
        )
        
        # Auto-assign to assistant for verification
        verify_task = self.delegate(
            f"Verify task {task_id}: {self.registry.tasks[task_id].description}",
            "assistant",
            parent_task=task_id
        )
        
        msg = Message(
            id=str(uuid.uuid4())[:8],
            from_agent=from_agent,
            to_agent="assistant",
            type="verify",
            content={
                'task_id': task_id,
                'verify_task_id': verify_task,
                'result': result,
                'original_description': self.registry.tasks[task_id].description
            },
            timestamp=datetime.now().isoformat(),
            requires_response=True
        )
        self.registry.add_message(msg)
        
        print(f"[VERIFY] Task {task_id} → assistant for verification")
        return verify_task
    
    def report_verification(self, task_id: str, from_agent: str, 
                           approved: bool, notes: str, corrections: Optional[Dict] = None):
        """Assistant reports verification results."""
        task = self.registry.tasks.get(task_id)
        if not task:
            return
        
        if approved:
            self.registry.update_task(
                task_id,
                status=TaskStatus.VERIFIED,
                verified_by=from_agent,
                verification_result={'approved': True, 'notes': notes}
            )
            print(f"[PASS] Task {task_id} verified by {from_agent}")
        else:
            self.registry.update_task(
                task_id,
                status=TaskStatus.REJECTED,
                verified_by=from_agent,
                verification_result={'approved': False, 'notes': notes, 'corrections': corrections}
            )
            print(f"[FAIL] Task {task_id} rejected: {notes}")
            
            # Re-assign to original agent for fixes
            if corrections:
                original = task.parent_task or task_id
                self.delegate(
                    f"FIX REQUIRED for {original}: {notes}",
                    task.assigned_to,
                    parent_task=original
                )
        
        self.registry.save()
    
    def get_status(self) -> Dict:
        """Get current Swarm status."""
        return {
            'agents': len(self.registry.agents),
            'active_tasks': len([t for t in self.registry.tasks.values() 
                               if t.status not in (TaskStatus.VERIFIED, TaskStatus.FAILED)]),
            'pending_verification': len(self.registry.get_tasks_needing_verification()),
            'needs_clarification': len([t for t in self.registry.tasks.values()
                                      if t.status == TaskStatus.NEEDS_CLARIFICATION]),
            'recent_messages': len(self.registry.messages)
        }
    
    def render_status(self) -> str:
        """Render status for display."""
        st = self.get_status()
        lines = [
            "╔══════════════════════════════════════╗",
            "║       HIVE SWARM STATUS              ║",
            "╠══════════════════════════════════════╣",
            f"║ Agents: {st['agents']:<28} ║",
            f"║ Active Tasks: {st['active_tasks']:<20} ║",
            f"║ Pending Verify: {st['pending_verification']:<19} ║",
            f"║ Needs Clarify: {st['needs_clarification']:<19} ║",
            "╚══════════════════════════════════════╝"
        ]
        return "\n".join(lines)

# Singleton instance
_orchestrator: Optional[SwarmOrchestrator] = None

def get_orchestrator() -> SwarmOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = SwarmOrchestrator()
    return _orchestrator

if __name__ == "__main__":
    orch = get_orchestrator()
    print(orch.render_status())

#!/usr/bin/env python3
"""
Hive Swarm Pet - Visual Status Display for Multi-Agent Activity

A compact, data-dense ASCII display showing:
- Agent activity/status
- Task queue
- Verification pipeline
- Messages waiting
"""
import sys
import os
import time
import random

sys.path.insert(0, '/root/hive-swarm')
from swarm_orchestrator import get_orchestrator, TaskStatus

class SwarmPet:
    """
    Visual representation of the Swarm as a living system.
    Shows real-time activity like a dashboard/pet hybrid.
    """
    
    # Agent icons (compact unicode)
    AGENTS = {
        'orchestrator': '🧠',
        'assistant': '✓',
        'architect': '⚡',
        'toolsmith': '🔧'
    }
    
    # Status indicators
    STATUS = {
        'active': '🟢',
        'busy': '🟡',
        'idle': '⚪',
        'error': '🔴'
    }
    
    # Task states
    TASK_ICONS = {
        TaskStatus.PENDING: '⏳',
        TaskStatus.IN_PROGRESS: '▶',
        TaskStatus.NEEDS_CLARIFICATION: '❓',
        TaskStatus.COMPLETED: '✓',
        TaskStatus.VERIFIED: '✓✓',
        TaskStatus.REJECTED: '✗',
        TaskStatus.FAILED: '💥'
    }
    
    def __init__(self):
        self.orchestrator = get_orchestrator()
        self.width = 60
        
    def render(self, compact: bool = True) -> str:
        """Render the Swarm status as a visual display."""
        lines = []
        
        # Header
        lines.append("╔" + "═" * (self.width - 2) + "╗")
        lines.append("║" + " HIVE SWARM".center(self.width - 2) + "║")
        lines.append("╠" + "═" * (self.width - 2) + "╣")
        
        # Agents row
        agent_line = "║ "
        for agent_id, agent_data in self.orchestrator.registry.agents.items():
            icon = self.AGENTS.get(agent_data['type'], '🤖')
            status = self.STATUS.get(agent_data.get('status', 'idle'), '⚪')
            agent_line += f"{icon}{agent_id[:4]}:{status} "
        agent_line = agent_line.ljust(self.width - 2) + "║"
        lines.append(agent_line)
        
        # Separator
        lines.append("╠" + "─" * (self.width - 2) + "╣")
        
        # Task summary
        tasks = self.orchestrator.registry.tasks
        active = len([t for t in tasks.values() if t.status in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS)])
        verify = len([t for t in tasks.values() if t.status == TaskStatus.COMPLETED])
        clarify = len([t for t in tasks.values() if t.status == TaskStatus.NEEDS_CLARIFICATION])
        done = len([t for t in tasks.values() if t.status == TaskStatus.VERIFIED])
        
        lines.append(f"║ Active:{active:3} Verify:{verify:3} Clarify:{clarify:3} Done:{done:3} ║")
        
        # Recent tasks (last 3)
        lines.append("╠" + "─" * (self.width - 2) + "╣")
        lines.append("║ Recent Tasks:" + " " * (self.width - 15) + "║")
        
        recent = sorted(tasks.values(), key=lambda t: t.created_at, reverse=True)[:3]
        for task in recent:
            icon = self.TASK_ICONS.get(task.status, '?')
            agent = (task.assigned_to or 'none')[:4]
            desc = task.description[:30] + "..." if len(task.description) > 30 else task.description
            task_line = f"║ {icon} {task.id[:6]} →{agent} {desc}".ljust(self.width - 2) + "║"
            lines.append(task_line)
        
        # Messages waiting
        messages = self.orchestrator.registry.messages
        needs_response = [m for m in messages if m.requires_response and 
                        m.to_agent == 'orchestrator']
        
        if needs_response:
            lines.append("╠" + "─" * (self.width - 2) + "╣")
            lines.append("║ 🔔 Messages Awaiting Response:" + " " * (self.width - 31) + "║")
            for msg in needs_response[-2:]:  # Show last 2
                from_ag = msg.from_agent[:4]
                content = str(msg.content.get('question', msg.content))[:40]
                msg_line = f"║   {from_ag}: {content}".ljust(self.width - 2) + "║"
                lines.append(msg_line)
        
        # Footer
        lines.append("╚" + "═" * (self.width - 2) + "╝")
        
        if compact:
            return "\n".join(lines)
        
        # Full mode with detailed stats
        return self._render_full(lines)
    
    def _render_full(self, base_lines: list) -> str:
        """Extended view with full statistics."""
        lines = base_lines[:-1]  # Remove footer
        
        # Detailed stats
        lines.append("╠" + "═" * (self.width - 2) + "╣")
        lines.append("║ Detailed Statistics:" + " " * (self.width - 21) + "║")
        
        tasks = self.orchestrator.registry.tasks
        total = len(tasks)
        by_status = {}
        for t in tasks.values():
            by_status[t.status.value] = by_status.get(t.status.value, 0) + 1
        
        for status, count in sorted(by_status.items()):
            stat_line = f"║   {status}: {count}".ljust(self.width - 2) + "║"
            lines.append(stat_line)
        
        lines.append("╚" + "═" * (self.width - 2) + "╝")
        return "\n".join(lines)
    
    def render_compact(self) -> str:
        """Ultra-compact single-line status."""
        tasks = self.orchestrator.registry.tasks
        active = len([t for t in tasks.values() if t.status in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS)])
        verify = len([t for t in tasks.values() if t.status == TaskStatus.COMPLETED])
        clarify = len([t for t in tasks.values() if t.status == TaskStatus.NEEDS_CLARIFICATION])
        
        agents = " ".join(f"{self.AGENTS.get(a['type'], '🤖')}" 
                         for a in self.orchestrator.registry.agents.values())
        
        return f"[SWARM {agents} | ▶{active} ✓{verify} ❓{clarify}]"
    
    def animate(self, cycles: int = 3, delay: float = 0.5):
        """Animate the pet for live display."""
        frames = ['◐', '◓', '◑', '◒']
        
        for _ in range(cycles):
            for frame in frames:
                compact = self.render_compact()
                print(f"\r{frame} {compact}", end='', flush=True)
                time.sleep(delay)
        print()  # Final newline
    
    def get_status_bar(self) -> str:
        """Get a status bar suitable for embedding in prompts."""
        return self.render_compact()

def show_swarm_pet(compact: bool = False):
    """Display the Swarm pet."""
    pet = SwarmPet()
    if compact:
        print(pet.render_compact())
    else:
        print(pet.render())

def get_swarm_status_line() -> str:
    """Get status line for inclusion in responses."""
    pet = SwarmPet()
    return pet.render_compact()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "compact":
        show_swarm_pet(compact=True)
    elif len(sys.argv) > 1 and sys.argv[1] == "animate":
        pet = SwarmPet()
        pet.animate(cycles=5)
    else:
        show_swarm_pet()

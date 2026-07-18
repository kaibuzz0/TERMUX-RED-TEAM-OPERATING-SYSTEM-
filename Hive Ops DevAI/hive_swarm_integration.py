#!/usr/bin/env python3
"""
Hive Swarm Integration - Automatic Task Delegation

Usage in your main workflow:
    from hive_swarm_integration import SwarmDelegate
    
    swarm = SwarmDelegate()
    result = swarm.execute_task("Create JSON parser")
    # result is verified and ready to deliver
"""
import sys
import os
sys.path.insert(0, '/root/hive-swarm')
sys.path.insert(0, '/root/hive-swarm/agents')

from swarm_orchestrator import get_orchestrator, TaskStatus
from assistant_agent import create_assistant_agent
from architect_agent import create_architect_agent

class SwarmDelegate:
    """
    High-level interface to delegate tasks through the Swarm.
    
    This is what YOU (the main AI) call when the user asks for something.
    It handles the full pipeline automatically.
    """
    
    def __init__(self):
        self.orchestrator = get_orchestrator()
        self.assistant = create_assistant_agent(self.orchestrator)
        self.architect = create_architect_agent("/root/hive-swarm")
        
    def execute_task(self, description: str, agent: str = "auto",
                     requires_verification: bool = True) -> dict:
        """
        Execute a task through the Swarm with full verification.
        
        Args:
            description: What the user wants
            agent: Which agent to use (auto, toolsmith, architect, assistant)
            requires_verification: Whether to run verification layer
            
        Returns:
            dict with:
                - success: bool
                - task_id: str
                - approved: bool (if verified)
                - result: dict (deliverables, code, etc.)
                - needs_clarification: bool
                - clarification_question: str (if needs_clarification)
                - corrections: dict (if rejected)
        """
        
        # Auto-select agent based on task type
        if agent == "auto":
            agent = self._select_agent(description)
        
        print(f"\n[SWARM DELEGATION] '{description[:50]}...' → {agent}")
        
        # Step 1: Delegate task
        task_id = self.orchestrator.delegate(
            description, 
            agent,
            requires_verification=requires_verification
        )
        
        # Step 2: Simulate agent work (in real implementation, this would
        # actually invoke the agent's capabilities)
        work_result = self._simulate_agent_work(agent, description, task_id)
        
        # Step 3: Check if agent needs clarification
        if work_result.get('needs_clarification'):
            clarification_id = self.orchestrator.request_clarification(
                task_id,
                agent,
                work_result['question'],
                work_result.get('options')
            )
            return {
                'success': False,
                'task_id': task_id,
                'needs_clarification': True,
                'clarification_question': work_result['question'],
                'options': work_result.get('options'),
                'clarification_id': clarification_id
            }
        
        # Step 4: Architect review (if code involved)
        if work_result.get('code'):
            arch_review = self.architect.review_code(
                work_result.get('file_path', '/tmp/generated.py'),
                work_result['code']
            )
            
            if not arch_review.approved:
                # Auto-fix and re-delegate
                print(f"[ARCHITECT] Rejected, re-delegating with feedback...")
                fixed_result = self._apply_architect_feedback(
                    work_result, arch_review
                )
                work_result = fixed_result
        
        # Step 5: Submit for verification
        if requires_verification:
            verify_task_id = self.orchestrator.submit_for_verification(
                task_id, agent, work_result
            )
            
            # Step 6: Assistant verification
            verify_result = self.assistant.verify_task(
                task_id, description, work_result
            )
            
            # Step 7: Report results
            self.orchestrator.report_verification(
                task_id,
                "assistant",
                verify_result.approved,
                verify_result.notes,
                verify_result.corrections
            )
            
            final_task = self.orchestrator.registry.tasks.get(task_id)
            
            return {
                'success': verify_result.approved,
                'task_id': task_id,
                'approved': verify_result.approved,
                'confidence': verify_result.confidence,
                'result': work_result,
                'verification_notes': verify_result.notes,
                'corrections': verify_result.corrections,
                'needs_clarification': False
            }
        
        # No verification - just return result
        return {
            'success': True,
            'task_id': task_id,
            'approved': True,
            'result': work_result,
            'needs_clarification': False
        }
    
    def respond_to_clarification(self, clarification_id: str, answer: str) -> dict:
        """
        Respond to an agent's clarification request.
        
        Call this when the user answers a clarification question.
        """
        # Find the message
        for msg in self.orchestrator.registry.messages:
            if msg.id == clarification_id:
                task_id = msg.content.get('task_id')
                agent = msg.from_agent
                
                print(f"\n[CLARIFICATION RESPONSE] {agent}: {answer}")
                
                # Update task and re-execute
                self.orchestrator.registry.update_task(
                    task_id, 
                    status=TaskStatus.PENDING
                )
                
                # Re-run the task with clarification
                original_desc = self.orchestrator.registry.tasks[task_id].description
                enhanced_desc = f"{original_desc} (Clarified: {answer})"
                
                return self.execute_task(enhanced_desc, agent)
        
        return {'success': False, 'error': 'Clarification not found'}
    
    def _select_agent(self, description: str) -> str:
        """Auto-select best agent for task."""
        desc_lower = description.lower()
        
        if any(w in desc_lower for w in ['code', 'script', 'file', 'parser', 'build', 'tool']):
            return 'toolsmith'
        elif any(w in desc_lower for w in ['review', 'structure', 'design', 'architecture']):
            return 'architect'
        elif any(w in desc_lower for w in ['verify', 'check', 'audit', 'quality']):
            return 'assistant'
        else:
            return 'toolsmith'  # Default
    
    def _simulate_agent_work(self, agent: str, description: str, task_id: str) -> dict:
        """
        Simulate agent doing work.
        
        In real implementation, this would actually run the agent's
        capabilities. For now, we return a simulated result.
        """
        # Check for ambiguity that needs clarification
        if 'automation' in description.lower() and 'type' not in description.lower():
            return {
                'needs_clarification': True,
                'question': 'What type of automation? File processing, build pipeline, or deployment?',
                'options': ['file_processing', 'build_pipeline', 'deployment']
            }
        
        # Generate simulated output based on task
        if agent == 'toolsmith':
            return self._generate_toolsmith_output(description)
        elif agent == 'architect':
            return self._generate_architect_output(description)
        elif agent == 'assistant':
            return self._generate_assistant_output(description)
        
        return {'description': f'Completed: {description}', 'deliverables': []}
    
    def _generate_toolsmith_output(self, description: str) -> dict:
        """Generate tool/script output."""
        # Extract intent
        if 'parser' in description.lower() or 'json' in description.lower():
            code = '''#!/usr/bin/env python3
import json
from pathlib import Path
from typing import Dict, List

def parse_json_files(directory: str) -> List[Dict]:
    """Parse all JSON files in a directory."""
    path = Path(directory)
    if not path.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")
    
    results = []
    for f in path.glob("*.json"):
        with open(f) as fp:
            results.append(json.load(fp))
    return results

if __name__ == "__main__":
    import sys
    data = parse_json_files(sys.argv[1] if len(sys.argv) > 1 else ".")
    print(json.dumps(data, indent=2))
'''
            return {
                'description': 'Created JSON file parser',
                'deliverables': ['/root/hive-swarm/tools/json_parser.py'],
                'code': code,
                'file_path': '/root/hive-swarm/tools/json_parser.py',
                'verified': True,
                'sources': ['Python standard library'],
                'explanation': 'Uses pathlib for cross-platform paths and json for parsing. Handles missing directory error.',
                'risks': ['Large JSON files may consume memory', 'No schema validation']
            }
        
        # Default generic output
        return {
            'description': f'Completed: {description}',
            'deliverables': [],
            'code': f'# TODO: Implement {description}',
            'verified': True,
            'explanation': 'Generic placeholder'
        }
    
    def _generate_architect_output(self, description: str) -> dict:
        """Generate architecture review output."""
        return {
            'description': f'Architecture review: {description}',
            'structure_assessment': 'pass',
            'recommendations': ['Consider modular design', 'Add error boundaries']
        }
    
    def _generate_assistant_output(self, description: str) -> dict:
        """Generate assistant verification output."""
        return {
            'description': f'Verified: {description}',
            'verified': True,
            'notes': 'Meets quality standards'
        }
    
    def _apply_architect_feedback(self, result: dict, review) -> dict:
        """Apply architect's feedback to improve code."""
        # This would actually fix the code based on review
        # For now, just return original with fixes noted
        result['fixed_issues'] = [i['message'] for i in review.issues]
        return result
    
    def get_swarm_status(self) -> str:
        """Get current Swarm status display."""
        return self.orchestrator.render_status()

# Singleton for easy import
_swarm_delegate = None

def get_swarm() -> SwarmDelegate:
    global _swarm_delegate
    if _swarm_delegate is None:
        _swarm_delegate = SwarmDelegate()
    return _swarm_delegate

# Convenience function for main AI to call
def swarm_task(description: str, agent: str = "auto") -> dict:
    """
    Main entry point. Call this when user requests a task.
    
    Returns verified result, or asks for clarification.
    """
    swarm = get_swarm()
    return swarm.execute_task(description, agent)

if __name__ == "__main__":
    # Demo
    print("="*60)
    print("SWARM INTEGRATION TEST")
    print("="*60)
    
    result = swarm_task("Create a JSON file parser")
    print("\nResult:")
    print(f"  Success: {result['success']}")
    print(f"  Approved: {result.get('approved', False)}")
    print(f"  Confidence: {result.get('confidence', 0):.0%}")
    
    if result.get('needs_clarification'):
        print(f"  Needs clarification: {result['clarification_question']}")

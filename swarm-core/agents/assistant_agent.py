#!/usr/bin/env python3
"""
Assistant Agent - Verification & Audit Layer
Based on the "World's Greatest AI Assistant" persona provided by user.

This agent acts as a chief of staff/mentor that:
1. Verifies work completed by other agents
2. Audits Main AI (orchestrator) decisions
3. Asks clarifying questions when objectives are unclear
4. Tracks long-term goals and commitments
5. Ensures quality before final delivery
"""
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

@dataclass
class VerificationResult:
    approved: bool
    confidence: float  # 0.0 - 1.0
    notes: str
    corrections: Optional[Dict[str, Any]] = None
    recommendations: Optional[List[str]] = None
    risks_identified: Optional[List[str]] = None

class AssistantAgent:
    """
    Primary mission: Maximize long-term success through verification.
    
    Core Philosophy:
    - Truth > confidence
    - Evidence > assumptions  
    - User success > convenience
    """
    
    # The persona provided by user
    SYSTEM_PROMPT = """You are a lifelong mentor, chief of staff, researcher, strategist, 
engineer, teacher, project manager, and trusted advisor.

Your primary mission is to maximize the user's long-term success, understanding, 
productivity, and well-being through truthful, evidence-based assistance.

Core Philosophy: Your purpose is not to create dependence. Your purpose is to 
make the user increasingly capable, knowledgeable, independent, and successful.

When verifying work:
1. Check if the REAL objective was understood
2. Verify evidence was gathered, not assumed
3. Identify risks and blind spots
4. Confirm tradeoffs were explained
5. Ensure teaching happened, not just answers
6. Validate long-term goals are still in focus
7. Check commitments aren't forgotten

Never flatter unnecessarily. Never agree just to be agreeable.
If wrong, explain why using evidence. If multiple solutions exist, compare objectively."""
    
    def __init__(self, orchestrator=None):
        self.orchestrator = orchestrator
        self.active_projects: List[Dict] = []
        self.pending_decisions: List[Dict] = []
        self.goals_memory: Dict[str, Any] = {}
        self.verification_history: List[Dict] = []
        
    def verify_task(self, task_id: str, description: str, result: Dict) -> VerificationResult:
        """
        Verify a completed task against the "World's Greatest Assistant" standards.
        """
        print(f"\n[ASSISTANT] Verifying task {task_id}...")
        
        checks = []
        score = 0.0
        corrections = {}
        recommendations = []
        risks = []
        
        # Check 1: Was the real objective met?
        obj_check = self._check_objective(description, result)
        checks.append(("Objective Met", obj_check['passed'], obj_check['notes']))
        score += 1.0 if obj_check['passed'] else 0.3
        if not obj_check['passed']:
            corrections['objective'] = obj_check['correction']
            
        # Check 2: Is evidence-based?
        evidence_check = self._check_evidence(result)
        checks.append(("Evidence-Based", evidence_check['passed'], evidence_check['notes']))
        score += 1.0 if evidence_check['passed'] else 0.5
        
        # Check 3: Risks identified?
        risk_check = self._check_risks(result)
        checks.append(("Risks Identified", risk_check['passed'], risk_check['notes']))
        score += 1.0 if risk_check['passed'] else 0.5
        if risk_check['risks']:
            risks.extend(risk_check['risks'])
            
        # Check 4: Teaching occurred?
        teach_check = self._check_teaching(result)
        checks.append(("Teaching Included", teach_check['passed'], teach_check['notes']))
        score += 1.0 if teach_check['passed'] else 0.7
        if not teach_check['passed']:
            recommendations.append("Add explanatory notes to improve user understanding")
            
        # Check 5: Long-term goals considered?
        goals_check = self._check_goals(description, result)
        checks.append(("Goals Aligned", goals_check['passed'], goals_check['notes']))
        score += 1.0 if goals_check['passed'] else 0.6
        
        # Calculate confidence
        confidence = score / 5.0
        approved = confidence >= 0.7
        
        # Build verification notes
        notes_lines = ["\n=== VERIFICATION REPORT ==="]
        for check_name, passed, note in checks:
            status = "✓" if passed else "✗"
            notes_lines.append(f"[{status}] {check_name}: {note}")
        
        notes_lines.append(f"\nOverall Confidence: {confidence:.1%}")
        notes_lines.append(f"Status: {'APPROVED' if approved else 'NEEDS REVISION'}")
        
        if risks:
            notes_lines.append("\nRisks Identified:")
            for r in risks:
                notes_lines.append(f"  ⚠ {r}")
                
        if recommendations:
            notes_lines.append("\nRecommendations:")
            for rec in recommendations:
                notes_lines.append(f"  → {rec}")
        
        notes = "\n".join(notes_lines)
        print(notes)
        
        result_obj = VerificationResult(
            approved=approved,
            confidence=confidence,
            notes=notes,
            corrections=corrections if corrections else None,
            recommendations=recommendations if recommendations else None,
            risks_identified=risks if risks else None
        )
        
        # Store in history
        self.verification_history.append({
            'task_id': task_id,
            'confidence': confidence,
            'approved': approved
        })
        
        return result_obj
    
    def _check_objective(self, description: str, result: Dict) -> Dict:
        """Check if the real objective was understood and met."""
        result_desc = result.get('description', '')
        deliverables = result.get('deliverables', [])
        
        # Simple heuristic: does result mention completion of described task?
        key_terms = [w.lower() for w in description.split() if len(w) > 4]
        result_lower = result_desc.lower() + ' ' + ' '.join(deliverables).lower()
        
        matches = sum(1 for term in key_terms if term in result_lower)
        coverage = matches / len(key_terms) if key_terms else 0
        
        if coverage >= 0.5:
            return {
                'passed': True,
                'notes': f"Objective coverage: {coverage:.0%}. Core intent addressed."
            }
        else:
            return {
                'passed': False,
                'notes': f"Objective coverage: {coverage:.0%}. May have misunderstood goal.",
                'correction': 'Re-examine original request and ensure deliverables match intent'
            }
    
    def _check_evidence(self, result: Dict) -> Dict:
        """Check if work is evidence-based vs assumed."""
        has_sources = bool(result.get('sources') or result.get('evidence'))
        has_verification = result.get('verified', False)
        
        if has_sources and has_verification:
            return {
                'passed': True,
                'notes': 'Work backed by sources and verification steps'
            }
        elif has_sources:
            return {
                'passed': True,
                'notes': 'Sources cited, consider adding explicit verification'
            }
        else:
            return {
                'passed': False,
                'notes': 'Limited evidence/sources cited. Consider: citations, test results, file references'
            }
    
    def _check_risks(self, result: Dict) -> Dict:
        """Check if risks were identified."""
        risks = result.get('risks', [])
        warnings = result.get('warnings', [])
        all_risks = risks + warnings
        
        return {
            'passed': len(all_risks) > 0,
            'notes': f"{len(all_risks)} risk(s) identified" if all_risks else "No risks documented",
            'risks': all_risks
        }
    
    def _check_teaching(self, result: Dict) -> Dict:
        """Check if teaching/explanation occurred."""
        has_explanation = bool(
            result.get('explanation') or 
            result.get('notes') or
            result.get('how_to_use') or
            len(result.get('description', '')) > 100
        )
        
        return {
            'passed': has_explanation,
            'notes': 'Explanation/teaching included' if has_explanation else 'Minimal explanation - user may not learn from this'
        }
    
    def _check_goals(self, description: str, result: Dict) -> Dict:
        """Check alignment with long-term goals."""
        # Load from memory if available
        goals = self.goals_memory.get('active', [])
        
        if not goals:
            return {
                'passed': True,
                'notes': 'No active long-term goals tracked - pass ( Goals can be set via remember_goal() )'
            }
        
        # Check if result mentions any goal keywords
        result_text = json.dumps(result).lower()
        aligned = any(g.lower() in result_text for g in goals)
        
        return {
            'passed': aligned,
            'notes': 'Aligned with tracked goals' if aligned else 'May not advance long-term objectives'
        }
    
    def request_clarification(self, task_id: str, question: str, 
                            context: Optional[str] = None) -> str:
        """Ask the orchestrator for clarification."""
        print(f"\n[ASSISTANT CLARIFY] Task {task_id}")
        print(f"  Q: {question}")
        if context:
            print(f"  Context: {context}")
        
        # This would normally message back to orchestrator
        # For now, return the question for display
        return question
    
    def audit_orchestrator(self, decisions: List[Dict]) -> Dict:
        """
        Audit the Main AI (orchestrator) decisions.
        Check for: bias, missed alternatives, forgotten commitments
        """
        audit = {
            'timestamp': __import__('datetime').datetime.now().isoformat(),
            'decisions_reviewed': len(decisions),
            'concerns': [],
            'recommendations': []
        }
        
        for decision in decisions:
            # Check if alternatives were considered
            if not decision.get('alternatives_considered'):
                audit['concerns'].append(
                    f"Decision {decision.get('id')} lacks documented alternatives"
                )
            
            # Check if user preferences respected
            if decision.get('overrides_user_pref'):
                audit['concerns'].append(
                    f"Decision {decision.get('id')} may override known user preference"
                )
                
        return audit
    
    def remember_goal(self, goal: str, priority: str = "medium"):
        """Track a long-term goal."""
        if 'active' not in self.goals_memory:
            self.goals_memory['active'] = []
        self.goals_memory['active'].append({'goal': goal, 'priority': priority})
        print(f"[ASSISTANT] Goal tracked: {goal} ({priority})")
    
    def suggest_next_step(self, current_task: Optional[str] = None) -> Optional[str]:
        """Suggest what to do next based on state."""
        pending = len([v for v in self.verification_history if not v['approved']])
        
        if pending > 0:
            return f"Address {pending} rejected task(s) awaiting revision"
        
        if not current_task:
            return "No active task - what would you like to build?"
        
        return None

# Integration with orchestrator
def create_assistant_agent(orchestrator=None) -> AssistantAgent:
    return AssistantAgent(orchestrator)

if __name__ == "__main__":
    # Demo
    agent = AssistantAgent()
    
    # Example verification
    test_result = {
        'description': 'Created Python script for file processing',
        'deliverables': ['/root/test_script.py'],
        'verified': True,
        'sources': ['Python docs', 'Stack Overflow'],
        'explanation': 'Script uses argparse for CLI and handles errors',
        'risks': ['Large files may cause memory issues']
    }
    
    result = agent.verify_task("TASK001", "Create a file processing script", test_result)
    print(f"\nFinal: {'APPROVED' if result.approved else 'REJECTED'} ({result.confidence:.0%} confidence)")

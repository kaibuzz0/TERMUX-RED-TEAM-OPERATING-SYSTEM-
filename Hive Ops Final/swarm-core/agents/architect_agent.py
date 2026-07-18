#!/usr/bin/env python3
"""
Architect Agent - Code Review & Design Approval

This agent focuses on:
1. Structural integrity of code
2. Design pattern compliance
3. Security review
4. Performance considerations
5. Maintainability assessment
6. Cross-referencing with existing codebase
"""
import json
import sys
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import ast

@dataclass
class CodeReview:
    file_path: str
    issues: List[Dict]
    score: float  # 0.0 - 1.0
    approved: bool
    security_concerns: List[str]
    performance_notes: List[str]
    design_patterns: List[str]
    recommendations: List[str]

class ArchitectAgent:
    """
    The Architect ensures code quality at the structural level.
    
    Responsibilities:
    - Structural integrity
    - Security vulnerabilities
    - Performance anti-patterns
    - Maintainability
    - Consistency with existing codebase
    """
    
    SECURITY_PATTERNS = {
        'eval_usage': r'\beval\s*\(',
        'exec_usage': r'\bexec\s*\(',
        'shell_injection': r'os\.system|subprocess\.call.*shell\s*=\s*True',
        'hardcoded_secrets': r'(password|secret|key|token)\s*=\s*["\'][^"\']+["\']',
        'pickle_usage': r'pickle\.(load|loads)',
        'yaml_load': r'yaml\.load\s*\(',
    }
    
    PERFORMANCE_PATTERNS = {
        'list_concat_in_loop': r'for.*\+\s*\[',  # list += [item] in loops
        'repeated_string_concat': r'\+\s*["\']',  # str1 + str2 + str3
        'no_generator': r'list\([^)]*for',  # list(x for x in y) vs (x for x in y)
    }
    
    def __init__(self, codebase_root: str = "/root/hive-swarm"):
        self.codebase_root = Path(codebase_root)
        self.existing_patterns: Dict[str, List[str]] = {}
        self._index_existing_code()
    
    def _index_existing_code(self):
        """Index existing codebase for consistency checks."""
        for py_file in self.codebase_root.rglob("*.py"):
            try:
                with open(py_file) as f:
                    content = f.read()
                    self.existing_patterns[str(py_file)] = self._extract_patterns(content)
            except Exception:
                pass
    
    def _extract_patterns(self, code: str) -> List[str]:
        """Extract structural patterns from code."""
        patterns = []
        
        # Class definitions
        for match in re.finditer(r'class\s+(\w+)', code):
            patterns.append(f"class:{match.group(1)}")
        
        # Function definitions
        for match in re.finditer(r'def\s+(\w+)', code):
            patterns.append(f"func:{match.group(1)}")
        
        # Import patterns
        for match in re.finditer(r'^(?:from|import)\s+([\w.]+)', code, re.M):
            patterns.append(f"import:{match.group(1)}")
        
        return patterns
    
    def review_code(self, file_path: str, code: str) -> CodeReview:
        """
        Perform comprehensive code review.
        """
        print(f"\n[ARCHITECT] Reviewing {file_path}...")
        
        issues = []
        score = 1.0
        security = []
        performance = []
        design = []
        recommendations = []
        
        # Security scan
        sec_result = self._security_scan(code)
        if sec_result['issues']:
            security.extend(sec_result['issues'])
            score -= len(sec_result['issues']) * 0.15
        
        # Performance scan
        perf_result = self._performance_scan(code)
        if perf_result['issues']:
            performance.extend(perf_result['issues'])
            score -= len(perf_result['issues']) * 0.05
        
        # Structure analysis
        struct_result = self._structure_analysis(code)
        issues.extend(struct_result['issues'])
        design.extend(struct_result['patterns'])
        score -= len(struct_result['issues']) * 0.1
        
        # Consistency check
        cons_result = self._consistency_check(code)
        if cons_result['deviations']:
            recommendations.extend(cons_result['deviations'])
            score -= len(cons_result['deviations']) * 0.05
        
        # Syntax validation
        syntax_ok = self._validate_syntax(code)
        if not syntax_ok:
            issues.append({
                'severity': 'critical',
                'line': 0,
                'message': 'Syntax error - code will not execute'
            })
            score = 0.0
        
        # Normalize score
        score = max(0.0, min(1.0, score))
        approved = score >= 0.7 and not any(i['severity'] == 'critical' for i in issues)
        
        review = CodeReview(
            file_path=file_path,
            issues=issues,
            score=score,
            approved=approved,
            security_concerns=security,
            performance_notes=performance,
            design_patterns=design,
            recommendations=recommendations
        )
        
        self._print_review(review)
        return review
    
    def _security_scan(self, code: str) -> Dict:
        """Scan for security issues."""
        issues = []
        
        for pattern_name, pattern in self.SECURITY_PATTERNS.items():
            for match in re.finditer(pattern, code, re.IGNORECASE):
                line_num = code[:match.start()].count('\n') + 1
                issues.append(f"{pattern_name} at line {line_num}")
        
        return {'issues': issues}
    
    def _performance_scan(self, code: str) -> Dict:
        """Scan for performance anti-patterns."""
        issues = []
        
        for pattern_name, pattern in self.PERFORMANCE_PATTERNS.items():
            for match in re.finditer(pattern, code):
                line_num = code[:match.start()].count('\n') + 1
                issues.append(f"{pattern_name} at line {line_num}")
        
        # Check function length
        func_lengths = self._get_function_lengths(code)
        for func, lines in func_lengths.items():
            if lines > 50:
                issues.append(f"Function '{func}' is {lines} lines (consider refactoring)")
        
        return {'issues': issues}
    
    def _get_function_lengths(self, code: str) -> Dict[str, int]:
        """Get lengths of all functions in code."""
        lengths = {}
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_code = code[node.lineno-1:node.end_lineno]
                    lengths[node.name] = node.end_lineno - node.lineno + 1
        except:
            pass
        return lengths
    
    def _structure_analysis(self, code: str) -> Dict:
        """Analyze code structure."""
        issues = []
        patterns = []
        
        try:
            tree = ast.parse(code)
            
            # Check for docstrings
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Module)):
                    has_doc = False
                    if isinstance(node, ast.Module):
                        has_doc = ast.get_docstring(node) is not None
                    else:
                        has_doc = ast.get_docstring(node) is not None
                    
                    if not has_doc and isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                        issues.append({
                            'severity': 'minor',
                            'line': node.lineno,
                            'message': f"{type(node).__name__} '{node.name}' lacks docstring"
                        })
            
            # Check complexity
            func_complexity = self._analyze_complexity(tree)
            for func, complexity in func_complexity.items():
                if complexity > 10:
                    issues.append({
                        'severity': 'warning',
                        'line': 0,
                        'message': f"Function '{func}' has complexity {complexity} (consider refactoring)"
                    })
            
            # Identify patterns
            patterns = self._identify_patterns(tree)
            
        except SyntaxError as e:
            issues.append({
                'severity': 'critical',
                'line': e.lineno or 0,
                'message': f"Syntax error: {e.msg}"
            })
        
        return {'issues': issues, 'patterns': patterns}
    
    def _analyze_complexity(self, tree: ast.AST) -> Dict[str, int]:
        """Calculate cyclomatic complexity per function."""
        complexity = {}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                count = 1  # Base complexity
                for child in ast.walk(node):
                    if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                        count += 1
                    elif isinstance(child, ast.BoolOp):
                        count += len(child.values) - 1
                complexity[node.name] = count
        
        return complexity
    
    def _identify_patterns(self, tree: ast.AST) -> List[str]:
        """Identify design patterns used."""
        patterns = []
        
        # Check for Singleton
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                has_instance = any(
                    isinstance(n, ast.Assign) and 
                    any(t.id == '_instance' for t in ast.walk(n) if isinstance(t, ast.Name))
                    for n in node.body
                )
                if has_instance:
                    patterns.append(f"Singleton:{node.name}")
                
                # Check for Factory
                if 'create' in node.name.lower():
                    patterns.append(f"Factory:{node.name}")
        
        return patterns
    
    def _consistency_check(self, code: str) -> Dict:
        """Check consistency with existing codebase."""
        deviations = []
        
        # Check import style
        if 'from typing import' in code:
            import_style = 'direct'
        else:
            import_style = 'module'
        
        # Check naming conventions
        if re.search(r'def [A-Z]', code):
            deviations.append("Function names use PascalCase (should be snake_case)")
        
        if re.search(r'class [a-z]', code):
            deviations.append("Class names use snake_case (should be PascalCase)")
        
        return {'deviations': deviations}
    
    def _validate_syntax(self, code: str) -> bool:
        """Validate Python syntax."""
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False
    
    def _print_review(self, review: CodeReview):
        """Print review results."""
        print("\n=== ARCHITECT REVIEW ===")
        print(f"File: {review.file_path}")
        print(f"Score: {review.score:.0%}")
        print(f"Status: {'APPROVED' if review.approved else 'REJECTED'}")
        
        if review.security_concerns:
            print("\n🔒 Security Concerns:")
            for c in review.security_concerns:
                print(f"  ⚠ {c}")
        
        if review.performance_notes:
            print("\n⚡ Performance Notes:")
            for n in review.performance_notes:
                print(f"  → {n}")
        
        if review.issues:
            print("\n📋 Issues:")
            for i in review.issues:
                icon = "🔴" if i['severity'] == 'critical' else "🟡" if i['severity'] == 'warning' else "🔵"
                print(f"  {icon} Line {i['line']}: {i['message']}")
        
        if review.design_patterns:
            print("\n🏗️ Design Patterns Detected:")
            for p in review.design_patterns:
                print(f"  ✓ {p}")
        
        if review.recommendations:
            print("\n💡 Recommendations:")
            for r in review.recommendations:
                print(f"  → {r}")
        
        print("=" * 40)
    
    def approve_architecture(self, component: str, design_doc: Dict) -> Tuple[bool, List[str]]:
        """
        Approve high-level architecture design.
        """
        print(f"\n[ARCHITECT] Reviewing architecture for {component}...")
        
        concerns = []
        
        # Check required sections
        required = ['purpose', 'interfaces', 'dependencies', 'failure_modes']
        for section in required:
            if section not in design_doc:
                concerns.append(f"Missing required section: {section}")
        
        # Check dependency circularity
        deps = design_doc.get('dependencies', [])
        if component in deps:
            concerns.append(f"Circular dependency detected: {component} depends on itself")
        
        approved = len(concerns) == 0
        
        if approved:
            print(f"✓ Architecture for {component} APPROVED")
        else:
            print(f"✗ Architecture for {component} REJECTED:")
            for c in concerns:
                print(f"  - {c}")
        
        return approved, concerns

# Integration
def create_architect_agent(codebase_root: str = "/root/hive-swarm") -> ArchitectAgent:
    return ArchitectAgent(codebase_root)

if __name__ == "__main__":
    # Demo
    agent = ArchitectAgent()
    
    test_code = '''
def process_data(data):
    """Process input data."""
    result = []
    for item in data:
        result = result + [item * 2]  # Performance issue
    return result

class DataProcessor:
    def __init__(self):
        self.data = []
    
    def Process(self, x):  # Naming issue
        eval(x)  # Security issue!
'''
    
    review = agent.review_code("/root/test.py", test_code)
    print(f"\nFinal: {'APPROVED' if review.approved else 'REJECTED'}")

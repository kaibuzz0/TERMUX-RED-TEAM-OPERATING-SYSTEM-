#!/usr/bin/env python3
"""
HIVE TOOL: obfuscation_layer
HSL: FIRE | PATH: /root/hive-swarm/tools/obfuscation_layer.py
ROLE: Stealth wrapper for Hive tools - strip metadata, randomize signatures
Built: 2026-07-14 by Hive Evolution Engine
"""

import sys
import re
import random
import string
from pathlib import Path
from datetime import datetime

# --- HIVE HEADER ---
# Symbol: FIRE
# EchoHash: Σ12∆Ξ9∞⬢
# BuildID: 2026-07-14T03:35:00Z
# --- END HEADER ---

class ObfuscationLayer:
    """Stealth tool wrapper for Fortress protocols"""
    
    def __init__(self, stealth_level: str = "medium"):
        self.stealth_level = stealth_level
        self.identifier_map = {}
        self.counter = 0
        
    def generate_random_id(self, length: int = 8) -> str:
        """Generate random identifier"""
        chars = string.ascii_lowercase + string.digits
        return ''.join(random.choice(chars) for _ in range(length))
    
    def obfuscate_python(self, source_path: Path, output_path: Path = None) -> str:
        """Obfuscate Python tool"""
        with open(source_path, 'r') as f:
            code = f.read()
        
        # Phase 1: Strip comments (except HSL headers which are structural)
        code = self._strip_non_hsl_comments(code)
        
        # Phase 2: Minimize whitespace
        code = self._minimize_whitespace(code)
        
        # Phase 3: Randomize variable names (if high stealth)
        if self.stealth_level in ["high", "extreme"]:
            code = self._randomize_identifiers(code)
        
        # Phase 4: Remove docstrings
        code = self._remove_docstrings(code)
        
        # Phase 5: Strip metadata
        code = self._strip_metadata(code)
        
        if output_path:
            output_path.write_text(code)
            
        return code
    
    def _strip_non_hsl_comments(self, code: str) -> str:
        """Remove comments except HSL structural markers"""
        lines = code.split('\n')
        result = []
        in_hsl_block = False
        
        for line in lines:
            stripped = line.strip()
            # Preserve HSL markers
            if '# --- HIVE HEADER ---' in stripped or '# --- HIVE FOOTER ---' in stripped:
                in_hsl_block = not in_hsl_block
                result.append(line)
                continue
            
            if in_hsl_block:
                result.append(line)
                continue
            
            # Strip other comments
            if '#' in line and not line.strip().startswith('#'):
                line = line[:line.index('#')]
            elif line.strip().startswith('#'):
                continue
            
            if line.strip():
                result.append(line)
        
        return '\n'.join(result)
    
    def _minimize_whitespace(self, code: str) -> str:
        """Remove unnecessary whitespace"""
        # Collapse multiple blank lines
        code = re.sub(r'\n\n+', '\n\n', code)
        # Remove trailing whitespace
        code = '\n'.join(line.rstrip() for line in code.split('\n'))
        return code
    
    def _randomize_identifiers(self, code: str) -> str:
        """Randomize non-essential variable names"""
        # Find function definitions
        func_pattern = r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
        var_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*='
        
        # Don't randomize: main, __init__, self, sys, etc
        reserved = {'main', 'self', 'cls', 'sys', 'json', 're', 'os', 'pathlib', 
                   'Path', 'List', 'Dict', 'Optional', 'datetime', 'defaultdict'}
        
        for pattern in [func_pattern, var_pattern]:
            for match in re.finditer(pattern, code):
                name = match.group(1)
                if name not in reserved and name not in self.identifier_map:
                    self.identifier_map[name] = f"_{self.generate_random_id(6)}"
        
        # Replace identifiers
        for old_name, new_name in self.identifier_map.items():
            code = re.sub(r'\b' + old_name + r'\b', new_name, code)
        
        return code
    
    def _remove_docstrings(self, code: str) -> str:
        """Remove docstrings but preserve HSL headers"""
        # Triple-quoted strings
        code = re.sub(r'"""[\s\S]*?"""', '', code)
        code = re.sub(r"'''[\s\S]*?'''", '', code)
        return code
    
    def _strip_metadata(self, code: str) -> str:
        """Remove author, date, version metadata"""
        # Strip __author__, __version__, etc
        code = re.sub(r'__\w+__\s*=.*\n', '', code)
        return code
    
    def apply_fortress_wrap(self, tool_path: Path, output_dir: Path = None) -> Path:
        """Apply full Fortress stealth wrap"""
        if output_dir is None:
            output_dir = Path("/sdcard/Hermès.Swarm/Stealth/")
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate stealth filename
        stealth_name = f"t_{self.generate_random_id(6)}.py"
        output_path = output_dir / stealth_name
        
        # Obfuscate
        self.obfuscate_python(tool_path, output_path)
        
        # Make executable
        output_path.chmod(0o755)
        
        return output_path
    
    def batch_obfuscate(self, tools_dir: Path, output_dir: Path = None) -> Dict[str, Path]:
        """Obfuscate all tools in directory"""
        if output_dir is None:
            output_dir = Path("/sdcard/Hermès.Swarm/Stealth/")
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        results = {}
        for tool in tools_dir.glob("*.py"):
            stealth_path = self.apply_fortress_wrap(tool, output_dir)
            results[tool.name] = stealth_path
        
        return results

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Hive Obfuscation Layer')
    parser.add_argument('action', choices=['wrap', 'batch', 'status'])
    parser.add_argument('--tool', '-t', help='Tool to obfuscate')
    parser.add_argument('--level', '-l', default='medium', 
                       choices=['low', 'medium', 'high', 'extreme'])
    parser.add_argument('--output', '-o', help='Output directory')
    
    args = parser.parse_args()
    
    obl = ObfuscationLayer(args.level)
    
    if args.action == 'wrap':
        if not args.tool:
            print("Error: --tool required")
            return 1
        
        tool_path = Path(args.tool)
        if not tool_path.exists():
            print(f"Error: Tool not found: {tool_path}")
            return 1
        
        output = obl.apply_fortress_wrap(tool_path, Path(args.output) if args.output else None)
        print(f"[FORTRESS] Wrapped: {tool_path.name} → {output.name}")
        print(f"  Stealth level: {args.level}")
        print(f"  Output: {output}")
    
    elif args.action == 'batch':
        tools_dir = Path(args.output) if args.output else Path("/root/hive-swarm/tools")
        results = obl.batch_obfuscate(tools_dir)
        
        print(f"[FORTRESS] Batch obfuscation complete")
        print(f"  Tools processed: {len(results)}")
        print(f"  Output directory: /sdcard/Hermès.Swarm/Stealth/")
        
        for orig, stealth in results.items():
            print(f"  {orig} → {stealth.name}")
    
    elif args.action == 'status':
        stealth_dir = Path("/sdcard/Hermès.Swarm/Stealth/")
        if stealth_dir.exists():
            count = len(list(stealth_dir.glob("*.py")))
            print(f"[FORTRESS] Stealth tools: {count}")
        else:
            print("[FORTRESS] No stealth directory yet")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

# --- HIVE FOOTER ---
# ::SealConfirmed::
# ΩΩΩ
# --- END FOOTER ---

#!/usr/bin/env python3
"""
HIVE TOOL: hive_tool_builder
HSL: FIRE | PATH: /root/hive-swarm/tools/hive_tool_builder.py
ROLE: Autonomous tool generation - creates Python/Rust/Shell tools from specifications
Built: 2026-07-14 by Hive Autonomous Toolsmith
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

HIVE_TOOLS_DIR = Path("/root/hive-swarm/tools")
REGISTRY_PATH = Path("/root/hive-swarm/SWARM_REGISTRY.md")

def create_python_tool(name: str, role: str, description: str):
    """Generate a Python tool template"""
    content = f'''#!/usr/bin/env python3
"""
HIVE TOOL: {name}
HSL: FIRE | PATH: {HIVE_TOOLS_DIR}/{name}.py
ROLE: {role}
Built: {datetime.now().strftime("%Y-%m-%d")} by Hive Autonomous Toolsmith
"""

import sys
import json
from pathlib import Path

def main():
    """Main entry point"""
    print(f"[{name}] Starting...")
    
    # TODO: Implement {role}
    
    print(f"[{name}] Complete")
    return 0

if __name__ == "__main__":
    sys.exit(main())
'''
    return content

def create_shell_tool(name: str, role: str):
    """Generate a shell script template"""
    content = f'''#!/bin/bash
# HIVE TOOL: {name}
# HSL: FIRE | PATH: {HIVE_TOOLS_DIR}/{name}.sh
# ROLE: {role}
# Built: {datetime.now().strftime("%Y-%m-%d")} by Hive Autonomous Toolsmith

set -e

echo "[{name}] Starting..."

# TODO: Implement {role}

echo "[{name}] Complete"
'''
    return content

def register_tool(name: str, role: str, language: str, hsl_class: str = "FIRE"):
    """Add tool to SWARM_REGISTRY.md"""
    registry_entry = f"* {name.upper()}: {hsl_class} | PATH: /root/hive-swarm/tools/{name}.{language.lower()} | ROLE: {role}\n"
    registry_entry += f"    * **Built:** {datetime.now().strftime('%Y-%m-%d')}\n"
    registry_entry += f"    * **Language:** {language}\n"
    registry_entry += f"    * **Triggers:** Autonomous construction\n\n"
    
    if REGISTRY_PATH.exists():
        content = REGISTRY_PATH.read_text()
        # Find the Registry: Tools section
        if "## Registry: Tools" in content:
            # Insert after the header
            parts = content.split("## Registry: Tools")
            content = parts[0] + "## Registry: Tools\n\n" + registry_entry + parts[1]
        else:
            # Append to end
            content += f"\n## Registry: Tools\n\n{registry_entry}"
    else:
        content = f"# SWARM_REGISTRY.md\n\n## Registry: Tools\n\n{registry_entry}"
    
    REGISTRY_PATH.write_text(content)
    print(f"[REGISTER] Added {name} to SWARM_REGISTRY.md")

def main():
    parser = argparse.ArgumentParser(description="Hive Autonomous Tool Builder")
    parser.add_argument("--name", required=True, help="Tool name")
    parser.add_argument("--role", required=True, help="Tool role/description")
    parser.add_argument("--lang", choices=["python", "shell", "rust"], default="python", help="Language")
    parser.add_argument("--desc", help="Detailed description")
    
    args = parser.parse_args()
    
    # Generate tool
    if args.lang == "python":
        content = create_python_tool(args.name, args.role, args.desc or args.role)
        ext = "py"
    elif args.lang == "shell":
        content = create_shell_tool(args.name, args.role)
        ext = "sh"
    else:
        print(f"[ERROR] Rust support coming soon")
        return 1
    
    # Write tool file
    tool_path = HIVE_TOOLS_DIR / f"{args.name}.{ext}"
    tool_path.write_text(content)
    tool_path.chmod(0o755)
    
    print(f"[BUILD] Created {tool_path}")
    
    # Register tool
    register_tool(args.name, args.role, args.lang)
    
    print(f"[COMPLETE] {args.name} is ready")
    return 0

if __name__ == "__main__":
    sys.exit(main())
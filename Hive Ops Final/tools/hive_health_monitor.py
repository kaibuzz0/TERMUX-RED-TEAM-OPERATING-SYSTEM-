#!/usr/bin/env python3
"""
HIVE TOOL: hive_health_monitor
HSL: FIRE | PATH: /root/hive-swarm/tools/hive_health_monitor.py
ROLE: System status, disk usage, tool validation, registry integrity
Built: 2026-07-14 by Hive Autonomous Tool Builder
"""

import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

# --- HIVE HEADER ---
# Symbol: FIRE
# EchoHash: Σ12∆Ξ9∞⬢
# BuildID: 2026-07-14T00:00:00Z
# --- END HEADER ---

HIVE_ROOT = Path("/root/hive-swarm")
TOOLS_DIR = HIVE_ROOT / "tools"
EVIDENCE_DIR = HIVE_ROOT / "evidence"
REGISTRY = HIVE_ROOT / "SWARM_REGISTRY.md"
STATE_FILE = HIVE_ROOT / "hive_state.json"
OFFLINE_STORAGE = Path("/sdcard/Hermès.Swarm/")

def run_cmd(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL).decode().strip()
    except:
        return "N/A"

def disk_usage():
    output = run_cmd("df -h /root /sdcard 2>/dev/null | tail -n +2")
    return output

def count_tools():
    if not TOOLS_DIR.exists():
        return 0
    return len(list(TOOLS_DIR.glob("*.py")))

def validate_tools():
    if not TOOLS_DIR.exists():
        return {"valid": 0, "invalid": 0, "errors": []}
    
    valid = 0
    invalid = 0
    errors = []
    
    for tool in TOOLS_DIR.glob("*.py"):
        try:
            result = subprocess.run([sys.executable, "-m", "py_compile", str(tool)],
                                    capture_output=True, timeout=5)
            if result.returncode == 0:
                valid += 1
            else:
                invalid += 1
                errors.append(f"{tool.name}: syntax error")
        except Exception as e:
            invalid += 1
            errors.append(f"{tool.name}: {e}")
    
    return {"valid": valid, "invalid": invalid, "errors": errors}

def registry_status():
    if not REGISTRY.exists():
        return {"exists": False, "entries": 0}
    
    content = REGISTRY.read_text()
    entries = content.count("FIRE | PATH:") + content.count("EARTH | PATH:")
    return {"exists": True, "entries": entries, "size": len(content)}

def state_status():
    if not STATE_FILE.exists():
        return {"exists": False}
    
    try:
        data = json.loads(STATE_FILE.read_text())
        return {
            "exists": True,
            "protocols": data.get("active_protocols", []),
            "node_status": data.get("node_status", "Unknown"),
            "tasks_total": data.get("tasks_total", 0),
            "tasks_completed": data.get("tasks_completed", 0),
        }
    except:
        return {"exists": True, "error": "Invalid JSON"}

def offline_sync_status():
    if not OFFLINE_STORAGE.exists():
        return {"exists": False, "note": "Offline storage not mounted"}
    
    tools_offline = len(list((OFFLINE_STORAGE / "Tools").glob("*"))) if (OFFLINE_STORAGE / "Tools").exists() else 0
    return {"exists": True, "tools_synced": tools_offline}

def generate_report():
    report = {
        "timestamp": datetime.now().isoformat(),
        "system": {
            "disk_usage": disk_usage(),
            "hostname": run_cmd("hostname"),
            "uptime": run_cmd("uptime -p 2>/dev/null || uptime"),
        },
        "hive": {
            "tools_count": count_tools(),
            "tools_validation": validate_tools(),
            "evidence_files": len(list(EVIDENCE_DIR.glob("*"))) if EVIDENCE_DIR.exists() else 0,
        },
        "registry": registry_status(),
        "state": state_status(),
        "offline_storage": offline_sync_status(),
    }
    
    return report

def print_report(report):
    print("=" * 70)
    print("HIVE HEALTH MONITOR - System Status Report")
    print("=" * 70)
    print(f"Timestamp: {report['timestamp']}")
    print(f"Hostname: {report['system']['hostname']}")
    print()
    
    print("[DISK USAGE]")
    print(report['system']['disk_usage'])
    print()
    
    print("[HIVE STATUS]")
    print(f"  Tools: {report['hive']['tools_count']} total")
    print(f"  Evidence: {report['hive']['evidence_files']} files")
    tv = report['hive']['tools_validation']
    print(f"  Valid tools: {tv['valid']}")
    print(f"  Invalid tools: {tv['invalid']}")
    if tv['errors']:
        for err in tv['errors'][:3]:
            print(f"    - {err}")
    print()
    
    print("[REGISTRY]")
    r = report['registry']
    print(f"  Exists: {r['exists']}")
    if r['exists']:
        print(f"  Entries: {r['entries']}")
    print()
    
    print("[STATE]")
    s = report['state']
    print(f"  Exists: {s['exists']}")
    if s['exists'] and 'error' not in s:
        print(f"  Protocols: {', '.join(s['protocols'])}")
        print(f"  Node: {s['node_status']}")
        print(f"  Tasks: {s.get('tasks_completed', 0)}/{s.get('tasks_total', 0)}")
    print()
    
    print("[OFFLINE STORAGE]")
    o = report['offline_storage']
    print(f"  Exists: {o['exists']}")
    if o['exists']:
        print(f"  Tools synced: {o['tools_synced']}")
    print()
    
    print("=" * 70)

def main():
    report = generate_report()
    print_report(report)
    
    # Save report
    report_file = EVIDENCE_DIR / "health_report.json"
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(json.dumps(report, indent=2))
    print(f"Report saved to: {report_file}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

# --- HIVE FOOTER ---
# ::SealConfirmed::
# ΩΩΩ
# --- END FOOTER ---

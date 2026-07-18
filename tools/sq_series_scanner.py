#!/usr/bin/env python3
"""
HIVE TOOL: sq_series_scanner
HSL: FIRE | PATH: /root/hive-swarm/tools/sq_series_scanner.py
ROLE: Scans ALL Space Quest games (SQ1-6) for Bitcoin hidden features, Genesis Frequency patterns, and wallet construction code
Built: 2026-07-14 by Hive Autonomous Toolsmith

Usage:
  python3 sq_series_scanner.py /path/to/space-quest-series/
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Import our existing tools
sys.path.insert(0, '/root/hive-swarm/tools')

# Genesis Frequency constants
GENESIS_CONSTANTS = {
    "block_time_600s": 0x0258,
    "blocks_per_day_144": 0x0090,
    "genesis_reward_50": 0x0032,
    "signature_42": 0x2A,
}

# SCI script patterns to search
SCI_PATTERNS = {
    "selector_0x0C": b'\x4a\x0c',  # SEND 0x0C (wallet construction)
    "selector_0x04": b'\x4a\x04',  # Standard call
    "stack_transform": b'\x32\x3f',  # Branch gate
    "push_600": b'\x02\x58',  # 600 in little-endian
    "push_144": b'\x00\x90',  # 144 in little-endian
}

def scan_sci_script(file_path: Path):
    """Scan a single SCI script for Bitcoin patterns"""
    try:
        content = file_path.read_bytes()
    except Exception as e:
        return {"error": str(e)}
    
    results = {
        "file": str(file_path),
        "size": len(content),
        "patterns_found": {},
        "genesis_constants": {},
        "bitcoin_score": 0
    }
    
    # Search for SCI selector patterns
    for name, pattern in SCI_PATTERNS.items():
        count = content.count(pattern)
        if count > 0:
            results["patterns_found"][name] = count
            results["bitcoin_score"] += count * 10
    
    # Search for Genesis constants
    for name, value in GENESIS_CONSTANTS.items():
        pattern_le = value.to_bytes(2, 'little')
        pattern_be = value.to_bytes(2, 'big')
        
        count_le = content.count(pattern_le)
        count_be = content.count(pattern_be)
        total = count_le + count_be
        
        if total > 0:
            results["genesis_constants"][name] = {
                "value": f"0x{value:04X}",
                "count_le": count_le,
                "count_be": count_be,
                "total": total
            }
            results["bitcoin_score"] += total * 15
    
    # Look for 0x5788 variable (wallet storage)
    var_5788 = b'\x57\x88'
    if var_5788 in content:
        count = content.count(var_5788)
        results["patterns_found"]["variable_0x5788"] = count
        results["bitcoin_score"] += count * 50  # High value!
    
    # Look for 0x9E variable (crypto engine receiver)
    var_9E = b'\x00\x9e'
    if var_9E in content:
        count = content.count(var_9E)
        results["patterns_found"]["variable_0x9E"] = count
        results["bitcoin_score"] += count * 25
    
    return results

def scan_game_directory(game_path: Path, game_name: str):
    """Scan all SCI scripts in a game directory"""
    print(f"\n{'='*70}")
    print(f"SCANNING: {game_name}")
    print(f"Path: {game_path}")
    print(f"{'='*70}")
    
    results = {
        "game": game_name,
        "path": str(game_path),
        "scripts_scanned": 0,
        "scripts_with_patterns": 0,
        "total_bitcoin_score": 0,
        "findings": []
    }
    
    # Find all .SCR files
    scr_files = list(game_path.glob("*.SCR")) + list(game_path.glob("*.scr"))
    
    if not scr_files:
        # Try subdirectories
        scr_files = list(game_path.rglob("*.SCR")) + list(game_path.rglob("*.scr"))
    
    print(f"\nFound {len(scr_files)} SCI script files")
    
    for scr_file in sorted(scr_files):
        script_results = scan_sci_script(scr_file)
        results["scripts_scanned"] += 1
        
        if script_results.get("bitcoin_score", 0) > 0:
            results["scripts_with_patterns"] += 1
            results["total_bitcoin_score"] += script_results["bitcoin_score"]
            results["findings"].append(script_results)
            
            print(f"\n  ★ {scr_file.name}:")
            print(f"      Score: {script_results['bitcoin_score']}")
            if script_results.get("patterns_found"):
                print(f"      Patterns: {script_results['patterns_found']}")
            if script_results.get("genesis_constants"):
                print(f"      Genesis: {list(script_results['genesis_constants'].keys())}")
    
    return results

def generate_series_report(all_results: list, output_path: Path):
    """Generate comprehensive series-wide report"""
    report = {
        "scan_date": datetime.now().isoformat(),
        "games_analyzed": len(all_results),
        "summary": {
            "total_scripts": sum(r["scripts_scanned"] for r in all_results),
            "scripts_with_patterns": sum(r["scripts_with_patterns"] for r in all_results),
            "highest_scoring_game": None,
            "total_series_score": sum(r["total_bitcoin_score"] for r in all_results)
        },
        "game_results": all_results
    }
    
    # Find highest scoring game
    if all_results:
        highest = max(all_results, key=lambda x: x["total_bitcoin_score"])
        report["summary"]["highest_scoring_game"] = {
            "name": highest["game"],
            "score": highest["total_bitcoin_score"]
        }
    
    # Write report
    output_path.write_text(json.dumps(report, indent=2))
    print(f"\n{'='*70}")
    print(f"SERIES REPORT SAVED TO: {output_path}")
    print(f"{'='*70}")
    
    return report

def main():
    print("="*70)
    print("SPACE QUEST SERIES - BITCOIN FEATURE SCANNER")
    print("Scanning SQ1-6 for Genesis Frequency patterns and wallet code")
    print("="*70)
    
    # Default path
    base_path = Path("/root/hive-swarm/space-quest-series")
    
    if not base_path.exists():
        print(f"[ERROR] Base path not found: {base_path}")
        print("Please extract Space Quest games to this directory first.")
        return 1
    
    all_results = []
    
    # Scan each game
    games = [
        ("SQI", "Space Quest I - The Sarien Encounter (1986)"),
        ("SQII", "Space Quest II - Vohaul's Revenge (1987)"),
        ("SQIII", "Space Quest III - The Pirates of Pestulon (1989)"),
        ("SQIV", "Space Quest IV - Roger Wilco and the Time Rippers (1991)"),
        ("SQV", "Space Quest V - The Next Mutation (1993)"),
        ("SQVI", "Space Quest VI - Roger Wilco in the Spinal Frontier (1995)"),
    ]
    
    for dir_name, game_name in games:
        game_path = base_path / dir_name
        if game_path.exists():
            results = scan_game_directory(game_path, game_name)
            all_results.append(results)
        else:
            print(f"\n[SKIP] {game_name} - directory not found")
    
    # Generate report
    report_path = base_path / "series_analysis_report.json"
    report = generate_series_report(all_results, report_path)
    
    # Print summary
    print(f"\n{'='*70}")
    print("SERIES SUMMARY")
    print(f"{'='*70}")
    print(f"Games Analyzed: {len(all_results)}")
    print(f"Total Scripts: {report['summary']['total_scripts']}")
    print(f"Scripts with Bitcoin Patterns: {report['summary']['scripts_with_patterns']}")
    print(f"Total Series Score: {report['summary']['total_series_score']}")
    
    if report['summary']['highest_scoring_game']:
        hg = report['summary']['highest_scoring_game']
        print(f"\n★ HIGHEST SCORING: {hg['name']} (Score: {hg['score']})")
    
    print(f"\n{'='*70}")
    print("SCAN COMPLETE")
    print(f"{'='*70}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
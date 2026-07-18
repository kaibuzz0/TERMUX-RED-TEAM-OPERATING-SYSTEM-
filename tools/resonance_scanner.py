#!/usr/bin/env python3
"""
HIVE TOOL: resonance_scanner
HSL: FIRE | PATH: /root/hive-swarm/tools/resonance_scanner.py
ROLE: Scans data streams for Genesis Frequency patterns (600s, 144 blocks) and resonance triggers
Built: 2026-07-14 by Hive Autonomous Toolsmith
"""

import sys
import json
from pathlib import Path
from collections import Counter

# Genesis Frequency constants
GENESIS_CONSTANTS = {
    "block_time_600s": 0x0258,      # 600 seconds = Bitcoin block target
    "blocks_per_day_144": 0x0090,   # ~144 blocks per day
    "genesis_reward_50": 0x32,       # 50 BTC genesis block reward
    "signature_42": 0x2A,            # 42-byte structural delta
}

def scan_hex_stream(hex_data: str):
    """Scan hex stream for Genesis Frequency patterns"""
    raw = bytes.fromhex(hex_data.replace(" ", "").replace("\n", ""))
    
    results = {
        "total_bytes": len(raw),
        "constants_found": {},
        "byte_frequency": {},
        "resonance_score": 0
    }
    
    # Search for Genesis constants
    for name, value in GENESIS_CONSTANTS.items():
        pattern_be_16 = value.to_bytes(2, 'big') if value <= 0xFFFF else None
        pattern_le_16 = value.to_bytes(2, 'little') if value <= 0xFFFF else None
        
        found_offsets = []
        for offset in range(len(raw) - 1):
            if pattern_be_16 and raw[offset:offset+2] == pattern_be_16:
                found_offsets.append(f"0x{offset:04x} (BE)")
            if pattern_le_16 and raw[offset:offset+2] == pattern_le_16:
                found_offsets.append(f"0x{offset:04x} (LE)")
        
        if found_offsets:
            results["constants_found"][name] = {
                "value": f"0x{value:04X}",
                "occurrences": len(found_offsets),
                "offsets": found_offsets[:10]  # Limit to first 10
            }
            results["resonance_score"] += len(found_offsets) * 10
    
    # Byte frequency analysis
    byte_freq = Counter(raw)
    results["byte_frequency"] = {
        f"0x{b:02X}": count 
        for b, count in byte_freq.most_common(10)
    }
    
    # Check for 42 signature
    count_42 = raw.count(0x2A)
    if count_42 > 0:
        results["constants_found"]["signature_42"] = {
            "value": "0x2A",
            "occurrences": count_42,
            "note": "42-byte structural delta signature"
        }
        results["resonance_score"] += count_42 * 25
    
    return results

def scan_file(file_path: str):
    """Scan a file for Genesis Frequency patterns"""
    path = Path(file_path)
    if not path.exists():
        return {"error": f"File not found: {file_path}"}
    
    content = path.read_text()
    
    # Extract hex data - look for long hex strings
    import re
    # Find hex strings that are at least 100 chars
    hex_pattern = r'[0-9a-fA-F]{100,}'
    matches = re.findall(hex_pattern, content)
    
    if not matches:
        return {"error": "No hex data found in file"}
    
    # Combine all hex matches
    hex_data = "".join(matches)
    print(f"[EXTRACT] Found {len(matches)} hex strings, total {len(hex_data)} chars")
    
    return scan_hex_stream(hex_data)

def main():
    print("="*60)
    print("HIVE RESONANCE SCANNER - Genesis Frequency Detection")
    print("="*60)
    
    # Default: scan memory dump
    default_file = "/root/hive-swarm/evidence/memory_dump_0x3909.log"
    
    if len(sys.argv) > 1:
        target = sys.argv[1]
    else:
        target = default_file
        print(f"\n[SCAN] Using default target: {target}")
    
    path = Path(target)
    if path.exists():
        print(f"[SCAN] Scanning file: {target}")
        results = scan_file(target)
    else:
        print(f"[SCAN] Treating as hex string...")
        results = scan_hex_stream(target)
    
    if "error" in results:
        print(f"[ERROR] {results['error']}")
        return 1
    
    # Output results
    print(f"\n[RESULTS]")
    print(f"  Total bytes analyzed: {results['total_bytes']}")
    print(f"  Resonance score: {results['resonance_score']}")
    
    print(f"\n[GENESIS CONSTANTS FOUND]")
    for name, data in results["constants_found"].items():
        print(f"  ✓ {name}: {data['value']} ({data['occurrences']}x)")
        for offset in data.get("offsets", [])[:5]:
            print(f"      - {offset}")
    
    print(f"\n[TOP 10 BYTE FREQUENCY]")
    for byte, count in results["byte_frequency"].items():
        pct = count / results["total_bytes"] * 100
        print(f"  {byte}: {count} ({pct:.1f}%)")
    
    # Resonance assessment
    print(f"\n[RESONANCE ASSESSMENT]")
    if results["resonance_score"] >= 100:
        print("  ★ HIGH RESONANCE - Strong Genesis Frequency presence")
    elif results["resonance_score"] >= 50:
        print("  ● MODERATE RESONANCE - Some Genesis patterns detected")
    else:
        print("  ○ LOW RESONANCE - Few or no Genesis patterns found")
    
    # Save results
    output_path = Path("/root/hive-swarm/evidence/resonance_scan_results.json")
    output_path.write_text(json.dumps(results, indent=2))
    print(f"\n[SAVE] Results written to: {output_path}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
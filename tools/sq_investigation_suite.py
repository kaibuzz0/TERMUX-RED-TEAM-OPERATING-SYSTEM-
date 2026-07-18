#!/usr/bin/env python3
"""
HIVE TOOL: sq_investigation_suite
HSL: FIRE | PATH: /root/hive-swarm/tools/sq_investigation_suite.py
ROLE: Consolidated Space Quest investigation toolkit
Built: 2026-07-14 by Hive Evolution Engine

Consolidates: sq_series_scanner, series_comparator, sqvi_deep_scanner
"""

import sys
import json
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# --- HIVE HEADER ---
# Symbol: FIRE
# EchoHash: Σ12∆Ξ9∞⬢
# BuildID: 2026-07-14T03:35:00Z
# --- END HEADER ---

class SpaceQuestInvestigationSuite:
    """Unified Space Quest Bitcoin Archaeology toolkit"""
    
    def __init__(self, base_path: str = "/sdcard/Hermès.Upload"):
        self.base_path = Path(base_path)
        self.results = {}
        
    def scan_script(self, script_path: Path) -> Dict:
        """Comprehensive single-script analysis"""
        if not script_path.exists():
            return {"error": f"File not found: {script_path}"}
        
        data = script_path.read_bytes()
        
        # Pattern detection
        patterns = {
            'selector_0x0C': len(re.findall(b'\x4a\x0c', data)),
            'selector_0x04': len(re.findall(b'\x4a\x04', data)),
            'genesis_600': len(re.findall(b'\x58\x02', data)),  # 0x0258 LE
            'genesis_144': len(re.findall(b'\x90\x00', data)),  # 0x0090 LE
            'genesis_50': len(re.findall(b'\x32\x00', data)),   # 0x0032 LE
            'byte_42': data.count(0x2A),
            'hex_4A': data.count(0x4A),
        }
        
        # Calculate score
        score = (
            patterns['selector_0x0C'] * 100 +
            patterns['selector_0x04'] * 50 +
            patterns['genesis_600'] * 25 +
            patterns['genesis_144'] * 25 +
            patterns['genesis_50'] * 25 +
            patterns['byte_42'] * 10
        )
        
        return {
            'file': str(script_path),
            'size': len(data),
            'patterns': patterns,
            'bitcoin_score': score,
            'entropy': self._calculate_entropy(data),
            'header_type': self._detect_header_type(data)
        }
    
    def _calculate_entropy(self, data: bytes) -> float:
        """Calculate Shannon entropy"""
        if not data:
            return 0.0
        entropy = 0.0
        for x in range(256):
            p_x = float(data.count(x)) / len(data)
            if p_x > 0:
                entropy += -p_x * (p_x.bit_length() - 1)  # log2 approximation
        return entropy
    
    def _detect_header_type(self, data: bytes) -> str:
        """Detect SCI header type"""
        size = len(data)
        if size % 42 == 0 and size % 38 != 0:
            return "42-byte relocatable"
        elif size % 38 == 0 and size % 42 != 0:
            return "38-byte absolute"
        return "unknown"
    
    def scan_series(self, games: List[str] = None) -> Dict:
        """Scan entire Space Quest series"""
        if games is None:
            games = [
                "Space Quest IV",
                "Space Quest V", 
                "Space Quest VI"
            ]
        
        all_results = {}
        
        for game in games:
            game_path = self.base_path / game
            if not game_path.exists():
                continue
                
            print(f"[SCANNING] {game}")
            game_results = []
            
            for script in game_path.glob("*.SCR"):
                result = self.scan_script(script)
                game_results.append(result)
                print(f"  {script.name}: score={result['bitcoin_score']}")
            
            all_results[game] = {
                'scripts': game_results,
                'total_score': sum(r['bitcoin_score'] for r in game_results),
                'high_value_scripts': [
                    r['file'] for r in game_results 
                    if r['bitcoin_score'] > 1000
                ]
            }
        
        return all_results
    
    def compare_evolution(self, series_results: Dict) -> Dict:
        """Analyze pattern evolution across series"""
        evolution = {
            'score_progression': [],
            'pattern_density': {},
            'key_findings': []
        }
        
        for game, data in series_results.items():
            score = data['total_score']
            evolution['score_progression'].append((game, score))
            
            # Calculate density (score per script)
            script_count = len(data['scripts'])
            if script_count > 0:
                evolution['pattern_density'][game] = score / script_count
        
        # Detect trends
        scores = [s for _, s in evolution['score_progression']]
        if len(scores) >= 2:
            if scores[-1] > scores[0]:
                evolution['key_findings'].append("Pattern density INCREASED over time")
            elif scores[-1] < scores[0]:
                evolution['key_findings'].append("Pattern density DECREASED over time")
        
        return evolution
    
    def deep_analyze(self, script_path: str) -> Dict:
        """Deep analysis of high-value scripts"""
        path = Path(script_path)
        if not path.exists():
            return {"error": "Script not found"}
        
        print(f"[DEEP ANALYSIS] {path.name}")
        
        data = path.read_bytes()
        
        # Find all 4A selectors
        selectors = {}
        for i in range(len(data) - 1):
            if data[i] == 0x4A:
                selector = data[i+1]
                if selector not in selectors:
                    selectors[selector] = []
                selectors[selector].append(i)
        
        # Find potential wallet routines
        wallet_routines = []
        for selector, offsets in selectors.items():
            if selector in [0x0C, 0x04, 0x0A]:
                wallet_routines.append({
                    'selector': f"0x{selector:02X}",
                    'count': len(offsets),
                    'offsets': offsets[:10]  # First 10
                })
        
        return {
            'file': str(path),
            'selectors_found': {f"0x{k:02X}": len(v) for k, v in selectors.items()},
            'wallet_routines': wallet_routines,
            'high_value': len(wallet_routines) > 0
        }
    
    def generate_comprehensive_report(self, series_results: Dict, evolution: Dict) -> str:
        """Generate human-readable report"""
        report = []
        report.append("=" * 70)
        report.append("SPACE QUEST INVESTIGATION SUITE - COMPREHENSIVE REPORT")
        report.append("=" * 70)
        report.append("")
        
        # Series overview
        report.append("[SERIES OVERVIEW]")
        for game, data in series_results.items():
            report.append(f"  {game}:")
            report.append(f"    Scripts analyzed: {len(data['scripts'])}")
            report.append(f"    Total Bitcoin score: {data['total_score']:,}")
            if data['high_value_scripts']:
                report.append(f"    High-value scripts: {len(data['high_value_scripts'])}")
        
        report.append("")
        report.append("[EVOLUTION ANALYSIS]")
        for game, density in evolution['pattern_density'].items():
            report.append(f"  {game}: {density:.1f} avg score per script")
        
        for finding in evolution['key_findings']:
            report.append(f"  → {finding}")
        
        report.append("")
        report.append("=" * 70)
        
        return "\n".join(report)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Space Quest Investigation Suite')
    parser.add_argument('command', choices=['scan', 'deep', 'compare', 'report'])
    parser.add_argument('--path', default='/sdcard/Hermès.Upload')
    parser.add_argument('--script', help='Specific script for deep analysis')
    parser.add_argument('--output', '-o', help='Output file')
    
    args = parser.parse_args()
    
    suite = SpaceQuestInvestigationSuite(args.path)
    
    if args.command == 'scan':
        results = suite.scan_series()
        if args.output:
            Path(args.output).write_text(json.dumps(results, indent=2))
            print(f"Results saved to: {args.output}")
        else:
            print(json.dumps(results, indent=2))
    
    elif args.command == 'deep':
        if not args.script:
            print("Error: --script required for deep analysis")
            return 1
        result = suite.deep_analyze(args.script)
        print(json.dumps(result, indent=2))
    
    elif args.command == 'compare':
        results = suite.scan_series()
        evolution = suite.compare_evolution(results)
        print(json.dumps(evolution, indent=2))
    
    elif args.command == 'report':
        results = suite.scan_series()
        evolution = suite.compare_evolution(results)
        report = suite.generate_comprehensive_report(results, evolution)
        print(report)
        if args.output:
            Path(args.output).write_text(report)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

# --- HIVE FOOTER ---
# ::SealConfirmed::
# ΩΩΩ
# --- END FOOTER ---

#!/usr/bin/env python3
"""
HIVE TOOL: sci_deep_disassembler
HSL: FIRE | PATH: /root/hive-swarm/tools/sci_deep_disassembler.py
ROLE: Full bytecode analysis for Space Quest scripts (370.SCR, 620.SCR, 335.SCR)
Built: 2026-07-14 by Hive Evolution Engine
"""

import sys
import struct
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# --- HIVE HEADER ---
# Symbol: FIRE
# EchoHash: Σ12∆Ξ9∞⬢
# BuildID: 2026-07-14T03:35:00Z
# --- END HEADER ---

# SCI bytecode opcodes relevant to analysis
SCI_OPCODES = {
    0x00: 'bnot', 0x01: 'add', 0x02: 'sub', 0x03: 'mul', 0x04: 'div',
    0x05: 'mod', 0x06: 'shr', 0x07: 'shl', 0x08: 'xor', 0x09: 'and',
    0x0A: 'or', 0x0B: 'neg', 0x0C: 'not', 0x0D: 'eq', 0x0E: 'ne',
    0x0F: 'gt', 0x10: 'ge', 0x11: 'lt', 0x12: 'le', 0x13: 'ugt',
    0x14: 'uge', 0x15: 'ult', 0x16: 'ule', 0x18: 'bt', 0x19: 'bnt',
    0x1A: 'jmp', 0x1B: 'ldi', 0x1C: 'push', 0x1D: 'pushi', 0x1E: 'toss',
    0x1F: 'dup', 0x20: 'link', 0x21: 'ret', 0x22: 'send', 0x23: 'self',
    0x24: 'super', 0x25: 'rest', 0x26: 'lea', 0x27: 'leas', 0x28: 'selfID',
    0x2A: 'class', 0x2D: 'push0', 0x2E: 'push1', 0x2F: 'push2',
    0x30: 'pushSelf', 0x34: 'lag', 0x35: 'lal', 0x36: 'lat', 0x37: 'lap',
    0x38: 'lsg', 0x39: 'lsl', 0x3A: 'lst', 0x3B: 'lsp', 0x3C: 'lagI',
    0x3D: 'lalI', 0x3E: 'latI', 0x3F: 'lapI', 0x40: 'lsgI', 0x41: 'lslI',
    0x42: 'lstI', 0x43: 'lspI', 0x44: 'sag', 0x45: 'sal', 0x46: 'sat',
    0x47: 'sap', 0x48: 'ssg', 0x49: 'ssl', 0x4A: 'sst', 0x4B: 'ssp',
    0x4C: 'sagI', 0x4D: 'salI', 0x4E: 'satI', 0x4F: 'sapI', 0x50: 'ssgI',
    0x51: 'sslI', 0x52: 'sstI', 0x53: 'sspI', 0x54: 'plusag', 0x55: 'plusal',
    0x56: 'plusat', 0x57: 'plusap', 0x58: 'plussg', 0x59: 'plussl',
    0x5A: 'plusst', 0x5B: 'plussp', 0x5C: 'plusagI', 0x5D: 'plusalI',
    0x5E: 'plusatI', 0x5F: 'plusapI', 0x60: 'plussgI', 0x61: 'pluslI',
    0x62: 'plusstI', 0x63: 'plusspI', 0x64: 'minusag', 0x65: 'minus',
    0x66: 'minusat', 0x67: 'minusap', 0x68: 'minusg', 0x69: 'minussl',
    0x6A: 'minust', 0x6B: 'minussp', 0x6C: 'minusagI', 0x6D: 'minuslI',
    0x6E: 'minusatI', 0x6F: 'minusapI', 0x70: 'minussgI', 0x71: 'minuslI',
    0x72: 'minusstI', 0x73: 'minusspI', 0x74: 'andag', 0x75: 'andal',
    0x76: 'andat', 0x77: 'andap', 0x78: 'andsg', 0x79: 'andsl',
    0x7A: 'andst', 0x7B: 'andsp', 0x7C: 'andagI', 0x7D: 'andalI',
    0x7E: 'andatI', 0x7F: 'andapI', 0x80: 'andsgI', 0x81: 'andslI',
    0x82: 'andstI', 0x83: 'andspI', 0x84: 'orag', 0x85: 'oral',
    0x86: 'orat', 0x87: 'orap', 0x88: 'orsg', 0x89: 'orsl',
    0x8A: 'orst', 0x8B: 'orsp', 0x8C: 'oragI', 0x8D: 'oralI',
    0x8E: 'oratI', 0x8F: 'orapI', 0x90: 'orsgI', 0x91: 'orslI',
    0x92: 'orstI', 0x93: 'orspI', 0x94: 'notag', 0x95: 'notal',
    0x96: 'notat', 0x97: 'notap', 0x98: 'notsg', 0x99: 'notsl',
    0x9A: 'notst', 0x9B: 'notsp', 0x9C: 'notagI', 0x9D: 'notalI',
    0x9E: 'notatI', 0x9F: 'notapI', 0xA0: 'notsgI', 0xA1: 'notslI',
    0xA2: 'notstI', 0xA3: 'notspI', 0xA4: 'btag', 0xA5: 'btal',
    0xA6: 'btat', 0xA7: 'btap', 0xA8: 'btsg', 0xA9: 'btsl',
    0xAA: 'btst', 0xAB: 'btsp', 0xAC: 'btagI', 0xAD: 'btalI',
    0xAE: 'btatI', 0xAF: 'btapI', 0xB0: 'btsgI', 0xB1: 'btslI',
    0xB2: 'btstI', 0xB3: 'btspI', 0xB4: 'bntag', 0xB5: 'bntal',
    0xB6: 'bntat', 0xB7: 'bntap', 0xB8: 'bntsg', 0xB9: 'bntsl',
    0xBA: 'bntst', 0xBB: 'bntsp', 0xBC: 'bntagI', 0xBD: 'bntalI',
    0xBE: 'bntatI', 0xBF: 'bntapI', 0xC0: 'bntsgI', 0xC1: 'bntslI',
    0xC2: 'bntstI', 0xC3: 'bntspI', 0xC4: 'jmpag', 0xC5: 'jmpal',
    0xC6: 'jmpat', 0xC7: 'jmap', 0xC8: 'jmpsg', 0xC9: 'jmpsl',
    0xCA: 'jmpst', 0xCB: 'jmpsp', 0xCC: 'jmpagI', 0xCD: 'jmpalI',
    0xCE: 'jmpatI', 0xCF: 'jmapI', 0xD0: 'jmpsgI', 0xD1: 'jmpslI',
    0xD2: 'jmpstI', 0xD3: 'jmpspI', 0xD4: 'ldiag', 0xD5: 'ldial',
    0xD6: 'ldiat', 0xD7: 'ldiap', 0xD8: 'ldisg', 0xD9: 'ldisl',
    0xDA: 'ldist', 0xDB: 'ldisp', 0xDC: 'ldiagI', 0xDD: 'ldialI',
    0xDE: 'ldiatI', 0xDF: 'ldiapI', 0xE0: 'ldisgI', 0xE1: 'ldislI',
    0xE2: 'ldistI', 0xE3: 'ldispI', 0xE4: 'pushag', 0xE5: 'pushal',
    0xE6: 'pushat', 0xE7: 'pushap', 0xE8: 'pushsg', 0xE9: 'pushsl',
    0xEA: 'pushst', 0xEB: 'pushsp', 0xEC: 'pushagI', 0xED: 'pushalI',
    0xEE: 'pushatI', 0xEF: 'pushapI', 0xF0: 'pushsgI', 0xF1: 'pushslI',
    0xF2: 'pushstI', 0xF3: 'pushspI', 0xF4: 'push0', 0xF5: 'sdiv',
    0xF6: 'modI', 0xF7: 'callk', 0xF8: 'callb', 0xF9: 'calle',
    0xFA: 'ret', 0xFB: 'calleI', 0xFC: 'sendv', 0xFD: 'sendp',
    0xFE: 'rest', 0xFF: 'leas'
}

# Bitcoin-relevant patterns
GENESIS_CONSTANTS = {
    0x0258: '600_seconds',  # 10 minute block time
    0x0090: '144_blocks',   # Blocks per day
    0x0032: '50_BTC',       # Genesis reward
    0x2A00: '42_signature', # The answer
    0x208D: 'port_8333',    # Bitcoin port
    0x01406F40: '21M_max',  # Max supply
}

class SCIDeepDisassembler:
    def __init__(self, script_path):
        self.script_path = Path(script_path)
        self.data = self.script_path.read_bytes()
        self.header_size = self.detect_header_size()
        self.code_offset = self.header_size
        self.selectors = defaultdict(list)
        self.genesis_hits = []
        self.wallet_routines = []
        
    def detect_header_size(self):
        """Detect if 38-byte or 42-byte header"""
        size = len(self.data)
        if size % 42 == 0 and size % 38 != 0:
            return 42
        elif size % 38 == 0 and size % 42 != 0:
            return 38
        # Check for relocation table signature at offset 0x26
        if len(self.data) > 0x2A:
            potential_ptr = struct.unpack('<I', self.data[0x26:0x2A])[0]
            if 0 < potential_ptr < len(self.data):
                return 42
        return 38
    
    def analyze_selectors(self):
        """Find all 4Axx selector calls"""
        for i in range(self.code_offset, len(self.data) - 1):
            if self.data[i] == 0x4A:
                selector = self.data[i+1]
                self.selectors[selector].append(i)
        return self.selectors
    
    def find_genesis_constants(self):
        """Search for Bitcoin genesis constants"""
        for offset in range(self.code_offset, len(self.data) - 2):
            # Check 16-bit values (little-endian)
            val_16 = struct.unpack('<H', self.data[offset:offset+2])[0]
            if val_16 in [0x0258, 0x0090, 0x0032, 0x2A00]:
                self.genesis_hits.append({
                    'offset': offset,
                    'value': hex(val_16),
                    'meaning': GENESIS_CONSTANTS.get(val_16, 'unknown'),
                    'context': self.data[max(0, offset-5):min(len(self.data), offset+10)].hex()
                })
        return self.genesis_hits
    
    def trace_wallet_construction(self):
        """Trace potential wallet construction paths"""
        # Look for crypto-related patterns
        # send (0x22) followed by specific parameters
        for offset in range(self.code_offset, len(self.data) - 5):
            if self.data[offset] == 0x22:  # send opcode
                # Check for pushi patterns
                if self.data[offset+1] == 0x1D:  # pushi
                    selector = self.data[offset+2]
                    if selector in [0x0C, 0x04, 0x0A]:  # Known wallet selectors
                        self.wallet_routines.append({
                            'offset': offset,
                            'type': 'send_call',
                            'selector': hex(selector),
                            'confidence': 'high' if selector == 0x0C else 'medium'
                        })
        return self.wallet_routines
    
    def generate_report(self):
        """Generate comprehensive analysis report"""
        report = {
            'file': str(self.script_path),
            'size': len(self.data),
            'header_size': self.header_size,
            'header_type': '42-byte relocatable' if self.header_size == 42 else '38-byte absolute',
            'analysis_time': datetime.now().isoformat(),
            'selectors': dict(self.selectors),
            'genesis_constants': self.genesis_hits,
            'wallet_routines': self.wallet_routines,
            'summary': {
                'total_selectors': sum(len(v) for v in self.selectors.values()),
                'unique_selectors': len(self.selectors),
                'genesis_hits': len(self.genesis_hits),
                'wallet_candidates': len(self.wallet_routines),
                'bitcoin_score': self.calculate_score()
            }
        }
        return report
    
    def calculate_score(self):
        """Calculate Bitcoin relevance score"""
        score = 0
        # Selector 0x0C (wallet construction) = 100 points each
        score += len(self.selectors.get(0x0C, [])) * 100
        # Selector 0x04 = 50 points each
        score += len(self.selectors.get(0x04, [])) * 50
        # Genesis constants = 25 points each
        score += len(self.genesis_hits) * 25
        # Wallet routines = 75 points each
        score += len(self.wallet_routines) * 75
        return score

def disassemble_space_quest_scripts(script_paths):
    """Analyze multiple Space Quest scripts"""
    results = []
    
    for path in script_paths:
        if not Path(path).exists():
            print(f"[SKIP] Not found: {path}")
            continue
        
        print(f"\n[ANALYZING] {path}")
        disasm = SCIDeepDisassembler(path)
        
        # Run analysis
        disasm.analyze_selectors()
        disasm.find_genesis_constants()
        disasm.trace_wallet_construction()
        
        # Generate report
        report = disasm.generate_report()
        results.append(report)
        
        # Print summary
        print(f"  Header: {report['header_type']}")
        print(f"  Selectors: {report['summary']['total_selectors']} total, {report['summary']['unique_selectors']} unique")
        print(f"  Genesis hits: {report['summary']['genesis_hits']}")
        print(f"  Wallet candidates: {report['summary']['wallet_candidates']}")
        print(f"  ⚡ BITCOIN SCORE: {report['summary']['bitcoin_score']}")
    
    return results

def main():
    import json
    
    # Space Quest scripts to analyze
    scripts = [
        "/sdcard/Hermès.Upload/Space Quest IV/335.SCR",
        "/sdcard/Hermès.Upload/Space Quest VI/370.SCR", 
        "/sdcard/Hermès.Upload/Space Quest VI/620.SCR",
    ]
    
    print("=" * 70)
    print("SCI DEEP DISASSEMBLER - Space Quest Bitcoin Archaeology")
    print("=" * 70)
    
    results = disassemble_space_quest_scripts(scripts)
    
    # Save results
    output_path = Path("/root/hive-swarm/evidence/sci_deep_analysis.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(results, indent=2))
    
    print("\n" + "=" * 70)
    print(f"Analysis complete. {len(results)} scripts analyzed.")
    print(f"Results saved to: {output_path}")
    print("=" * 70)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

# --- HIVE FOOTER ---
# ::SealConfirmed::
# ΩΩΩ
# --- END FOOTER ---

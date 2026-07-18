#!/usr/bin/env python3
"""
HIVE TOOL: Deep Disassembler for SQ VI 370.SCR and 620.SCR
HSL: FIRE | PATH: /root/hive-swarm/tools/deep_disassembler_sqvi.py
TASK: Full instruction-level disassembly to reveal wallet construction algorithm
"""

import sys
import struct
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# Extended SCI bytecode opcodes with operand info
SCI_OPCODES = {
    0x00: ('bnot', 0), 0x01: ('add', 0), 0x02: ('sub', 0), 0x03: ('mul', 0),
    0x04: ('div', 0), 0x05: ('mod', 0), 0x06: ('shr', 0), 0x07: ('shl', 0),
    0x08: ('xor', 0), 0x09: ('and', 0), 0x0A: ('or', 0), 0x0B: ('neg', 0),
    0x0C: ('not', 0), 0x0D: ('eq', 0), 0x0E: ('ne', 0), 0x0F: ('gt', 0),
    0x10: ('ge', 0), 0x11: ('lt', 0), 0x12: ('le', 0), 0x13: ('ugt', 0),
    0x14: ('uge', 0), 0x15: ('ult', 0), 0x16: ('ule', 0), 0x18: ('bt', 1),
    0x19: ('bnt', 1), 0x1A: ('jmp', 1), 0x1B: ('ldi', 2), 0x1C: ('push', 0),
    0x1D: ('pushi', 1), 0x1E: ('toss', 0), 0x1F: ('dup', 0), 0x20: ('link', 1),
    0x21: ('ret', 0), 0x22: ('send', 1), 0x23: ('self', 1), 0x24: ('super', 2),
    0x25: ('rest', 1), 0x26: ('lea', 2), 0x27: ('leas', 0), 0x28: ('selfID', 0),
    0x2A: ('class', 1), 0x2D: ('push0', 0), 0x2E: ('push1', 0), 0x2F: ('push2', 0),
    0x30: ('pushSelf', 0), 0x34: ('lag', 1), 0x35: ('lal', 1), 0x36: ('lat', 1),
    0x37: ('lap', 1), 0x38: ('lsg', 1), 0x39: ('lsl', 1), 0x3A: ('lst', 1),
    0x3B: ('lsp', 1), 0x44: ('sag', 1), 0x45: ('sal', 1), 0x46: ('sat', 1),
    0x47: ('sap', 1), 0x48: ('ssg', 1), 0x49: ('ssl', 1), 0x4A: ('sst', 1),
    0x4B: ('ssp', 1), 0xF7: ('callk', 2), 0xF8: ('callb', 2), 0xF9: ('calle', 2),
    0xFA: ('ret', 0),
}

# Critical selectors for wallet analysis
WALLET_SELECTORS = {
    0x0C: 'WALLET_CONSTRUCT',
    0x04: 'CRYPTO_OP',
    0x0A: 'KEY_DERIVE',
    0x9E: 'RECEIVER_VAR',
    0x50: 'GENESIS_REF',
}

class DeepDisassembler:
    def __init__(self, script_path):
        self.script_path = Path(script_path)
        self.data = self.script_path.read_bytes()
        self.disassembly = []
        self.selectors = defaultdict(list)
        self.wallet_chains = []
        self.crypto_patterns = []
        
    def get_operand(self, offset, size):
        """Extract operand at given offset"""
        if offset + size > len(self.data):
            return 0, size
        if size == 1:
            return self.data[offset], size
        elif size == 2:
            return struct.unpack('<H', self.data[offset:offset+2])[0], size
        return 0, size
    
    def disassemble(self):
        """Full instruction-level disassembly"""
        offset = 0
        
        while offset < len(self.data):
            opcode = self.data[offset]
            
            if opcode in SCI_OPCODES:
                mnemonic, operand_size = SCI_OPCODES[opcode]
                operand = 0
                
                if operand_size > 0 and offset + operand_size < len(self.data):
                    operand, _ = self.get_operand(offset + 1, operand_size)
                
                # Build instruction record
                instr = {
                    'offset': offset,
                    'raw': self.data[offset:offset+1+operand_size].hex(),
                    'opcode': opcode,
                    'mnemonic': mnemonic,
                    'operand': operand if operand_size > 0 else None,
                    'operand_size': operand_size,
                }
                
                # Add annotation for special opcodes
                instr['annotation'] = self.annotate_instruction(instr)
                
                self.disassembly.append(instr)
                offset += 1 + operand_size
            else:
                # Unknown opcode - treat as data
                self.disassembly.append({
                    'offset': offset,
                    'raw': f'{opcode:02x}',
                    'opcode': opcode,
                    'mnemonic': 'db',
                    'operand': opcode,
                    'operand_size': 0,
                    'annotation': f'; byte 0x{opcode:02x}'
                })
                offset += 1
        
        return self.disassembly
    
    def annotate_instruction(self, instr):
        """Add semantic annotations to instructions"""
        mnemonic = instr['mnemonic']
        operand = instr['operand']
        offset = instr['offset']
        
        annotations = []
        
        # Track 4Axx selector stores
        if instr['opcode'] == 0x4A and operand is not None:
            self.selectors[operand].append(offset)
            sel_name = WALLET_SELECTORS.get(operand, f'sel_{operand:02x}')
            annotations.append(f'STORE_SELECTOR [{sel_name}]')
            
            # Track wallet construction chains
            if operand == 0x0C:
                self.wallet_chains.append({
                    'offset': offset,
                    'context': self.get_context(offset, 20)
                })
        
        # Track send operations (0x22)
        if instr['opcode'] == 0x22:
            annotations.append('METHOD_SEND')
        
        # Track pushi patterns for crypto constants
        if instr['opcode'] == 0x1D and operand is not None:
            if operand in [0x50, 0x0258, 0x0090, 0x0032]:
                annotations.append(f'GENESIS_CONST [{operand}]')
            elif operand == 0x9E:
                annotations.append('RECEIVER_VAR_0x9E')
        
        # Track crypto operations
        if mnemonic in ['xor', 'and', 'or', 'shr', 'shl']:
            annotations.append('CRYPTO_OP')
            self.crypto_patterns.append({
                'offset': offset,
                'op': mnemonic,
                'context': self.get_context(offset, 10)
            })
        
        return ' | '.join(annotations) if annotations else ''
    
    def get_context(self, offset, window):
        """Get context bytes around an offset"""
        start = max(0, offset - window)
        end = min(len(self.data), offset + window)
        return self.data[start:end].hex()
    
    def find_entry_points(self):
        """Identify potential wallet construction entry points"""
        entries = []
        
        # Look for method prologues (link instruction)
        for i, instr in enumerate(self.disassembly):
            if instr['mnemonic'] == 'link':
                # Check if followed by crypto-related ops
                next_instrs = self.disassembly[i+1:i+10]
                crypto_count = sum(1 for x in next_instrs if 'CRYPTO_OP' in x.get('annotation', ''))
                
                if crypto_count > 0 or any('WALLET_CONSTRUCT' in x.get('annotation', '') for x in next_instrs):
                    entries.append({
                        'offset': instr['offset'],
                        'type': 'method_prologue',
                        'crypto_ops': crypto_count,
                        'confidence': 'high' if crypto_count >= 2 else 'medium'
                    })
        
        return entries
    
    def trace_4a0c_chains(self):
        """Trace 0x4A0C selector chains specifically"""
        chains = []
        
        for sel_offset in self.selectors.get(0x0C, []):
            # Look backward for parameter setup
            chain_start = max(0, sel_offset - 50)
            
            # Find the start of this instruction sequence
            for instr in self.disassembly:
                if chain_start <= instr['offset'] < sel_offset:
                    if instr['mnemonic'] in ['pushi', 'push', 'push0', 'push1', 'push2']:
                        chain_start = instr['offset']
            
            chain_bytes = self.data[chain_start:sel_offset+2]
            
            chains.append({
                'selector_offset': sel_offset,
                'chain_start': chain_start,
                'chain_bytes': chain_bytes.hex(),
                'chain_length': len(chain_bytes),
                'decrypted': self.attempt_decrypt(chain_bytes)
            })
        
        return chains
    
    def attempt_decrypt(self, data):
        """Attempt simple XOR decryption patterns"""
        results = []
        
        # Try common XOR keys
        for key in [0x42, 0x21, 0x50, 0x00, 0xFF]:
            decrypted = bytes([b ^ key for b in data])
            # Check for printable ASCII
            printable = ''.join(chr(b) if 32 <= b < 127 else '.' for b in decrypted)
            if any(c.isalnum() for c in printable):
                results.append(f'XOR 0x{key:02x}: {printable[:50]}')
        
        return results
    
    def generate_markdown_report(self):
        """Generate comprehensive markdown report"""
        lines = []
        
        lines.append('# Deep Disassembly Report: SQ VI Wallet Construction Algorithm')
        lines.append(f'\n**File:** {self.script_path}')
        lines.append(f'**Size:** {len(self.data)} bytes')
        lines.append(f'**Analysis Time:** {datetime.now().isoformat()}')
        lines.append(f'**Analyst:** Hive Deep Disassembler (HSL: FIRE)')
        lines.append('\n---\n')
        
        # Summary
        lines.append('## Executive Summary\n')
        lines.append(f'- **Total Instructions:** {len(self.disassembly)}')
        lines.append(f'- **Unique Selectors:** {len(self.selectors)}')
        lines.append(f'- **Wallet Construction Chains:** {len(self.wallet_chains)}')
        lines.append(f'- **Crypto Operations:** {len(self.crypto_patterns)}')
        lines.append('\n---\n')
        
        # Selector Analysis
        lines.append('## Selector Analysis\n')
        lines.append('| Selector | Count | Symbolic Name | Offsets |')
        lines.append('|----------|-------|---------------|---------|')
        
        for sel in sorted(self.selectors.keys()):
            count = len(self.selectors[sel])
            name = WALLET_SELECTORS.get(sel, f'sel_{sel:02x}')
            offsets = ', '.join([f'0x{o:04x}' for o in self.selectors[sel][:5]])
            if len(self.selectors[sel]) > 5:
                offsets += f' (+{len(self.selectors[sel]) - 5} more)'
            lines.append(f'| 0x{sel:02X} | {count} | {name} | {offsets} |')
        
        lines.append('\n---\n')
        
        # Full Disassembly
        lines.append('## Full Instruction Disassembly\n')
        lines.append('```')
        lines.append(f'{"Offset":<8} {"Raw":<12} {"Mnemonic":<12} {"Operand":<12} {"Annotation"}')
        lines.append('-' * 80)
        
        for instr in self.disassembly:
            operand_str = f'0x{instr["operand"]:04x}' if instr['operand'] is not None else ''
            lines.append(f'{instr["offset"]:08x} {instr["raw"]:<12} {instr["mnemonic"]:<12} '
                        f'{operand_str:<12} {instr.get("annotation", "")}')
        
        lines.append('```\n')
        lines.append('\n---\n')
        
        # Entry Points
        entries = self.find_entry_points()
        lines.append(f'## Wallet Construction Entry Points ({len(entries)} found)\n')
        for entry in entries:
            lines.append(f'- **0x{entry["offset"]:04x}** - {entry["type"]} '
                        f'(crypto_ops: {entry["crypto_ops"]}, confidence: {entry["confidence"]})')
        lines.append('\n---\n')
        
        # 0x4A0C Chain Analysis
        chains = self.trace_4a0c_chains()
        lines.append(f'## 0x4A0C Selector Chain Analysis ({len(chains)} chains)\n')
        
        for i, chain in enumerate(chains[:20], 1):  # Limit to first 20
            lines.append(f'### Chain {i}: Offset 0x{chain["selector_offset"]:04x}\n')
            lines.append(f'- **Start:** 0x{chain["chain_start"]:04x}')
            lines.append(f'- **Length:** {chain["chain_length"]} bytes')
            lines.append(f'- **Bytes:** `{chain["chain_bytes"]}`')
            lines.append('- **Decryption attempts:**')
            for decrypt in chain['decrypted'][:3]:
                lines.append(f'  - {decrypt}')
            lines.append('')
        
        lines.append('\n---\n')
        
        # Crypto Pattern Analysis
        lines.append(f'## Cryptographic Operation Patterns ({len(self.crypto_patterns)} ops)\n')
        for i, pattern in enumerate(self.crypto_patterns[:30], 1):
            lines.append(f'{i}. **0x{pattern["offset"]:04x}** - `{pattern["op"]}` - '
                        f'`{pattern["context"][:40]}`...')
        
        lines.append('\n---\n')
        
        # Developer Signatures
        lines.append('## Developer Signatures/Markers\n')
        signatures = self.find_signatures()
        if signatures:
            for sig in signatures:
                lines.append(f'- **0x{sig["offset"]:04x}:** {sig["type"]} - `{sig["data"]}`')
        else:
            lines.append('*No explicit developer signatures found*')
        
        lines.append('\n---\n')
        lines.append('## Analysis Complete\n')
        lines.append('*Generated by Hive Deep Disassembler*')
        
        return '\n'.join(lines)
    
    def find_signatures(self):
        """Look for developer signatures or markers"""
        signatures = []
        
        # Look for "SQ" or "Sierra" strings
        for i in range(len(self.data) - 10):
            chunk = self.data[i:i+10]
            try:
                text = chunk.decode('ascii', errors='ignore')
                if any(marker in text for marker in ['SQ', 'Sierra', 'SCI', 'WALLET', 'CRYPTO']):
                    signatures.append({
                        'offset': i,
                        'type': 'ascii_marker',
                        'data': text.strip()
                    })
            except:
                pass
        
        return signatures

def main():
    scripts = [
        "/root/hive-swarm/space-quest-series/SQVI/SQ6/370.SCR",
        "/root/hive-swarm/space-quest-series/SQVI/SQ6/620.SCR",
    ]
    
    output_path = Path("/root/hive-swarm/evidence/sqvi_deep_disassembly.md")
    
    with open(output_path, 'w') as f:
        f.write('# SQ VI Deep Disassembly Analysis\n')
        f.write(f'## Generated: {datetime.now().isoformat()}\n\n')
        f.write('---\n\n')
        
        for script_path in scripts:
            print(f"[DISASSEMBLING] {script_path}...")
            
            if not Path(script_path).exists():
                f.write(f'## ERROR: File not found: {script_path}\n\n')
                continue
            
            disasm = DeepDisassembler(script_path)
            disasm.disassemble()
            
            report = disasm.generate_markdown_report()
            f.write(report)
            f.write('\n\n---\n\n')
            
            print(f"  ✓ Analyzed: {len(disasm.disassembly)} instructions")
            print(f"  ✓ Selectors found: {len(disasm.selectors)}")
            print(f"  ✓ Wallet chains: {len(disasm.wallet_chains)}")
    
    print(f"\n[COMPLETE] Report saved to: {output_path}")
    return 0

if __name__ == "__main__":
    sys.exit(main())

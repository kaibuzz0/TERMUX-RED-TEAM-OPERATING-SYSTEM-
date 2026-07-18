#!/usr/bin/env python3
"""Hive Ops DevAI - Whitespace Stealth Module
Encode/decode secrets in spaces/tabs at end of lines.
Zero dependencies. Minimal footprint."""

import os
from pathlib import Path

class WhitespaceSteg:
    """Hide data in trailing whitespace."""
    
    # Encoding: space=0, tab=1
    SPACE = ' '
    TAB = '\t'
    
    @staticmethod
    def encode(data: str, cover_text: str) -> str:
        """Encode data into cover text whitespace.
        
        Args:
            data: Secret string to hide
            cover_text: Visible text to camouflage
        
        Returns:
            Text with encoded whitespace
        """
        # Convert data to binary
        binary = ''.join(format(ord(c), '08b') for c in data)
        
        lines = cover_text.split('\n')
        result = []
        bit_idx = 0
        
        for line in lines:
            # Strip existing trailing whitespace
            line = line.rstrip()
            
            # Add encoded whitespace (up to 8 bits per line)
            whitespace = ''
            for _ in range(8):
                if bit_idx < len(binary):
                    bit = binary[bit_idx]
                    whitespace += WhitespaceSteg.SPACE if bit == '0' else WhitespaceSteg.TAB
                    bit_idx += 1
            
            result.append(line + whitespace)
        
        # Add remaining bits if any
        while bit_idx < len(binary):
            whitespace = ''
            for _ in range(8):
                if bit_idx < len(binary):
                    bit = binary[bit_idx]
                    whitespace += WhitespaceSteg.SPACE if bit == '0' else WhitespaceSteg.TAB
                    bit_idx += 1
            result.append('#' + whitespace)
        
        return '\n'.join(result)
    
    @staticmethod
    def decode(stego_text: str) -> str:
        """Decode data from trailing whitespace.
        
        Args:
            stego_text: Text with hidden whitespace
        
        Returns:
            Decoded secret string
        """
        binary = ''
        
        for line in stego_text.split('\n'):
            # Get trailing whitespace
            stripped = line.rstrip()
            trailing = line[len(stripped):] if len(line) > len(stripped) else ''
            
            for char in trailing:
                if char == WhitespaceSteg.SPACE:
                    binary += '0'
                elif char == WhitespaceSteg.TAB:
                    binary += '1'
        
        # Convert binary to string
        chars = []
        for i in range(0, len(binary), 8):
            byte = binary[i:i+8]
            if len(byte) == 8:
                chars.append(chr(int(byte, 2)))
        
        return ''.join(chars)
    
    @staticmethod
    def load_config(config_path: Path) -> dict:
        """Load config with embedded secrets.
        
        Returns dict with visible config + decoded secrets.
        """
        if not config_path.exists():
            return {}
        
        text = config_path.read_text()
        
        # Parse visible lines (comments = hidden data)
        config = {}
        secrets = []
        
        for line in text.split('\n'):
            stripped = line.strip()
            
            # Regular config line
            if '=' in stripped and not stripped.startswith('#'):
                key, val = stripped.split('=', 1)
                config[key.strip()] = val.strip().strip('"\'')
            
            # Extract secrets from trailing whitespace
            trailing = line[len(line.rstrip()):] if len(line) > len(line.rstrip()) else ''
            if trailing:
                for char in trailing:
                    secrets.append('0' if char == ' ' else '1')
        
        # Decode secrets
        if secrets:
            binary = ''.join(secrets)
            decoded = ''
            for i in range(0, len(binary), 8):
                byte = binary[i:i+8]
                if len(byte) == 8:
                    decoded += chr(int(byte, 2))
            
            # Parse decoded secrets (format: KEY=VALUE;)
            for pair in decoded.split(';'):
                if '=' in pair:
                    k, v = pair.split('=', 1)
                    config[f'_{k}'] = v  # Secrets prefixed with _
        
        return config


def test():
    """Test encoding/decoding."""
    cover = """# This is a normal Python config file
API_ENDPOINT = "https://api.example.com"
DEBUG = False
TIMEOUT = 30
# End of config"""
    
    secret = "API_KEY=sk-abc123;SECRET_TOKEN=xyz789"
    
    # Encode
    encoded = WhitespaceSteg.encode(secret, cover)
    print("=== ENCODED (showing whitespace as [S] and [T]) ===")
    for line in encoded.split('\n'):
        vis = line.replace(' ', '[S]').replace('\t', '[T]')
        print(vis)
    
    # Decode
    decoded = WhitespaceSteg.decode(encoded)
    print("\n=== DECODED ===")
    print(decoded)
    
    # Verify
    assert decoded == secret, "Decode failed!"
    print("\n✓ Test passed")


if __name__ == '__main__':
    test()

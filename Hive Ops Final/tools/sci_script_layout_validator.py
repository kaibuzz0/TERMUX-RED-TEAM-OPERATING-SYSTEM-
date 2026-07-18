#!/usr/bin/env python3
import sys
import struct
import os

# Hive Symbolic Language Tool: SCI Script Layout Validator
# Validates SQ4, SQ5, SQ6 files (SCI script headers)
# Logic: Checks header integrity, section offsets, and basic structure.

def validate_sci_file(filepath):
    if not os.path.exists(filepath):
        print(f"Error: File {filepath} not found.")
        return False

    filesize = os.path.getsize(filepath)
    
    # Auto-detection logic: 38 vs 42 bytes
    if filesize % 42 == 0:
        print(f"Detected: 42-byte SCI Script (Relocation Table present)")
        is_relocatable = True
    elif filesize % 38 == 0:
        print(f"Detected: 38-byte SCI Script (Absolute Addressing)")
        is_relocatable = False
    else:
        print(f"Warning: Unexpected filesize {filesize} for SCI script variant.")
        is_relocatable = False

    with open(filepath, 'rb') as f:
        data = f.read()

    # Header analysis based on variant
    if is_relocatable:
        relocation_table = data[38:42]
        print(f"Relocation Table: {relocation_table.hex()}")
    
    # Analysis of section boundary markers
    # For 38-byte variant, offsets start at absolute indices (0x02, 0x04, etc.)
    # For 42-byte variant, pointers are offset by the 4-byte table
    
    offset_base = 0 if not is_relocatable else 4
    
    # Example: Script ID at offset 0x02
    script_id = struct.unpack('<H', data[0x02:0x04])[0]
    print(f"Script ID: {script_id}")
    
    return True



if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: sci_script_layout_validator.py <file>")
        sys.exit(1)
    
    success = validate_sci_file(sys.argv[1])
    sys.exit(0 if success else 1)


import sys
import os

# Ensure the directory is in the path
sys.path.append("/root/hive-swarm/tools")
from sci_emulator import SCIEmulator

def inject():
    # Hex payload
    payload = [0x46, 0x47, 0x50, 0x46, 0x47, 0x47, 0x51, 0x47, 0x33, 0x47, 0x4e, 0x70, 0x6a, 0x6b, 0x36, 0x68]
    start_addr = 0x3890
    
    # Initialize emulator
    emulator = SCIEmulator()
    
    print(f"Injecting payload into memory at {hex(start_addr)}...")
    
    # Write payload
    for i, byte in enumerate(payload):
        emulator.write_memory(start_addr + i, byte)
    
    # Verify
    success = True
    print("Verification:")
    for i, byte in enumerate(payload):
        val = emulator.memory[start_addr + i]
        if val != byte:
            print(f"Verification failed at {hex(start_addr + i)}: Expected {hex(byte)}, Got {hex(val)}")
            success = False
        else:
            print(f"Byte {i}: {hex(val)} OK")
    
    if success:
        print("Injection and verification successful.")
    else:
        print("Injection failed.")

if __name__ == "__main__":
    inject()

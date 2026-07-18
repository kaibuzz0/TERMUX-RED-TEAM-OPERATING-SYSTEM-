import os
import sys
import math
import base64
import binascii

def calculate_entropy(data):
    if not data:
        return 0
    entropy = 0
    for x in range(256):
        p_x = float(data.count(bytes([x]))) / len(data)
        if p_x > 0:
            entropy += - p_x * math.log(p_x, 2)
    return entropy

def analyze_file(filepath):
    try:
        with open(filepath, 'rb') as f:
            data = f.read()
    except Exception as e:
        return f"Error reading file: {e}"

    results = {
        "file": filepath,
        "size": len(data),
        "entropy": calculate_entropy(data),
        "detections": []
    }

    # Basic heuristic detections
    if results["entropy"] > 7.5:
        results["detections"].append("High entropy (potential encrypted or compressed)")
    
    # Base64 check
    try:
        if len(data) > 4:
            base64.b64decode(data[:100])
            results["detections"].append("Potential Base64 encoding detected")
    except:
        pass

    # Simple XOR check (common 0x55, 0xAA)
    if any(b ^ 0x55 == 0 for b in data[:100]) or any(b ^ 0xAA == 0 for b in data[:100]):
        results["detections"].append("Potential XOR pattern detected")

    return results

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 recon_node.py <file_path>")
        sys.exit(1)
    
    print(analyze_file(sys.argv[1]))

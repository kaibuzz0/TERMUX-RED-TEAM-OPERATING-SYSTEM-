#!/usr/bin/env python3
"""
HIVE TOOL: blockchain_monitor
HSL: FIRE | PATH: /root/hive-swarm/tools/blockchain_monitor.py
ROLE: Continuous monitoring of 53 Space Quest addresses for balance/activity
Built: 2026-07-14 by Hive Autonomous Tool Builder
"""

import sys
import json
import time
import urllib.request
from pathlib import Path
from datetime import datetime

# --- HIVE HEADER ---
# Symbol: FIRE
# EchoHash: Σ12∆Ξ9∞⬢
# BuildID: 2026-07-14T00:00:00Z
# --- END HEADER ---

ADDRESSES_FILE = Path("/root/hive-swarm/space-quest-series/unique_addresses.txt")
LOG_FILE = Path("/root/hive-swarm/evidence/blockchain_monitor.log")
STATE_FILE = Path("/root/hive-swarm/evidence/monitor_state.json")

API_ENDPOINTS = [
    "https://blockchain.info/rawaddr/{}",
    "https://api.blockcypher.com/v1/btc/main/addrs/{}?txlimit=0",
]

def log_event(message):
    timestamp = datetime.now().isoformat()
    entry = f"[{timestamp}] {message}\n"
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(entry)
    print(entry.strip())

def check_address(address, api_idx=0):
    try:
        url = API_ENDPOINTS[api_idx].format(address)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            balance = data.get("final_balance", data.get("balance", 0))
            return {
                "address": address,
                "balance_satoshis": balance,
                "balance_btc": balance / 1e8,
                "n_tx": data.get("n_tx", 0),
                "checked_at": datetime.now().isoformat(),
                "status": "active" if balance > 0 or data.get("n_tx", 0) > 0 else "empty",
            }
    except Exception as e:
        return {"address": address, "error": str(e), "status": "error"}

def load_addresses():
    if not ADDRESSES_FILE.exists():
        return []
    return [line.strip() for line in ADDRESSES_FILE.read_text().split("\n") if line.strip()]

def save_state(results):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(results, indent=2))

def main():
    log_event("=" * 60)
    log_event("BLOCKCHAIN MONITOR - Space Quest Address Surveillance")
    log_event("=" * 60)
    
    addresses = load_addresses()
    if not addresses:
        log_event("[ERROR] No addresses found. Run blockchain_batch_checker first.")
        return 1
    
    log_event(f"Monitoring {len(addresses)} addresses...")
    
    results = {"checked_at": datetime.now().isoformat(), "addresses": []}
    funded = 0
    
    for addr in addresses:
        result = check_address(addr)
        results["addresses"].append(result)
        
        if result.get("status") == "active":
            funded += 1
            log_event(f"[ALERT] ACTIVE ADDRESS: {addr}")
            log_event(f"  Balance: {result['balance_btc']:.8f} BTC")
            log_event(f"  Transactions: {result['n_tx']}")
    
    results["summary"] = {
        "total": len(addresses),
        "funded": funded,
        "empty": len(addresses) - funded,
    }
    
    save_state(results)
    
    log_event("-" * 60)
    log_event(f"SUMMARY: {funded} funded, {len(addresses)-funded} empty")
    log_event(f"State saved to: {STATE_FILE}")
    log_event("=" * 60)
    
    return 0 if funded == 0 else 100  # 100 = activity detected

if __name__ == "__main__":
    sys.exit(main())

# --- HIVE FOOTER ---
# ::SealConfirmed::
# ΩΩΩ
# --- END FOOTER ---

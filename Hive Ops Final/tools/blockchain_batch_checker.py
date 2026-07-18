#!/usr/bin/env python3
"""
HIVE TOOL: blockchain_batch_checker
HSL: FIRE | PATH: /root/hive-swarm/tools/blockchain_batch_checker.py
ROLE: Checks multiple Bitcoin addresses for balance/transactions in parallel - maximizes API throughput
Built: 2026-07-14 by Hive Autonomous Toolsmith

Usage:
  python3 blockchain_batch_checker.py --input /root/hive-swarm/space-quest-series/unique_addresses.txt
"""

import sys
import json
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# API endpoints (free, no auth required)
API_ENDPOINTS = [
    "https://blockchain.info/rawaddr/{address}",
    "https://api.blockcypher.com/v1/btc/main/addrs/{address}?txlimit=0",
]

def check_address_blockchain_info(address):
    """Check address using blockchain.info API"""
    try:
        url = f"https://blockchain.info/rawaddr/{address}?limit=0"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            return {
                'address': address,
                'final_balance': data.get('final_balance', 0),
                'total_received': data.get('total_received', 0),
                'total_sent': data.get('total_sent', 0),
                'n_tx': data.get('n_tx', 0),
                'source': 'blockchain.info'
            }
    except Exception as e:
        return {'address': address, 'error': str(e), 'source': 'blockchain.info'}

def check_address_blockcypher(address):
    """Check address using BlockCypher API"""
    try:
        url = f"https://api.blockcypher.com/v1/btc/main/addrs/{address}?txlimit=0"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            return {
                'address': address,
                'final_balance': data.get('balance', 0),
                'total_received': data.get('total_received', 0),
                'total_sent': data.get('total_sent', 0),
                'n_tx': data.get('n_tx', 0),
                'source': 'blockcypher'
            }
    except Exception as e:
        return {'address': address, 'error': str(e), 'source': 'blockcypher'}

def check_address(address, retry=True):
    """Check a single address with fallback APIs"""
    print(f"  Checking: {address[:20]}...{address[-10:]}")
    
    # Try blockchain.info first
    result = check_address_blockchain_info(address)
    
    # If error and retry enabled, try BlockCypher
    if 'error' in result and retry:
        print(f"    Fallback to BlockCypher...")
        result = check_address_blockcypher(address)
    
    # Convert satoshis to BTC
    if 'final_balance' in result:
        result['balance_btc'] = result['final_balance'] / 1e8
        result['received_btc'] = result.get('total_received', 0) / 1e8
        result['sent_btc'] = result.get('total_sent', 0) / 1e8
    
    return result

def check_batch(addresses, max_workers=10):
    """Check multiple addresses in parallel"""
    results = []
    
    print(f"\n{'='*80}")
    print(f"BLOCKCHAIN BATCH CHECK - {len(addresses)} addresses, {max_workers} workers")
    print(f"{'='*80}\n")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_address = {
            executor.submit(check_address, addr): addr 
            for addr in addresses
        }
        
        completed = 0
        for future in as_completed(future_to_address):
            result = future.result()
            results.append(result)
            completed += 1
            
            # Progress indicator
            if completed % 10 == 0 or completed == len(addresses):
                print(f"  Progress: {completed}/{len(addresses)}")
    
    return results

def generate_report(results, output_path):
    """Generate comprehensive report"""
    # Separate funded vs empty
    funded = [r for r in results if r.get('final_balance', 0) > 0 or r.get('n_tx', 0) > 0]
    empty = [r for r in results if r.get('final_balance', 0) == 0 and r.get('n_tx', 0) == 0 and 'error' not in r]
    errors = [r for r in results if 'error' in r]
    
    report = {
        'checked_at': datetime.now().isoformat(),
        'summary': {
            'total_checked': len(results),
            'funded_addresses': len(funded),
            'empty_addresses': len(empty),
            'errors': len(errors),
            'total_balance_btc': sum(r.get('balance_btc', 0) for r in funded)
        },
        'funded_addresses': funded,
        'empty_addresses': empty,
        'errors': errors
    }
    
    output_path.write_text(json.dumps(report, indent=2))
    return report

def main():
    print("="*80)
    print("BLOCKCHAIN BATCH CHECKER - Space Quest Address Verification")
    print("="*80)
    
    # Load addresses
    input_path = Path("/root/hive-swarm/space-quest-series/unique_addresses.txt")
    if not input_path.exists():
        print(f"[ERROR] Address file not found: {input_path}")
        return 1
    
    addresses = [line.strip() for line in input_path.read_text().split('\n') if line.strip()]
    print(f"\nLoaded {len(addresses)} addresses")
    
    # Check all addresses
    results = check_batch(addresses, max_workers=10)
    
    # Generate report
    output_path = Path("/root/hive-swarm/space-quest-series/blockchain_check_results.json")
    report = generate_report(results, output_path)
    
    # Print summary
    print(f"\n{'='*80}")
    print("RESULTS SUMMARY")
    print(f"{'='*80}")
    print(f"Total checked: {report['summary']['total_checked']}")
    print(f"Funded (balance > 0): {report['summary']['funded_addresses']}")
    print(f"Empty (never used): {report['summary']['empty_addresses']}")
    print(f"Errors: {report['summary']['errors']}")
    print(f"Total balance: {report['summary']['total_balance_btc']:.8f} BTC")
    
    if report['summary']['funded_addresses'] > 0:
        print(f"\n*** FUNDED ADDRESSES FOUND ***")
        for addr in report['funded_addresses']:
            print(f"\n  Address: {addr['address']}")
            print(f"  Balance: {addr.get('balance_btc', 0):.8f} BTC")
            print(f"  Received: {addr.get('received_btc', 0):.8f} BTC")
            print(f"  Transactions: {addr.get('n_tx', 0)}")
    else:
        print(f"\n✓ No funded addresses found")
        print(f"  All {len(addresses)} addresses are fresh/unused")
    
    print(f"\n{'='*80}")
    print(f"Full report saved to: {output_path}")
    print(f"{'='*80}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python3
"""
Hermes-Hive Memory Sync
Synchronizes Hermes persistent memory to Hive Ledger
"""
import json
import time
import hashlib
from pathlib import Path
from datetime import datetime
import subprocess
import sys

# Paths
HERMES_HOME = Path('/root/.hermes')
HIVE_SWARM = Path('/root/hive-swarm')
LEDGER_SCRIPT = HIVE_SWARM / 'services' / 'resonance_ledger.py'

MEMORY_FILES = {
    'user': 'memory/user.json',
    'memory': 'memory.json',
    'skills_index': 'skills/.index.json',
}

class HermesMemorySync:
    """Sync Hermes memory to Hive Resonance Ledger."""
    
    def __init__(self):
        self.sync_log = []
        
    def _hash_content(self, content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _emit_to_ledger(self, event_type: str, payload: dict):
        """Emit event to ledger."""
        if not LEDGER_SCRIPT.exists():
            return False
        
        try:
            result = subprocess.run([
                sys.executable, str(LEDGER_SCRIPT),
                'emit', '--type', event_type,
                '--payload', json.dumps(payload)
            ], capture_output=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    def sync_user_preferences(self):
        """Sync user preferences from Hermes memory."""
        user_file = HERMES_HOME / 'memory' / 'user.json'
        if not user_file.exists():
            return
        
        try:
            with open(user_file) as f:
                data = json.load(f)
            
            # Emit each preference as event
            for key, value in data.items():
                if isinstance(value, (str, int, float, bool)):
                    self._emit_to_ledger('HERMES_PREF', {
                        'key': key,
                        'value_hash': self._hash_content(str(value)),
                        'timestamp': time.time()
                    })
            
            print(f"✓ Synced {len(data)} user preferences")
            
        except Exception as e:
            print(f"✗ Error syncing user prefs: {e}")
    
    def sync_skills(self):
        """Sync skills index."""
        skills_index = HERMES_HOME / 'skills' / '.index.json'
        if not skills_index.exists():
            return
        
        try:
            with open(skills_index) as f:
                data = json.load(f)
            
            skills = data.get('skills', [])
            self._emit_to_ledger('HERMES_SKILLS', {
                'count': len(skills),
                'names': [s.get('name', '?') for s in skills[:10]],
                'timestamp': time.time()
            })
            
            print(f"✓ Synced {len(skills)} skills")
            
        except Exception as e:
            print(f"✗ Error syncing skills: {e}")
    
    def sync_session_state(self):
        """Sync current session state."""
        # Find session files
        sessions = list(HERMES_HOME.glob('session_*.json'))
        
        if sessions:
            latest = max(sessions, key=lambda p: p.stat().st_mtime)
            try:
                with open(latest) as f:
                    data = json.load(f)
                
                self._emit_to_ledger('HERMES_SESSION', {
                    'file': latest.name,
                    'timestamp': data.get('timestamp', time.time()),
                    'size': len(json.dumps(data))
                })
                
                print(f"✓ Synced session: {latest.name}")
                
            except Exception as e:
                print(f"✗ Error syncing session: {e}")
    
    def run_full_sync(self):
        """Run complete sync."""
        print("="*50)
        print("  HERMES → HIVE MEMORY SYNC")
        print("="*50 + "\n")
        
        self.sync_user_preferences()
        self.sync_skills()
        self.sync_session_state()
        
        # Emit completion event
        self._emit_to_ledger('SYNC_COMPLETE', {
            'timestamp': time.time(),
            'source': 'hermes-memory-sync'
        })
        
        print("\n✓ Sync complete")
        return 0


def main():
    sync = HermesMemorySync()
    return sync.run_full_sync()


if __name__ == '__main__':
    sys.exit(main())

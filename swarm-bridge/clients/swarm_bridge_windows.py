#!/usr/bin/env python3
"""
SWARM BRIDGE CLIENT - Windows Node
Git-based message transport for Hive Swarm
"""

import os
import json
import uuid
import time
import subprocess
from pathlib import Path
from datetime import datetime

# CONFIG
MY_NODE = "node_2_windows"
PEER_NODE = "node_1_termux"
REPO_URL = "https://github.com/kaibuzz0/the-hive-tools.git"
BRIDGE_DIR = Path("D:/Hermes-USB-Portable-main/the-hive-tools/swarm-bridge")

class SwarmGitBridge:
    def __init__(self):
        self.pending_dir = BRIDGE_DIR / "messages" / "pending" / f"{MY_NODE}_to_{PEER_NODE}"
        self.inbox_dir = BRIDGE_DIR / "messages" / "pending" / f"{PEER_NODE}_to_{MY_NODE}"
        self.archive_dir = BRIDGE_DIR / "messages" / "archive"
    
    def ensure_repo(self):
        """Clone or pull latest"""
        if not BRIDGE_DIR.exists():
            BRIDGE_DIR.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["git", "clone", REPO_URL, str(BRIDGE_DIR)], check=True)
        else:
            subprocess.run(["git", "-C", str(BRIDGE_DIR), "pull"], capture_output=True)
    
    def send_message(self, payload: str, msg_type: str = "text") -> str:
        """Send message to peer via git"""
        self.ensure_repo()
        
        msg = {
            "id": str(uuid.uuid4())[:8],
            "from": MY_NODE,
            "to": PEER_NODE,
            "timestamp": datetime.utcnow().isoformat(),
            "type": msg_type,
            "payload": payload
        }
        
        # Write to pending
        self.pending_dir.mkdir(parents=True, exist_ok=True)
        msg_file = self.pending_dir / f"{msg['id']}.json"
        msg_file.write_text(json.dumps(msg, indent=2))
        
        # Git commit and push
        try:
            subprocess.run(["git", "-C", str(BRIDGE_DIR), "add", "."], check=True)
            subprocess.run([
                "git", "-C", str(BRIDGE_DIR), "commit",
                "-m", f"[{MY_NODE}] {msg_type}: {payload[:50]}...",
                "--author=Swarm Bot <swarm@hive.local>"
            ], capture_output=True)
            subprocess.run(["git", "-C", str(BRIDGE_DIR), "push"], capture_output=True)
        except subprocess.CalledProcessError:
            pass
        
        return msg["id"]
    
    def receive_messages(self) -> list:
        """Check for messages from peer"""
        self.ensure_repo()
        
        messages = []
        if self.inbox_dir.exists():
            for msg_file in sorted(self.inbox_dir.glob("*.json")):
                try:
                    msg = json.loads(msg_file.read_text())
                    messages.append(msg)
                    
                    # Archive
                    self.archive_dir.mkdir(parents=True, exist_ok=True)
                    archive_path = self.archive_dir / f"{msg['id']}_{int(time.time())}.json"
                    msg_file.rename(archive_path)
                except Exception as e:
                    print(f"Error processing {msg_file}: {e}")
        
        # Commit archive
        if messages:
            try:
                subprocess.run(["git", "-C", str(BRIDGE_DIR), "add", "."], capture_output=True)
                subprocess.run([
                    "git", "-C", str(BRIDGE_DIR), "commit",
                    "-m", f"[{MY_NODE}] Archived {len(messages)} messages from {PEER_NODE}"
                ], capture_output=True)
                subprocess.run(["git", "-C", str(BRIDGE_DIR), "push"], capture_output=True)
            except subprocess.CalledProcessError:
                pass
        
        return messages

# CLI
if __name__ == "__main__":
    import sys
    bridge = SwarmGitBridge()
    
    if len(sys.argv) > 1 and sys.argv[1] == "send":
        msg = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "Ping from Windows!"
        msg_id = bridge.send_message(msg)
        print(f"📤 Sent: {msg_id}")
        
    elif len(sys.argv) > 1 and sys.argv[1] == "receive":
        messages = bridge.receive_messages()
        if messages:
            print(f"📨 {len(messages)} new messages:")
            for m in messages:
                print(f"  [{m['timestamp'][:19]}] {m['payload'][:100]}")
        else:
            print("📭 No new messages")
            
    elif len(sys.argv) > 1 and sys.argv[1] == "daemon":
        # Run as continuous receiver
        print("🐝 Swarm Bridge Daemon started...")
        while True:
            messages = bridge.receive_messages()
            if messages:
                for m in messages:
                    print(f"\n📨 [{m['timestamp'][:19]}] {m['type'].upper()}")
                    print(f"   {m['payload']}")
            time.sleep(10)
            
    else:
        print("Swarm Bridge - Windows Node")
        print("Usage:")
        print("  python swarm_bridge_windows.py send 'Your message'")
        print("  python swarm_bridge_windows.py receive")
        print("  python swarm_bridge_windows.py daemon")

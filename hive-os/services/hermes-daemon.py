#!/usr/bin/env python3
"""
Hermes Daemon Service for Hive OS
Manages Hermes as a persistent background service with Hive integration
"""
import os
import sys
import json
import time
import socket
import signal
import threading
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import subprocess

# Hive paths
HIVE_ROOT = Path('/root/hive-os')
HIVE_SWARM = Path('/root/hive-swarm')
HERMES_HOME = Path('/root/.hermes')
RUN_DIR = HIVE_ROOT / 'run'
LOG_DIR = HIVE_ROOT / 'log'

class HermesDaemon:
    """
    Hermes as a Hive OS service.
    Provides API for AI-OS bidirectional communication.
    """
    
    VERSION = "4.0-HIVE-MIND"
    API_PORT = 14741  # H-I-V-E on phone keypad
    
    def __init__(self):
        self.running = True
        self.state = {
            'status': 'initializing',
            'last_activity': time.time(),
            'commands_processed': 0,
            'errors': 0
        }
        self._ensure_dirs()
        self._setup_signal_handlers()
        
    def _ensure_dirs(self):
        RUN_DIR.mkdir(parents=True, exist_ok=True)
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        
    def _setup_signal_handlers(self):
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)
        
    def _handle_shutdown(self, signum, frame):
        print(f"[HermesDaemon] Received signal {signum}, shutting down...")
        self.running = False
        self._log_event('DAEMON_SHUTDOWN', {'signal': signum})
        
    def _log_event(self, event_type: str, data: dict):
        """Log to both file and Hive ledger."""
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] {event_type}: {json.dumps(data)}\n"
        
        # Local log
        with open(LOG_DIR / 'hermes-daemon.log', 'a') as f:
            f.write(log_entry)
        
        # Hive ledger
        try:
            ledger_script = HIVE_SWARM / 'services' / 'resonance_ledger.py'
            if ledger_script.exists():
                subprocess.run([
                    sys.executable, str(ledger_script),
                    'emit', '--type', f'HERMES_{event_type}',
                    '--payload', json.dumps(data)
                ], capture_output=True, timeout=3)
        except:
            pass
    
    def _sync_memory_to_ledger(self):
        """Sync Hermes memory files to Hive ledger."""
        memory_dir = HERMES_HOME
        if not memory_dir.exists():
            return
        
        # Scan memory files
        for mem_file in memory_dir.glob('*.json'):
            try:
                with open(mem_file) as f:
                    data = json.load(f)
                
                # Emit to ledger
                self._log_event('MEMORY_SYNC', {
                    'file': mem_file.name,
                    'keys': list(data.keys()),
                    'size': len(json.dumps(data))
                })
            except:
                pass
    
    def _create_api_handler(self):
        """Create HTTP API for Hive-Hermes communication."""
        daemon = self  # Reference for closure
        
        class APIHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass  # Suppress default logging
            
            def do_GET(self):
                if self.path == '/status':
                    self._send_json(200, daemon.state)
                elif self.path == '/health':
                    self._send_json(200, {'status': 'healthy', 'version': daemon.VERSION})
                else:
                    self._send_json(404, {'error': 'Not found'})
            
            def do_POST(self):
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length).decode()
                
                try:
                    data = json.loads(body)
                except:
                    self._send_json(400, {'error': 'Invalid JSON'})
                    return
                
                if self.path == '/command':
                    result = daemon._process_command(data.get('command'), data.get('args', []))
                    self._send_json(200, {'result': result})
                elif self.path == '/query':
                    result = daemon._process_query(data.get('query'))
                    self._send_json(200, {'result': result})
                else:
                    self._send_json(404, {'error': 'Not found'})
            
            def _send_json(self, status, data):
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(data).encode())
        
        return APIHandler
    
    def _process_command(self, command: str, args: list) -> dict:
        """Process incoming command from Hive."""
        self.state['commands_processed'] += 1
        self.state['last_activity'] = time.time()
        
        if command == 'sync_memory':
            self._sync_memory_to_ledger()
            return {'status': 'synced'}
        
        elif command == 'get_context':
            return self._load_context()
        
        elif command == 'log_event':
            self._log_event(args.get('type', 'UNKNOWN'), args.get('data', {}))
            return {'status': 'logged'}
        
        else:
            return {'error': f'Unknown command: {command}'}
    
    def _process_query(self, query: str) -> dict:
        """Process query from Hive."""
        if query == 'status':
            return self.state
        elif query == 'memory_summary':
            return self._get_memory_summary()
        else:
            return {'error': 'Unknown query'}
    
    def _load_context(self) -> dict:
        """Load Hermes context for Hive."""
        context = {
            'daemon_version': self.VERSION,
            'hermes_home': str(HERMES_HOME),
            'timestamp': time.time(),
            'state': self.state
        }
        
        # Load recent memory
        try:
            user_memory = HERMES_HOME / 'memory' / 'user.json'
            if user_memory.exists():
                with open(user_memory) as f:
                    context['user_prefs'] = json.load(f)
        except:
            pass
        
        return context
    
    def _get_memory_summary(self) -> dict:
        """Get summary of Hermes memory."""
        summary = {
            'files': 0,
            'total_size': 0,
            'types': []
        }
        
        if HERMES_HOME.exists():
            for f in HERMES_HOME.rglob('*.json'):
                try:
                    stat = f.stat()
                    summary['files'] += 1
                    summary['total_size'] += stat.st_size
                except:
                    pass
        
        return summary
    
    def _heartbeat(self):
        """Emit periodic heartbeat to ledger."""
        while self.running:
            self._log_event('HEARTBEAT', {
                'commands': self.state['commands_processed'],
                'errors': self.state['errors'],
                'uptime': time.time() - self.state.get('start_time', time.time())
            })
            time.sleep(300)  # Every 5 minutes
    
    def run(self):
        """Main daemon loop."""
        self.state['start_time'] = time.time()
        self.state['status'] = 'running'
        self._log_event('DAEMON_START', {'version': self.VERSION})
        
        print(f"[HermesDaemon] v{self.VERSION} starting...")
        print(f"[HermesDaemon] API on port {self.API_PORT}")
        
        # Start heartbeat thread
        hb_thread = threading.Thread(target=self._heartbeat, daemon=True)
        hb_thread.start()
        
        # Start API server
        try:
            HTTPServer.allow_reuse_address = True
            server = HTTPServer(('127.0.0.1', self.API_PORT), self._create_api_handler())
            
            print(f"[HermesDaemon] Ready")
            
            while self.running:
                server.handle_request()
                
        except Exception as e:
            self.state['errors'] += 1
            self._log_event('DAEMON_ERROR', {'error': str(e)})
            print(f"[HermesDaemon] Error: {e}")
            return 1
        
        return 0


def main():
    daemon = HermesDaemon()
    return daemon.run()


if __name__ == '__main__':
    sys.exit(main())

# ::SealConfirmed::
# ΩΩΩ

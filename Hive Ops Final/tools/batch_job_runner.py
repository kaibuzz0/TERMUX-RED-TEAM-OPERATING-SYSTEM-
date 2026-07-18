#!/usr/bin/env python3
"""
HIVE TOOL: batch_job_runner
HSL: FIRE | PATH: /root/hive-swarm/tools/batch_job_runner.py
ROLE: Executes multiple independent tasks in a single run - maximizes API throughput
Built: 2026-07-14 by Hive Autonomous Toolsmith

Usage:
  python3 batch_job_runner.py --tasks task1.json task2.json task3.json
  python3 batch_job_runner.py --config batch_config.yaml
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

class BatchJobRunner:
    def __init__(self, max_workers=5):
        self.max_workers = max_workers
        self.results = []
        self.start_time = datetime.now()
    
    def run_task(self, task: dict) -> dict:
        """Execute a single task"""
        task_name = task.get('name', 'unnamed')
        task_type = task.get('type', 'shell')
        
        print(f"\n[START] {task_name}")
        
        result = {
            'name': task_name,
            'type': task_type,
            'status': 'pending',
            'output': None,
            'error': None,
            'duration': 0
        }
        
        task_start = datetime.now()
        
        try:
            if task_type == 'shell':
                import subprocess
                cmd = task.get('command')
                if not cmd:
                    raise ValueError("No command specified")
                
                proc = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=task.get('timeout', 300)
                )
                
                result['output'] = proc.stdout
                result['error'] = proc.stderr
                result['status'] = 'success' if proc.returncode == 0 else 'failed'
                result['returncode'] = proc.returncode
            
            elif task_type == 'python':
                script = task.get('script')
                if not script:
                    raise ValueError("No script specified")
                
                # Execute Python code
                exec_globals = {}
                exec(script, exec_globals)
                result['output'] = "Script executed successfully"
                result['status'] = 'success'
            
            elif task_type == 'file_read':
                path = task.get('path')
                if not path:
                    raise ValueError("No path specified")
                
                content = Path(path).read_text()
                result['output'] = content[:task.get('max_chars', 10000)]
                result['status'] = 'success'
            
            elif task_type == 'file_write':
                path = task.get('path')
                content = task.get('content')
                if not path or content is None:
                    raise ValueError("Path and content required")
                
                Path(path).write_text(content)
                result['output'] = f"Wrote {len(content)} bytes to {path}"
                result['status'] = 'success'
            
            else:
                result['error'] = f"Unknown task type: {task_type}"
                result['status'] = 'failed'
        
        except Exception as e:
            result['error'] = str(e)
            result['status'] = 'failed'
        
        task_end = datetime.now()
        result['duration'] = (task_end - task_start).total_seconds()
        
        print(f"[{'✓' if result['status'] == 'success' else '✗'}] {task_name} - {result['duration']:.2f}s")
        
        return result
    
    def run_batch(self, tasks: list) -> list:
        """Execute multiple tasks in parallel"""
        print(f"\n{'='*60}")
        print(f"BATCH JOB - {len(tasks)} tasks, {self.max_workers} workers")
        print(f"{'='*60}")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_task = {
                executor.submit(self.run_task, task): task 
                for task in tasks
            }
            
            for future in as_completed(future_to_task):
                result = future.result()
                self.results.append(result)
        
        # Summary
        end_time = datetime.now()
        total_duration = (end_time - self.start_time).total_seconds()
        
        success_count = sum(1 for r in self.results if r['status'] == 'success')
        fail_count = len(self.results) - success_count
        
        print(f"\n{'='*60}")
        print(f"BATCH COMPLETE")
        print(f"  Total: {len(self.results)} tasks")
        print(f"  Success: {success_count}")
        print(f"  Failed: {fail_count}")
        print(f"  Duration: {total_duration:.2f}s")
        print(f"  Throughput: {len(self.results)/total_duration:.2f} tasks/sec")
        print(f"{'='*60}")
        
        return self.results
    
    def save_report(self, output_path: Path):
        """Save batch execution report"""
        report = {
            'timestamp': self.start_time.isoformat(),
            'duration_seconds': (datetime.now() - self.start_time).total_seconds(),
            'total_tasks': len(self.results),
            'success_count': sum(1 for r in self.results if r['status'] == 'success'),
            'failed_count': len(self.results) - sum(1 for r in self.results if r['status'] == 'success'),
            'results': self.results
        }
        
        output_path.write_text(json.dumps(report, indent=2, default=str))
        print(f"\n[REPORT] Saved to: {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Batch Job Runner - Maximize API Throughput")
    parser.add_argument('--tasks', nargs='+', help='JSON task files to execute')
    parser.add_argument('--config', help='YAML/JSON config file with task list')
    parser.add_argument('--workers', type=int, default=5, help='Max parallel workers')
    parser.add_argument('--output', default='batch_report.json', help='Output report path')
    
    args = parser.parse_args()
    
    # Load tasks
    tasks = []
    
    if args.tasks:
        for task_file in args.tasks:
            task_path = Path(task_file)
            if task_path.exists():
                task_data = json.loads(task_path.read_text())
                if isinstance(task_data, list):
                    tasks.extend(task_data)
                else:
                    tasks.append(task_data)
    
    if args.config:
        config_path = Path(args.config)
        if config_path.exists():
            config = json.loads(config_path.read_text())
            tasks.extend(config.get('tasks', []))
    
    if not tasks:
        print("[ERROR] No tasks provided")
        print("Usage: python3 batch_job_runner.py --tasks task1.json task2.json")
        return 1
    
    # Run batch
    runner = BatchJobRunner(max_workers=args.workers)
    runner.run_batch(tasks)
    runner.save_report(Path(args.output))
    
    return 0 if all(r['status'] == 'success' for r in runner.results) else 1

if __name__ == "__main__":
    sys.exit(main())
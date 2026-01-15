import os
import time
import subprocess
import signal
import json
from typing import Dict
from common.supabase_client import get_supabase

# Active processes: run_id -> subprocess
processes: Dict[str, subprocess.Popen] = {}

def start_run(payload: Dict) -> str:
    """
    Start a new trading run.
    Payload: { "version": "v4", "config_overrides": {}, "flags": "" }
    """
    try:
        version = payload.get("version", "v4")
        overrides = payload.get("config_overrides", {})
        
        # Construct command
        # Construct command based on version
        cmd = []
        cwd = os.getcwd()
        env = os.environ.copy()
        
        # Add current dir to PYTHONPATH for all versions to ensure imports work
        env["PYTHONPATH"] = cwd + os.pathsep + env.get("PYTHONPATH", "")

        if version == "v4":
            cmd = ["python", "-m", "v4.main", "--no-ui"]
            # Override handling for v4
            if "symbols" in overrides:
                cmd.append("--symbols")
                cmd.extend(overrides["symbols"])

        elif version == "v3":
            # Assuming v3 uses similar structure or live_mock
            cmd = ["python", "-m", "v3.live_mock"]
            if "symbols" in overrides:
                cmd.append("--symbols")
                cmd.extend(overrides["symbols"])
        
        elif version == "v2":
            # v2_modern/main.py
            cmd = ["python", "v2_modern/main.py"]
            # v2 might not support cli args the same way, check if needed
            # For now running it as is

        else:
            return f"error_unknown_version_{version}"

        if not cmd:
            return "error_empty_command"
            
        print(f"[Manager] Starting Run ({version}): {' '.join(cmd)}")
        
        proc = subprocess.Popen(cmd, cwd=cwd, env=env)
        
        return f"pid_{proc.pid}"
            
    except Exception as e:
        print(f"[Manager] Failed to start: {e}")
        return f"error_{e}"

def stop_run(run_id: str):
    # This requires us to know which PID corresponds to which run_id.
    # Since we didn't implement that mapping cleanly yet, we might need a way to look it up.
    # Or, we can broadcast a "STOP" command via DB that the Runner listens to?
    # Implementing "Listen for Stop" in Runner is safer.
    pass

def process_commands():
    sb = get_supabase()
    if not sb.enabled:
        print("Supabase not enabled. Manager exiting.")
        return

    print("[Manager] Listening for commands...")
    
    while True:
        try:
            # Poll for PENDING commands
            res = sb.client.table("commands").select("*").eq("status", "PENDING").limit(1).execute()
            commands = res.data
            
            for cmd in commands:
                print(f"[Manager] Processing command: {cmd['command']}")
                
                # Mark as PROCESSING
                sb.client.table("commands").update({"status": "PROCESSING"}).eq("id", cmd['id']).execute()
                
                result = None
                status = "COMPLETED"
                
                if cmd['command'] == "START_RUN":
                    result = start_run(cmd.get('payload', {}))
                elif cmd['command'] == "STOP_RUN":
                    # For MVP, we can't easily stop specific runs via PID yet without the mapping.
                    # We will assume Runner listens to "runs" table update? 
                    # Or we just kill all python v4/main.py? No.
                    result = "stop_not_implemented_yet"
                else:
                    status = "FAILED"
                    result = "unknown_command"
                
                # Update Command Status
                sb.client.table("commands").update({
                    "status": status, 
                    "result": result
                }).eq("id", cmd['id']).execute()
                
            time.sleep(2.0)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"[Manager] Error loop: {e}")
            time.sleep(5.0)

if __name__ == "__main__":
    process_commands()

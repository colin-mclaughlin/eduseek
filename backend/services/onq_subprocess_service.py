#!/usr/bin/env python3
"""
OnQ Subprocess Service for FastAPI Integration

This service runs OnQ scraping as a separate subprocess to avoid
Windows asyncio event loop issues with Playwright.
"""

import subprocess
import sys
import os
import json
import uuid
import tempfile
from typing import Dict, Optional
import datetime

# Global state for tracking active processes
active_processes = {}
temp_files = {}

def start_onq_sync_subprocess(username: str, password: str) -> Dict:
    """
    Start OnQ sync as a subprocess.
    
    Args:
        username: OnQ username (NetID)
        password: OnQ password
        
    Returns:
        Dict with status information and process ID
    """
    try:
        # Generate unique job ID
        job_id = str(uuid.uuid4())[:8]
        
        # Create temporary files for status and results
        temp_dir = tempfile.gettempdir()
        status_file = os.path.join(temp_dir, f"onq_status_{job_id}.json")
        results_file = os.path.join(temp_dir, f"onq_results_{job_id}.json")
        
        # Store temp file paths for cleanup
        temp_files[job_id] = {
            "status_file": status_file,
            "results_file": results_file
        }
        
        # Prepare command to run the scraper
        script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "integrated_onq_scraper.py")
        cmd = [
            sys.executable, 
            script_path,
            "--username", username,
            "--password", password,
            "--status-file", status_file,
            "--results-file", results_file
        ]
        
        print(f"[SUBPROCESS] Starting OnQ sync with job ID: {job_id}")
        print(f"[SUBPROCESS] Command: {' '.join(cmd[:4])} [credentials hidden]")
        print(f"[SUBPROCESS] Status file: {status_file}")
        
        # Start the subprocess
        if sys.platform.startswith("win"):
            # On Windows, use CREATE_NEW_PROCESS_GROUP to avoid inheriting console
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=creationflags,
                text=True
            )
        else:
            # On Unix-like systems
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        
        # Store process info
        active_processes[job_id] = {
            "process": process,
            "started_at": datetime.datetime.now(),
            "status_file": status_file,
            "results_file": results_file,
            "username": username  # Store for reference (not password for security)
        }
        
        # Initialize status file
        initial_status = {
            "is_running": True,
            "current_step": "starting",
            "progress": 0,
            "message": "Starting OnQ sync subprocess...",
            "error": None,
            "results": None,
            "job_id": job_id
        }
        
        try:
            with open(status_file, 'w', encoding='utf-8') as f:
                json.dump(initial_status, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Warning: Could not write initial status file: {e}")
        
        return {
            "status": "started",
            "message": "OnQ sync started as subprocess",
            "job_id": job_id,
            "process_id": process.pid
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to start OnQ sync subprocess: {str(e)}",
            "job_id": None
        }

def get_onq_sync_status(job_id: Optional[str] = None) -> Dict:
    """
    Get the current status of OnQ sync process.
    
    Args:
        job_id: Optional job ID. If None, returns status of most recent job.
        
    Returns:
        Dict with current sync status information
    """
    try:
        # If no job_id provided, use the most recent one
        if not job_id and active_processes:
            job_id = max(active_processes.keys(), key=lambda k: active_processes[k]["started_at"])
        
        if not job_id or job_id not in active_processes:
            return {
                "is_running": False,
                "current_step": "idle",
                "progress": 0,
                "message": "No sync process found",
                "error": None,
                "results": None,
                "job_id": job_id
            }
        
        process_info = active_processes[job_id]
        status_file = process_info["status_file"]
        process = process_info["process"]
        
        # Check if process is still running
        poll_result = process.poll()
        
        # Try to read status from file
        status = {
            "is_running": poll_result is None,
            "current_step": "unknown",
            "progress": 0,
            "message": "No status available",
            "error": None,
            "results": None,
            "job_id": job_id
        }
        
        if os.path.exists(status_file):
            try:
                with open(status_file, 'r', encoding='utf-8') as f:
                    file_status = json.load(f)
                    status.update(file_status)
                    status["job_id"] = job_id  # Ensure job_id is always set
            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"Warning: Could not read status file: {e}")
        
        # If process finished but status file says it's still running, update it
        if poll_result is not None and status.get("is_running", True):
            # Process finished, check for results
            results_file = process_info["results_file"]
            results = None
            
            if os.path.exists(results_file):
                try:
                    with open(results_file, 'r', encoding='utf-8') as f:
                        results = json.load(f)
                except (json.JSONDecodeError, FileNotFoundError) as e:
                    print(f"Warning: Could not read results file: {e}")
            
            # Update status based on process exit code
            if poll_result == 0:
                # Success
                status.update({
                    "is_running": False,
                    "current_step": "completed",
                    "progress": 100,
                    "message": "OnQ sync completed successfully",
                    "error": None,
                    "results": results
                })
            else:
                # Error
                error_msg = "OnQ sync process failed"
                try:
                    # Try to get stderr from process
                    _, stderr = process.communicate(timeout=1)
                    if stderr:
                        error_msg = f"OnQ sync failed: {stderr.strip()}"
                except subprocess.TimeoutExpired:
                    pass
                except Exception as e:
                    print(f"Warning: Could not get process error output: {e}")
                
                status.update({
                    "is_running": False,
                    "current_step": "error",
                    "progress": 0,
                    "message": error_msg,
                    "error": error_msg,
                    "results": None
                })
        
        return status
        
    except Exception as e:
        return {
            "is_running": False,
            "current_step": "error",
            "progress": 0,
            "message": f"Error checking sync status: {str(e)}",
            "error": str(e),
            "results": None,
            "job_id": job_id
        }

def cleanup_completed_processes():
    """Clean up completed processes and their temporary files."""
    completed_jobs = []
    
    for job_id, process_info in active_processes.items():
        process = process_info["process"]
        if process.poll() is not None:  # Process finished
            completed_jobs.append(job_id)
    
    for job_id in completed_jobs:
        # Clean up temp files
        if job_id in temp_files:
            temp_info = temp_files[job_id]
            for file_path in temp_info.values():
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        print(f"[CLEANUP] Removed temp file: {file_path}")
                except Exception as e:
                    print(f"Warning: Could not remove temp file {file_path}: {e}")
            del temp_files[job_id]
        
        # Remove from active processes
        if job_id in active_processes:
            del active_processes[job_id]
            print(f"[CLEANUP] Cleaned up completed job: {job_id}")

def stop_onq_sync(job_id: str) -> Dict:
    """
    Stop a running OnQ sync process.
    
    Args:
        job_id: Job ID of the process to stop
        
    Returns:
        Dict with stop status
    """
    try:
        if job_id not in active_processes:
            return {
                "status": "error",
                "message": f"No active process found with job ID: {job_id}"
            }
        
        process = active_processes[job_id]["process"]
        
        if process.poll() is None:  # Process is still running
            process.terminate()
            try:
                process.wait(timeout=5)  # Wait up to 5 seconds for graceful shutdown
            except subprocess.TimeoutExpired:
                process.kill()  # Force kill if it doesn't terminate gracefully
            
            return {
                "status": "stopped",
                "message": f"OnQ sync process {job_id} stopped successfully"
            }
        else:
            return {
                "status": "already_finished",
                "message": f"Process {job_id} was already finished"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to stop process {job_id}: {str(e)}"
        }

def get_active_jobs() -> Dict:
    """Get information about all active jobs."""
    cleanup_completed_processes()  # Clean up first
    
    jobs = {}
    for job_id, process_info in active_processes.items():
        jobs[job_id] = {
            "started_at": process_info["started_at"].isoformat(),
            "username": process_info["username"],
            "process_id": process_info["process"].pid,
            "is_running": process_info["process"].poll() is None
        }
    
    return {
        "active_jobs": jobs,
        "total_active": len(jobs)
    }
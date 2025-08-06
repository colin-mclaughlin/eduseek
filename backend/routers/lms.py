from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from pydantic import BaseModel
from services.lms_scraper import scrape_lms_files, LMS_TYPE
from services.lms_scraper_real import scrape_real_lms
from services.onq_subprocess_service import start_onq_sync_subprocess, get_onq_sync_status, get_active_jobs
import sys

router = APIRouter()

class LMSImportRequest(BaseModel):
    lms_type: str  # Changed from LMS_TYPE to str to support both mock and real types
    username: str
    password: str

class OnQSyncRequest(BaseModel):
    username: str
    password: str

@router.post("/import/lms", status_code=200)
async def import_lms_files(request: LMSImportRequest):
    """
    Import course files from an LMS using either mock or real scraping.
    Supports:
    - 'brightspace': Mock LMS scraping with file processing
    - 'brightspace-real': Real Playwright-based Brightspace login
    """
    try:
        print(f"[LMS ROUTER] Received request for {request.lms_type}")
        
        # Route to appropriate scraper based on lms_type
        if request.lms_type == "brightspace-real":
            print("[LMS ROUTER] Using real LMS scraper for Brightspace")
            result = await scrape_real_lms(request.lms_type, request.username, request.password)
        elif request.lms_type == "brightspace":
            print("[LMS ROUTER] Using mock LMS scraper for Brightspace")
            result = await scrape_lms_files(request.lms_type, request.username, request.password)
        else:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported LMS type: {request.lms_type}. Supported types: 'brightspace', 'brightspace-real'"
            )
        
        print(f"[LMS ROUTER] Scraper result: {result}")
        
        if result.get("status") == "success":
            return {
                "message": result.get("message", "LMS import successful."), 
                "files": result.get("files", []),
                "processed": result.get("processed", 0),
                "url": result.get("url", None),
                "details": result.get("details", {})
            }
        elif result.get("status") == "twofa_required":
            return {
                "status": "twofa_required",
                "message": result.get("message", "Two-factor authentication required"),
                "url": result.get("url", None),
                "twofa_number": result.get("twofa_number", None),
                "details": result.get("details", {})
            }
        else:
            error_msg = result.get("message", "Unknown error")
            print(f"[LMS ROUTER] Scraping failed: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail=f"LMS scraping failed: {error_msg}"
            )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[LMS ROUTER] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Unexpected error during LMS import: {str(e)}"
        )

@router.post("/sync_lms", status_code=200)
async def sync_onq_lms(request: OnQSyncRequest):
    """
    Start OnQ sync process as a subprocess.
    Returns immediately with a job ID for status polling.
    """
    try:
        # Check if there's already an active sync running
        active_jobs = get_active_jobs()
        if active_jobs["total_active"] > 0:
            # Find the running job
            running_job = None
            for job_id, job_info in active_jobs["active_jobs"].items():
                if job_info["is_running"]:
                    running_job = job_id
                    break
            
            if running_job:
                raise HTTPException(
                    status_code=400,
                    detail=f"OnQ sync is already in progress (Job ID: {running_job}). Please wait for it to complete."
                )
        
        # Use subprocess on Windows, or if explicitly requested
        if sys.platform.startswith("win"):
            print("[OnQ SYNC] Starting OnQ sync as subprocess (Windows)")
            result = start_onq_sync_subprocess(request.username, request.password)
        else:
            print("[OnQ SYNC] Starting OnQ sync as subprocess (non-Windows)")
            result = start_onq_sync_subprocess(request.username, request.password)
        
        if result["status"] == "error":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["message"]
            )
        
        return {
            "status": "started",
            "message": "OnQ sync started as subprocess. Use /api/sync_lms/status to check progress.",
            "job_id": result["job_id"],
            "process_id": result.get("process_id")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[OnQ SYNC] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start OnQ sync: {str(e)}"
        )

@router.get("/sync_lms/status", status_code=200)
async def get_onq_sync_status_endpoint(job_id: str = None):
    """
    Get the current status of OnQ sync process.
    Used for polling progress updates.
    
    Args:
        job_id: Optional job ID. If not provided, returns status of most recent job.
    """
    try:
        status_info = get_onq_sync_status(job_id)
        return {
            "is_running": status_info["is_running"],
            "current_step": status_info["current_step"],
            "progress": status_info["progress"],
            "message": status_info["message"],
            "error": status_info["error"],
            "results": status_info["results"],
            "job_id": status_info["job_id"],
            "twofa_number": status_info.get("twofa_number")
        }
    except Exception as e:
        print(f"[OnQ STATUS] Error getting status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get sync status: {str(e)}"
        )

@router.get("/sync_lms/jobs", status_code=200)
async def get_active_sync_jobs():
    """
    Get information about all active OnQ sync jobs.
    """
    try:
        return get_active_jobs()
    except Exception as e:
        print(f"[OnQ JOBS] Error getting active jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get active jobs: {str(e)}"
        ) 
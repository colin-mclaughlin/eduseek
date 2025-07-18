from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from services.lms_scraper import scrape_lms_files, LMS_TYPE
from services.lms_scraper_real import scrape_real_lms

router = APIRouter()

class LMSImportRequest(BaseModel):
    lms_type: str  # Changed from LMS_TYPE to str to support both mock and real types
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
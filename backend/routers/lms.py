from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from services.lms_scraper import scrape_lms_files, LMS_TYPE

router = APIRouter()

class LMSImportRequest(BaseModel):
    lms_type: LMS_TYPE
    username: str
    password: str

@router.post("/import/lms", status_code=200)
async def import_lms_files(request: LMSImportRequest):
    """
    Import course files from an LMS using Playwright-based scraping.
    """
    try:
        print(f"[LMS ROUTER] Received request for {request.lms_type}")
        result = await scrape_lms_files(request.lms_type, request.username, request.password)
        print(f"[LMS ROUTER] Scraper result: {result}")
        
        if result.get("status") == "success":
            return {
                "message": result.get("message", "LMS import successful."), 
                "files": result.get("files", [])
            }
        else:
            error_msg = result.get("error", "Unknown error")
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
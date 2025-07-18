from typing import Literal
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from fastapi import HTTPException
import asyncio
import sys
import os
import subprocess
import json

# Supported LMS types for real scraping
LMS_TYPE = Literal["brightspace-real", "moodle-real", "canvas-real"]

class LMSRealScraperError(Exception):
    pass

BRIGHTSPACE_URL = "https://onq.queensu.ca/"

async def scrape_real_lms(lms_type: str, username: str, password: str) -> dict:
    """
    Real LMS scraping implementation using Playwright.
    Currently supports Brightspace login flow.
    """
    print(f"[LMS REAL] Starting real LMS scrape for {lms_type}")
    print(f"[LMS REAL] Platform: {sys.platform}")
    print(f"[LMS REAL] Python version: {sys.version}")
    print(f"[LMS REAL] Current working directory: {os.getcwd()}")
    
    if lms_type != "brightspace-real":
        raise NotImplementedError(f"Real LMS type '{lms_type}' is not supported yet.")
    
    try:
        print("[LMS REAL] Using subprocess approach for Windows compatibility...")
        
        if lms_type != "brightspace-real":
            raise NotImplementedError(f"Real LMS type '{lms_type}' is not supported yet.")
        
        # Use subprocess to run the standalone Playwright script
        result = subprocess.run(
            [sys.executable, "playwright_scraper_runner.py", username, password],
            cwd=os.getcwd(),
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            print(f"[LMS REAL] Subprocess failed with return code {result.returncode}")
            print(f"[LMS REAL] stderr: {result.stderr}")
            raise HTTPException(status_code=500, detail=f"Scraping failed: {result.stderr.strip()}")

        output = result.stdout.strip()
        print(f"[LMS REAL] Subprocess output: {output}")
        
        # Find the last JSON object in the output (in case there's extra output)
        lines = output.split('\n')
        json_line = None
        for line in reversed(lines):
            line = line.strip()
            if line.startswith('{') and line.endswith('}'):
                json_line = line
                break
        
        if not json_line:
            print(f"[LMS REAL] No JSON found in output")
            raise HTTPException(status_code=500, detail="No JSON response from scraper")
        
        try:
            parsed = json.loads(json_line)
        except json.JSONDecodeError as e:
            print(f"[LMS REAL] Failed to parse JSON output: {e}")
            print(f"[LMS REAL] JSON line: {json_line}")
            raise HTTPException(status_code=500, detail="Invalid response from scraper")

        if parsed.get("status") == "success":
            return {
                "status": "success",
                "message": parsed.get("message", "Login successful"),
                "url": parsed.get("url", ""),
                "details": {
                    "lms_type": lms_type,
                    "username": username,
                    "login_successful": True
                }
            }
        elif parsed.get("status") == "twofa_required":
            return {
                "status": "twofa_required",
                "message": parsed.get("message", "Two-factor authentication required"),
                "url": parsed.get("url", ""),
                "details": {
                    "lms_type": lms_type,
                    "username": username,
                    "login_successful": False,
                    "twofa_required": True
                }
            }
        elif parsed.get("status") == "failure":
            raise HTTPException(status_code=401, detail=parsed.get("message", "Login failed"))
        else:
            raise HTTPException(status_code=500, detail=parsed.get("message", "Unknown error"))
                
    except NotImplementedError as e:
        print(f"[LMS REAL] NotImplementedError: {e}")
        raise e
    except HTTPException as e:
        print(f"[LMS REAL] HTTPException: {e}")
        raise e
    except subprocess.TimeoutExpired:
        print("[LMS REAL] Subprocess timeout")
        raise HTTPException(status_code=500, detail="Scraping timed out")
    except Exception as e:
        print(f"[LMS REAL] General exception: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Real LMS scraping failed: {str(e)}") 
#!/usr/bin/env python3
"""
OnQ Sync Service for FastAPI Integration

This service provides async functions that can be called from FastAPI endpoints
to handle OnQ scraping and ingestion without CLI interaction.
"""

import asyncio
import os
import sys
from typing import Dict, Optional, List
from playwright.async_api import async_playwright
import datetime
import json

# Add the current directory to Python path to ensure imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the login function (now async Playwright)
from playwright_scraper_runner import login_and_get_session

# Import the scraping function (async Playwright)
from lms_scraper.scrape_onq_files import scrape_onq_files_with_authentication

# Import the ingestion function
from lms_scraper.ingest_downloaded_files import ingest_course_json

# Global state for tracking sync progress
sync_status = {
    "is_running": False,
    "current_step": "idle",
    "progress": 0,
    "message": "No sync in progress",
    "error": None,
    "results": None,
    "batch_id": None
}

async def sync_onq_files(username: str, password: str) -> Dict:
    """
    Main integration function that orchestrates login and scraping for API calls.
    
    Args:
        username: OnQ username (NetID)
        password: OnQ password
        
    Returns:
        Dict with keys:
        - status: "success", "error", or "twofa_required"
        - message: Human-readable status message
        - files: List of scraped files (if successful)
        - batch_id: Scrape batch ID for tracking
        - processed: Number of files processed
        - uploaded: Number of files uploaded to backend
        - duplicates: Number of duplicate files
        - failed: Number of failed uploads
    """
    global sync_status
    
    # Initialize sync status
    batch_id = datetime.datetime.now().strftime('onq_batch_%Y%m%d-%H%M%S')
    sync_status.update({
        "is_running": True,
        "current_step": "initializing",
        "progress": 0,
        "message": "Starting OnQ sync...",
        "error": None,
        "results": None,
        "batch_id": batch_id
    })
    
    try:
        # Validate inputs
        if not username or not password:
            raise ValueError("Username and password are required")
            
        # Step 1: Initialize Playwright and login
        sync_status.update({
            "current_step": "login",
            "progress": 20,
            "message": "Logging into OnQ..."
        })
        
        browser = None
        files = []
        
        async with async_playwright() as p:
            try:
                browser, context, page = await login_and_get_session(p, username, password)
                
                sync_status.update({
                    "current_step": "scraping",
                    "progress": 40,
                    "message": "Login successful, starting file scraping..."
                })
                
                # Step 2: Run async scraping (inside the Playwright context)
                scrape_result = await scrape_onq_files_with_authentication(
                    browser, 
                    context, 
                    page, 
                    batch_id
                )
                
                sync_status.update({
                    "current_step": "processing",
                    "progress": 70,
                    "message": "Processing scraped files..."
                })
                
            except Exception as e:
                error_msg = str(e)
                if "2FA" in error_msg or "two-factor" in error_msg.lower():
                    sync_status.update({
                        "is_running": False,
                        "current_step": "error",
                        "progress": 0,
                        "message": "Two-factor authentication required",
                        "error": error_msg
                    })
                    return {
                        "status": "twofa_required",
                        "message": "Please complete two-factor authentication and try again",
                        "batch_id": batch_id
                    }
                else:
                    raise e
            finally:
                # Clean up browser
                if browser:
                    try:
                        await browser.close()
                    except:
                        pass
        
        # Step 3: Process results and ingest files
        files = scrape_result.get('files', [])
        course_json_path = scrape_result.get('course_json_path')
        course_id = scrape_result.get('course_id')
        course_name = scrape_result.get('course_name')
        
        uploaded = 0
        duplicate = 0
        failed = 0
        missing = 0
        
        if course_json_path and os.path.exists(course_json_path):
            sync_status.update({
                "current_step": "ingesting",
                "progress": 90,
                "message": "Ingesting files into backend..."
            })
            
            try:
                uploaded, duplicate, failed, missing = ingest_course_json(
                    course_json_path,
                    backend_url="http://localhost:8000",
                    course_id_override=course_id,
                    course_name_override=course_name,
                    scrape_batch_id=batch_id
                )
            except Exception as e:
                print(f"Ingestion error: {e}")
                failed = len(files)
        
        # Step 4: Update final status
        sync_status.update({
            "is_running": False,
            "current_step": "completed",
            "progress": 100,
            "message": f"Sync complete! {uploaded} files uploaded, {duplicate} duplicates, {failed} failed",
            "error": None,
            "results": {
                "files": files,
                "uploaded": uploaded,
                "duplicates": duplicate,
                "failed": failed,
                "missing": missing,
                "course_id": course_id,
                "course_name": course_name
            }
        })
        
        return {
            "status": "success",
            "message": f"Successfully synced {len(files)} files from OnQ",
            "files": files,
            "batch_id": batch_id,
            "processed": len(files),
            "uploaded": uploaded,
            "duplicates": duplicate,
            "failed": failed,
            "course_id": course_id,
            "course_name": course_name
        }
        
    except Exception as e:
        error_msg = str(e)
        sync_status.update({
            "is_running": False,
            "current_step": "error",
            "progress": 0,
            "message": f"Sync failed: {error_msg}",
            "error": error_msg
        })
        
        return {
            "status": "error",
            "message": f"OnQ sync failed: {error_msg}",
            "batch_id": batch_id
        }

def get_sync_status() -> Dict:
    """
    Get the current sync status for polling.
    
    Returns:
        Dict with current sync status information
    """
    return dict(sync_status)

def reset_sync_status():
    """Reset sync status to idle state."""
    global sync_status
    sync_status.update({
        "is_running": False,
        "current_step": "idle",
        "progress": 0,
        "message": "No sync in progress",
        "error": None,
        "results": None,
        "batch_id": None
    })
#!/usr/bin/env python3
"""
Integrated OnQ Scraper

This script combines the automated login flow from playwright_scraper_runner.py
with the file scraping functionality from scrape_onq_files.py.

Usage:
    python integrated_onq_scraper.py

The script will prompt for username and password, then automatically:
1. Log into OnQ using the automated flow
2. Navigate to the dashboard
3. Present course selection options
4. Scrape files from the selected course
5. Report results and close browser
"""

import asyncio
import getpass
import sys
import os
import argparse
import json
from typing import List, Dict
from playwright.async_api import async_playwright

# Add the current directory to Python path to ensure imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the login function (now async Playwright)
from playwright_scraper_runner import login_and_get_session

# Import the scraping function (async Playwright)
from lms_scraper.scrape_onq_files import scrape_onq_files_with_authentication

# Import the ingestion function
from lms_scraper.ingest_downloaded_files import ingest_course_json


def parse_arguments():
    """
    Parse command line arguments for OnQ credentials and options.
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(description='OnQ File Scraper')
    parser.add_argument('--username', type=str, help='OnQ username (NetID)')
    parser.add_argument('--password', type=str, help='OnQ password')
    parser.add_argument('--status-file', type=str, default='onq_sync_status.json', 
                        help='JSON file to write status updates')
    parser.add_argument('--results-file', type=str, default='onq_sync_results.json',
                        help='JSON file to write final results')
    parser.add_argument('--interactive', action='store_true', 
                        help='Use interactive mode for credentials')
    return parser.parse_args()

def get_user_credentials():
    """
    Prompt user for OnQ credentials (legacy interactive mode).
    
    Returns:
        tuple: (username, password)
    """
    print("*** OnQ Login Credentials Required ***")
    print("=" * 40)
    
    # Get username
    username = input("Enter your OnQ username (NetID): ").strip()
    if not username:
        print("ERROR: Username cannot be empty")
        sys.exit(1)
    
    # Get password securely (hidden input)
    try:
        password = getpass.getpass("Enter your OnQ password: ")
        if not password:
            print("ERROR: Password cannot be empty")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\nERROR: Login cancelled by user")
        sys.exit(1)
    
    return username, password

def write_status_update(status_file, step, progress, message, error=None, twofa_number=None):
    """Write status update to JSON file for API polling."""
    status = {
        "is_running": True,
        "current_step": step,
        "progress": progress,
        "message": message,
        "error": error,
        "timestamp": asyncio.get_event_loop().time() if asyncio.get_event_loop().is_running() else 0
    }
    
    # Add 2FA number if provided
    if twofa_number is not None:
        status["twofa_number"] = twofa_number
        
    try:
        with open(status_file, 'w', encoding='utf-8') as f:
            json.dump(status, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Warning: Could not write status file: {e}")

def write_final_results(results_file, results):
    """Write final results to JSON file."""
    try:
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Warning: Could not write results file: {e}")


async def main():
    """
    Main integration function that orchestrates login and scraping.
    """
    # Parse command line arguments
    args = parse_arguments()
    
    print("*** Integrated OnQ File Scraper ***")
    print("=" * 50)
    
    # Step 1: Get user credentials
    try:
        if args.interactive or (not args.username or not args.password):
            # Interactive mode
            username, password = get_user_credentials()
        else:
            # CLI mode
            username, password = args.username, args.password
            
        print(f"Username: {username}")
        print("Password: [hidden]")
        
        # Initialize status tracking
        write_status_update(args.status_file, "initializing", 0, "Starting OnQ sync...")
        
    except Exception as e:
        error_msg = f"Error getting credentials: {e}"
        print(f"ERROR: {error_msg}")
        write_status_update(args.status_file, "error", 0, error_msg, str(e))
        return
    
    # Step 2: Initialize Playwright context and perform async login
    print("\nStep 1: Initializing browser and logging into OnQ...")
    write_status_update(args.status_file, "login", 20, "Logging into OnQ...")
    browser = None
    files = []
    
    # Create status callback function for real-time updates during login
    async def status_callback(step, progress, message, twofa_number=None):
        write_status_update(args.status_file, step, progress, message, twofa_number=twofa_number)
    
    async with async_playwright() as p:
        try:
            browser, context, page, twofa_number = await login_and_get_session(p, username, password, status_callback)
            
            # Handle 2FA if detected
            if twofa_number:
                print(f"SUCCESS: Login with 2FA completed! Number was: {twofa_number}")
                write_status_update(args.status_file, "login_complete", 35, "Two-factor authentication completed, proceeding to file scraping...", twofa_number=None)
            else:
                print("SUCCESS: Login successful! OnQ dashboard loaded.")
                write_status_update(args.status_file, "login_complete", 35, "Login successful, proceeding to file scraping...", twofa_number=None)
                
            print(f"Current URL: {page.url}")
            
            # Step 3: Run async scraping (inside the Playwright context)
            print("\nStep 2: Starting file scraping...")
            write_status_update(args.status_file, "scraping", 40, "Login successful, starting file scraping...")
            scrape_result = {}
            try:
                import datetime
                scrape_batch_id = datetime.datetime.now().strftime('batch_%Y%m%d-%H%M%S')
                print(f"Scrape batch ID: {scrape_batch_id}")
                
                scrape_result = await scrape_onq_files_with_authentication(
                    browser, 
                    context, 
                    page, 
                    scrape_batch_id
                )
                write_status_update(args.status_file, "processing", 70, "Processing scraped files...")
            except Exception as e:
                error_msg = f"Scraping failed: {e}"
                print(f"ERROR: {error_msg}")
                write_status_update(args.status_file, "error", 0, error_msg, str(e))
                scrape_result = {'files': []}
            
        except Exception as e:
            error_msg = f"Login failed: {e}"
            print(f"ERROR: {error_msg}")
            if "2FA" in str(e) or "two-factor" in str(e).lower():
                write_status_update(args.status_file, "error", 0, "Two-factor authentication required", str(e))
            else:
                write_status_update(args.status_file, "error", 0, error_msg, str(e))
            return
        finally:
            # Step 4: Clean up browser (happens automatically when context exits)
            print("\nStep 3: Cleaning up...")
            try:
                if browser:
                    await browser.close()
                    print("SUCCESS: Browser closed successfully")
            except Exception as e:
                print(f"WARNING: Error closing browser: {e}")
    
    # Step 5: Report scraping results and ingest files (outside the Playwright context)
    files = scrape_result.get('files', [])
    print("\nScraping Results:")
    print("=" * 30)
    
    uploaded = 0
    duplicate = 0
    failed = 0
    missing = 0
    
    if files:
        print(f"SUCCESS: Successfully scraped {len(files)} files")
        print("\nFile Summary:")
        file_types = {}
        for file_info in files:
            file_type = file_info.get('file_type', 'unknown')
            file_types[file_type] = file_types.get(file_type, 0) + 1
        
        for file_type, count in sorted(file_types.items()):
            print(f"   * {file_type}: {count} files")
        
        # Step 6: Ingest the scraped files into backend
        course_json_path = scrape_result.get('course_json_path')
        course_id = scrape_result.get('course_id')
        course_name = scrape_result.get('course_name')
        scrape_batch_id = scrape_result.get('scrape_batch_id')
        
        if course_json_path and os.path.exists(course_json_path):
            print("\nIngesting scraped files into backend...")
            write_status_update(args.status_file, "ingesting", 90, "Ingesting files into backend...")
            try:
                uploaded, duplicate, failed, missing = ingest_course_json(
                    course_json_path,
                    backend_url="http://localhost:8000",
                    course_id_override=course_id,
                    course_name_override=course_name,
                    scrape_batch_id=scrape_batch_id
                )
                print(f"\nIngestion Complete:")
                print(f"   SUCCESS: Uploaded: {uploaded}")
                print(f"   SKIPPED: Duplicates: {duplicate}")
                print(f"   ERROR: Failed: {failed}")
                print(f"   WARNING: Missing: {missing}")
            except Exception as e:
                error_msg = f"Ingestion failed: {e}"
                print(f"ERROR: {error_msg}")
                write_status_update(args.status_file, "error", 0, error_msg, str(e))
                failed = len(files)
        else:
            print(f"WARNING: Course metadata file not found: {course_json_path}")
    else:
        print("ERROR: No files were scraped")
    
    print(f"\nTotal files scraped: {len(files)}")
    print("SUCCESS: Integration complete!")
    
    # Write final results
    final_results = {
        "status": "completed" if not files or uploaded > 0 else "failed",
        "files": files,
        "uploaded": uploaded,
        "duplicates": duplicate,
        "failed": failed,
        "missing": missing,
        "course_id": scrape_result.get('course_id'),
        "course_name": scrape_result.get('course_name'),
        "batch_id": scrape_result.get('scrape_batch_id'),
        "total_files": len(files)
    }
    
    # Write completion status
    if final_results["status"] == "completed":
        write_status_update(args.status_file, "completed", 100, 
                          f"Sync complete! {uploaded} files uploaded, {duplicate} duplicates, {failed} failed")
    else:
        write_status_update(args.status_file, "completed", 100, 
                          f"Sync completed with issues. {len(files)} files found but {failed} failed to upload")
    
    # Mark as not running and write final results
    final_status = {
        "is_running": False,
        "current_step": "completed",
        "progress": 100,
        "message": final_results["status"],
        "error": None,
        "results": final_results
    }
    
    try:
        with open(args.status_file, 'w', encoding='utf-8') as f:
            json.dump(final_status, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Warning: Could not write final status: {e}")
        
    write_final_results(args.results_file, final_results)


if __name__ == "__main__":
    try:
        # Run the async main function
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nERROR: Script interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        sys.exit(1)
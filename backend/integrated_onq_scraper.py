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


def get_user_credentials():
    """
    Prompt user for OnQ credentials.
    
    Returns:
        tuple: (username, password)
    """
    print("🔐 OnQ Login Credentials Required")
    print("=" * 40)
    
    # Get username
    username = input("Enter your OnQ username (NetID): ").strip()
    if not username:
        print("❌ Username cannot be empty")
        sys.exit(1)
    
    # Get password securely (hidden input)
    try:
        password = getpass.getpass("Enter your OnQ password: ")
        if not password:
            print("❌ Password cannot be empty")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n❌ Login cancelled by user")
        sys.exit(1)
    
    return username, password


async def main():
    """
    Main integration function that orchestrates login and scraping.
    """
    print("🎓 Integrated OnQ File Scraper")
    print("=" * 50)
    
    # Step 1: Get user credentials
    try:
        username, password = get_user_credentials()
        print(f"👤 Username: {username}")
        print("🔒 Password: [hidden]")
    except Exception as e:
        print(f"❌ Error getting credentials: {e}")
        return
    
    # Step 2: Initialize Playwright context and perform async login
    print("\n🚀 Step 1: Initializing browser and logging into OnQ...")
    browser = None
    files = []
    
    async with async_playwright() as p:
        try:
            browser, context, page = await login_and_get_session(p, username, password)
            print("✅ Login successful! OnQ dashboard loaded.")
            print(f"📍 Current URL: {page.url}")
            
            # Step 3: Run async scraping (inside the Playwright context)
            print("\n🗂️ Step 2: Starting file scraping...")
            scrape_result = {}
            try:
                import datetime
                scrape_batch_id = datetime.datetime.now().strftime('batch_%Y%m%d-%H%M%S')
                print(f"📋 Scrape batch ID: {scrape_batch_id}")
                
                scrape_result = await scrape_onq_files_with_authentication(
                    browser, 
                    context, 
                    page, 
                    scrape_batch_id
                )
            except Exception as e:
                print(f"❌ Scraping failed: {e}")
                scrape_result = {'files': []}
            
        except Exception as e:
            print(f"❌ Login failed: {e}")
            return
        finally:
            # Step 4: Clean up browser (happens automatically when context exits)
            print("\n🧹 Step 3: Cleaning up...")
            try:
                if browser:
                    await browser.close()
                    print("✅ Browser closed successfully")
            except Exception as e:
                print(f"⚠️ Warning: Error closing browser: {e}")
    
    # Step 5: Report scraping results and ingest files (outside the Playwright context)
    files = scrape_result.get('files', [])
    print("\n📊 Scraping Results")
    print("=" * 30)
    if files:
        print(f"✅ Successfully scraped {len(files)} files")
        print("\n📁 File Summary:")
        file_types = {}
        for file_info in files:
            file_type = file_info.get('file_type', 'unknown')
            file_types[file_type] = file_types.get(file_type, 0) + 1
        
        for file_type, count in sorted(file_types.items()):
            print(f"   • {file_type}: {count} files")
        
        # Step 6: Ingest the scraped files into backend
        course_json_path = scrape_result.get('course_json_path')
        course_id = scrape_result.get('course_id')
        course_name = scrape_result.get('course_name')
        scrape_batch_id = scrape_result.get('scrape_batch_id')
        
        if course_json_path and os.path.exists(course_json_path):
            print("\n🚀 Ingesting scraped files into backend...")
            try:
                uploaded, duplicate, failed, missing = ingest_course_json(
                    course_json_path,
                    backend_url="http://localhost:8000",
                    course_id_override=course_id,
                    course_name_override=course_name,
                    scrape_batch_id=scrape_batch_id
                )
                print(f"\n📈 Ingestion Complete:")
                print(f"   ✅ Uploaded: {uploaded}")
                print(f"   ⏭️ Duplicates: {duplicate}")
                print(f"   ❌ Failed: {failed}")
                print(f"   ⚠️ Missing: {missing}")
            except Exception as e:
                print(f"❌ Ingestion failed: {e}")
        else:
            print(f"⚠️ Course metadata file not found: {course_json_path}")
    else:
        print("❌ No files were scraped")
    
    print(f"\n🎯 Total files scraped: {len(files)}")
    print("✅ Integration complete!")


if __name__ == "__main__":
    try:
        # Run the async main function
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n❌ Script interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)
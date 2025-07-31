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

# Add the current directory to Python path to ensure imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the login function (now async Playwright)
from playwright_scraper_runner import login_and_get_session

# Import the scraping function (async Playwright)
from lms_scraper.scrape_onq_files import scrape_onq_files_with_authentication


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
    
    # Step 2: Perform async login
    print("\n🚀 Step 1: Logging into OnQ...")
    browser = None
    try:
        browser, context, page = await login_and_get_session(username, password)
        print("✅ Login successful! OnQ dashboard loaded.")
        print(f"📍 Current URL: {page.url}")
    except Exception as e:
        print(f"❌ Login failed: {e}")
        return
    
    # Step 3: Run async scraping
    print("\n🗂️ Step 2: Starting file scraping...")
    files = []
    try:
        import datetime
        scrape_batch_id = datetime.datetime.now().strftime('batch_%Y%m%d-%H%M%S')
        print(f"📋 Scrape batch ID: {scrape_batch_id}")
        
        files = await scrape_onq_files_with_authentication(
            browser, 
            context, 
            page, 
            scrape_batch_id
        )
    except Exception as e:
        print(f"❌ Scraping failed: {e}")
    finally:
        # Step 4: Clean up browser
        print("\n🧹 Step 3: Cleaning up...")
        try:
            if browser:
                await browser.close()
                print("✅ Browser closed successfully")
        except Exception as e:
            print(f"⚠️ Warning: Error closing browser: {e}")
    
    # Step 5: Report results
    print("\n📊 Final Results")
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
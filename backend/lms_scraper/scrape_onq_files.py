import asyncio
import json
import os
import re
from typing import List, Dict, Optional, Tuple
from playwright.async_api import async_playwright, Page
import tempfile
import zipfile
import argparse
import datetime
import shutil
import sys

# Set the correct browser path for Windows
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "C:\\Users\\colin\\AppData\\Local\\ms-playwright"

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to be safe for filesystem."""
    # Remove or replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Remove leading/trailing spaces and dots
    filename = filename.strip('. ')
    
    # Limit length
    if len(filename) > 200:
        filename = filename[:200]
    
    return filename

def get_file_type(filename: str) -> str:
    """Get file type based on filename extension."""
    ext = os.path.splitext(filename)[1].lower()
    if ext == '.pdf':
        return 'pdf'
    elif ext == '.html':
        return 'html'
    elif ext in ['.doc', '.docx']:
        return 'word'
    elif ext in ['.ppt', '.pptx']:
        return 'powerpoint'
    elif ext in ['.xls', '.xlsx']:
        return 'excel'
    elif ext in ['.txt']:
        return 'text'
    elif ext in ['.zip', '.rar']:
        return 'compressed'
    else:
        return ext.lstrip('.') or 'other'

def parse_scraper_args():
    parser = argparse.ArgumentParser(description="LMS Scraper with duplicate handling.")
    parser.add_argument('--rename-duplicates', action='store_true', help='Rename ZIPs and files if duplicates exist (default)')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite ZIPs and files if duplicates exist')
    parser.add_argument('--skip-duplicates', action='store_true', help='Skip ZIPs and files if duplicates exist')
    return parser.parse_args()

def get_unique_filename(path, strategy='rename'):
    """Return a unique filename based on the strategy: rename, overwrite, or skip."""
    if not os.path.exists(path):
        return path, None
    if strategy == 'overwrite':
        return path, 'overwrite'
    elif strategy == 'skip':
        return None, 'skip'
    else:  # rename
        base, ext = os.path.splitext(path)
        import datetime
        timestamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        new_path = f"{base}_{timestamp}{ext}"
        return new_path, 'rename'

class OnQFileScraper:
    def __init__(self, page: Page, course_id: str = "1006419"):
        self.page = page
        self.course_id = course_id
        self.base_url = "https://onq.queensu.ca"
        
    async def validate_session(self) -> bool:
        """Check if the session is still valid by trying to access the home page."""
        try:
            await self.page.goto(f"{self.base_url}/d2l/home")
            await self.page.wait_for_load_state("networkidle")
            
            # Check if we're redirected to login page
            if "login.microsoftonline.com" in self.page.url or "signin" in self.page.url.lower():
                print("ERROR: Session expired - redirected to login page")
                print("💡 Delete onq_state.json to re-authenticate")
                return False
                
            print("SUCCESS: Session is valid")
            return True
        except Exception as e:
            print(f"ERROR: Error validating session: {e}")
            return False
    
    async def navigate_to_course_content(self) -> bool:
        """Navigate to the course content page."""
        try:
            print(f"📚 Navigating to course content for course ID: {self.course_id}")
            
            # Go directly to the course content page
            content_url = f"{self.base_url}/d2l/le/content/{self.course_id}/Home"
            await self.page.goto(content_url)
            await self.page.wait_for_load_state("networkidle")
            
            # Wait for content to load
            await self.page.wait_for_selector('a.d2l-link[href*="/viewContent/"]', timeout=10000)
            print("SUCCESS: Successfully navigated to course content")
            return True
            
        except Exception as e:
            print(f"ERROR: Error navigating to course content: {e}")
            return False
    
    async def scrape_course_files(self, course_name: str = "Unknown Course", scrape_batch_id: str = None) -> List[Dict]:
        """Main method to scrape all course files using Table of Contents ZIP method."""
        try:
            print(f"STARTING: Starting course file scraping for: {course_name}")
            
            # Validate session first
            if not await self.validate_session():
                raise Exception("Session is not valid")
            
            # Navigate to course content
            if not await self.navigate_to_course_content():
                raise Exception("Failed to navigate to course content")
            
            # Go to Table of Contents tab
            try:
                toc_selectors = [
                    'div#TreeItemTOC.d2l-placeholder',
                    'text=Table of Contents'
                ]
                toc_clicked = False
                for selector in toc_selectors:
                    try:
                        toc = await self.page.query_selector(selector)
                        if toc:
                            await toc.click()
                            toc_clicked = True
                            print(f"Clicked Table of Contents tab using selector: {selector}")
                            await self.page.wait_for_load_state('networkidle')
                            break
                    except Exception:
                        continue
                if not toc_clicked:
                    print("ERROR: Could not find Table of Contents tab. Make sure you are on the Content page.")
                    return []
                
                # Wait for overlays to disappear
                try:
                    await self.page.wait_for_selector('.d2l-partial-render-shimbg1', state='detached', timeout=10000)
                except Exception:
                    pass  # If overlay not found, continue
                await asyncio.sleep(0.5)  # Small extra delay
            except Exception as e:
                print(f"ERROR: Error navigating to Table of Contents: {e}")
                return []
            
            # Wait for Download button and handle DOM detachment issues
            try:
                print("Waiting for Download button...")
                # Wait for the button to be available
                await self.page.wait_for_selector('button.d2l-button:has-text("Download")', timeout=10000)
                
                # Small delay to ensure page is stable
                await asyncio.sleep(1)
                
                # Re-query the button right before clicking to avoid DOM detachment
                download_btn = await self.page.query_selector('button.d2l-button:has-text("Download")')
                if not download_btn:
                    print("ERROR: Could not find Download button. Make sure you are on the Table of Contents page.")
                    return []
                
                # Check if button is still attached and visible
                if not await download_btn.is_visible():
                    print("ERROR: Download button is not visible. Trying alternative approach...")
                    # Try clicking by selector instead of element handle
                    async with self.page.expect_download(timeout=30000) as download_info:
                        await self.page.click('button.d2l-button:has-text("Download")')
                    download = await download_info.value
                else:
                    # Use the element handle
                    async with self.page.expect_download(timeout=30000) as download_info:
                        await download_btn.click()
                    download = await download_info.value
                
                downloads_dir = os.path.abspath('downloads')
                os.makedirs(downloads_dir, exist_ok=True)
                zip_path_raw = os.path.join(downloads_dir, sanitize_filename(download.suggested_filename))
                zip_path, zip_action = get_unique_filename(zip_path_raw, 'rename')
                if zip_path is None:
                    print(f"SKIPPED: Skipped ZIP (duplicate exists): {zip_path_raw}")
                    return []
                if zip_action == 'rename':
                    print(f"📝 Renamed ZIP to avoid duplicate: {zip_path}")
                elif zip_action == 'overwrite':
                    print(f"WARNING: Overwriting existing ZIP: {zip_path}")
                await download.save_as(zip_path)
                print(f"Saved ZIP to: {zip_path}")
                
            except Exception as e:
                print(f"ERROR: Failed to download ZIP: {e}")
                print("🔄 Trying alternative download method...")
                try:
                    # Alternative: try clicking by selector directly
                    async with self.page.expect_download(timeout=30000) as download_info:
                        await self.page.click('button.d2l-button:has-text("Download")')
                    download = await download_info.value
                    downloads_dir = os.path.abspath('downloads')
                    os.makedirs(downloads_dir, exist_ok=True)
                    zip_path = os.path.join(downloads_dir, sanitize_filename(download.suggested_filename))
                    await download.save_as(zip_path)
                    print(f"SUCCESS: Saved ZIP to: {zip_path}")
                except Exception as e2:
                    print(f"ERROR: Alternative download method also failed: {e2}")
                    return []
            
            # Extract and parse ZIP
            with tempfile.TemporaryDirectory() as extract_dir:
                try:
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall(extract_dir)
                    file_list = []
                    extracted_renamed, extracted_skipped, extracted_overwritten = 0, 0, 0
                    for root, _, files in os.walk(extract_dir):
                        for fname in files:
                            rel_path = os.path.relpath(os.path.join(root, fname), extract_dir)
                            out_path_raw = os.path.join(downloads_dir, rel_path)
                            out_dir = os.path.dirname(out_path_raw)
                            if not os.path.exists(out_dir):
                                os.makedirs(out_dir, exist_ok=True)
                            out_path, file_action = get_unique_filename(out_path_raw, 'rename')
                            if out_path is None:
                                print(f"SKIPPED: Skipped extracted file (duplicate exists): {out_path_raw}")
                                extracted_skipped += 1
                                continue
                            if file_action == 'rename':
                                print(f"📝 Renamed extracted file to avoid duplicate: {out_path}")
                                extracted_renamed += 1
                            elif file_action == 'overwrite':
                                print(f"WARNING: Overwriting existing file: {out_path}")
                                extracted_overwritten += 1
                            # Actually copy the file, preserving subfolders
                            shutil.copy2(os.path.join(root, fname), out_path)
                    print(f"\n📄 Extraction Summary: Renamed: {extracted_renamed}, Skipped: {extracted_skipped}, Overwritten: {extracted_overwritten}")
                    file_list = []
                    for root, _, files in os.walk(extract_dir):
                        for fname in files:
                            rel_path = os.path.relpath(os.path.join(root, fname), extract_dir)
                            file_list.append({
                                "filename": fname,
                                "path": rel_path.replace("/", "\\"),
                                "file_type": get_file_type(fname),
                                "source": "zip_download",
                                "scrape_batch_id": scrape_batch_id
                            })
                    print(f"Found {len(file_list)} files in ZIP.")
                    
                    # Create course-specific output filename
                    safe_course_name = sanitize_filename(course_name)
                    output_path = os.path.join(downloads_dir, f'course_files_from_zip_{self.course_id}_{safe_course_name}.json')
                    with open(output_path, 'w', encoding='utf-8') as f:
                        json.dump(file_list, f, ensure_ascii=False, indent=2)
                    print(f"SUCCESS: Saved file metadata to {output_path}")
                    return file_list
                except Exception as e:
                    print(f"ERROR: Failed to extract or parse ZIP: {e}")
                    return []
        except Exception as e:
            print(f"ERROR: Error during scraping: {e}")
            return []

async def scrape_course_files(page: Page, course_id: str = "1006419", course_name: str = "Unknown Course", scrape_batch_id: str = None) -> List[Dict]:
    """Convenience function to scrape course files from an authenticated page."""
    scraper = OnQFileScraper(page, course_id)
    return await scraper.scrape_course_files(course_name, scrape_batch_id=scrape_batch_id)

async def wait_for_dashboard_ready(page: Page) -> bool:
    """Wait for dashboard to be fully loaded and ready."""
    print("🔄 Checking dashboard status...")
    
    try:
        # Navigate to dashboard if not already there
        current_url = page.url
        if "d2l/home" not in current_url:
            await page.goto("https://onq.queensu.ca/d2l/home")
            await page.wait_for_load_state("networkidle")
        
        # Wait for page to be fully loaded
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_load_state("networkidle")
        
        # Check if we're still on login page (session expired)
        if "login.microsoftonline.com" in page.url or "signin" in page.url.lower():
            print("ERROR: Session expired - redirected to login page")
            return False
        
        # Now check if dashboard is ready
        print("🔍 Checking if dashboard is ready...")
        
        # Wait a moment for any final loading
        await asyncio.sleep(2)
        
        # Try to detect if courses are present
        course_selectors = [
            '[class*="course"]',
            '[class*="d2l-course"]',
            'a[href*="/d2l/le/"]',
            '[class*="card"]',
            '[class*="tile"]'
        ]
        
        courses_found = False
        for selector in course_selectors:
            try:
                elements = await page.locator(selector).all()
                if len(elements) > 0:
                    print(f"SUCCESS: Found {len(elements)} elements with '{selector}'")
                    courses_found = True
                    break
            except:
                continue
        
        if courses_found:
            print("SUCCESS: Dashboard appears to be ready!")
            return True
        else:
            print("WARNING: No course elements found on dashboard")
            print("This might mean:")
            print("  - Dashboard is still loading")
            print("  - You're not enrolled in any courses")
            print("  - Page layout is different")
            return False
            
    except Exception as e:
        print(f"ERROR: Error checking dashboard: {e}")
        return False

async def extract_course_links(page: Page) -> List[Tuple[str, str]]:
    """Extract all course links from the OnQ dashboard."""
    courses = []
    try:
        print("🔍 Scanning dashboard for course links...")
        
        # Wait for dashboard to be fully ready first
        if not await wait_for_dashboard_ready(page):
            print("ERROR: Dashboard not ready, cannot extract courses")
            return []
        
        # Now extract courses (dashboard should be ready)
        print("🔍 Extracting course links...")
        
        # Debug: Let's see what's actually on the page (only if no courses found)
        debug_enabled = True  # Set to True for debugging
        
        if debug_enabled:
            print("🔍 Debug: Checking page content...")
            
            # Try to find course cards by looking for common patterns
            debug_selectors = [
                '[class*="course"]',
                '[class*="d2l-course"]', 
                '[class*="card"]',
                '[class*="tile"]',
                '[class*="widget"]',
                'a[href*="/d2l/le/"]',
            ]
            
            for debug_selector in debug_selectors:
                try:
                    elements = await page.locator(debug_selector).all()
                    print(f"  Debug: Found {len(elements)} elements with '{debug_selector}'")
                    for i, elem in enumerate(elements[:3]):  # Show first 3
                        try:
                            text = await elem.inner_text()
                            href = await elem.get_attribute('href')
                            classes = await elem.get_attribute('class')
                            print(f"    [{i+1}] Text: '{text[:50]}...' | Href: '{href}' | Classes: '{classes}'")
                        except:
                            print(f"    [{i+1}] Could not get details")
                except Exception as e:
                    print(f"  Debug: Error with '{debug_selector}': {e}")
        
        # Try multiple selector strategies to find course links
        selectors = [
            'a[href*="/d2l/le/content/"]',  # Direct content links
            '[class*="course-card"] a',     # Course card links
            '[class*="d2l-course"] a',      # D2L course links
            '[class*="course"] a',          # General course links
            'a[href*="/d2l/le/"]',          # Any d2l/le links (will be filtered)
        ]
        
        all_links = []
        for selector in selectors:
            try:
                links = await page.locator(selector).all()
                all_links.extend(links)
                print(f"  Found {len(links)} links with selector: {selector}")
            except Exception as e:
                print(f"  WARNING: Error with selector '{selector}': {e}")
                continue
        
        # Remove duplicates while preserving order
        seen_hrefs = set()
        unique_links = []
        for link in all_links:
            try:
                href = await link.get_attribute('href')
                if href and href not in seen_hrefs:
                    seen_hrefs.add(href)
                    unique_links.append(link)
            except:
                continue
        
        print(f"  Total unique links found: {len(unique_links)}")
        
        for link in unique_links:
            try:
                href = await link.get_attribute('href')
                if not href:
                    continue
                
                print(f"  🔗 Processing link: {href}")
                
                # Filter out non-course links
                exclude_patterns = [
                    r'/d2l/le/userprogress/',      # Progress pages
                    r'/d2l/le/news/',              # News pages
                    r'/d2l/le/calendar/',          # Calendar pages
                    r'/d2l/le/manageCourses/',     # Course management
                    r'/d2l/le/discovery/',         # Discovery pages
                    r'/d2l/le/email/',             # Email pages
                    r'/d2l/le/discussions/',       # Discussion pages
                    r'/d2l/le/dropbox/',           # Dropbox pages
                    r'/d2l/le/quizzes/',           # Quiz pages
                    r'/d2l/le/grades/',            # Grade pages
                    r'/d2l/le/assignments/',       # Assignment pages
                    r'/d2l/le/checklist/',         # Checklist pages
                    r'/d2l/le/surveys/',           # Survey pages
                    r'/d2l/le/selfassessments/',   # Self-assessment pages
                    r'/d2l/le/competencies/',      # Competency pages
                    r'/d2l/le/rubrics/',           # Rubric pages
                    r'/d2l/le/outcomes/',          # Outcome pages
                    r'/d2l/le/attendance/',        # Attendance pages
                    r'/d2l/le/group/',             # Group pages
                    r'/d2l/le/classlist/',         # Classlist pages
                    r'/d2l/le/content/.*?/View',   # Content view pages (not content home)
                ]
                
                # Check if this link should be excluded
                should_exclude = False
                for pattern in exclude_patterns:
                    if re.search(pattern, href):
                        print(f"    ERROR: Excluded (matches pattern: {pattern})")
                        should_exclude = True
                        break
                
                if should_exclude:
                    continue
                
                # Extract course ID from URL - handle both home and content URLs
                course_id = None
                patterns = [
                    r'/d2l/home/(\d+)',             # Course home page (found in debug)
                    r'/d2l/le/content/(\d+)/Home',  # Content home page (preferred)
                    r'/d2l/le/content/(\d+)/',      # Any content URL
                    r'/d2l/le/(\d+)/',              # General d2l/le URL (fallback)
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, href)
                    if match:
                        course_id = match.group(1)
                        print(f"    SUCCESS: Found course ID: {course_id}")
                        break
                
                if not course_id:
                    print(f"    WARNING: Could not extract course ID from: {href}")
                    continue
                
                # Extract course name from link text or nearby elements
                course_name = await link.inner_text()
                
                # If link text is empty or too short, try to find course name in parent elements
                if not course_name or len(course_name.strip()) < 3:
                    try:
                        # Look for course name in parent elements
                        parent_selectors = [
                            'xpath=ancestor::div[contains(@class, "course")]',
                            'xpath=ancestor::div[contains(@class, "d2l")]',
                            'xpath=ancestor::div[contains(@class, "card")]',
                            'xpath=ancestor::div[contains(@class, "title")]',
                            'xpath=ancestor::div[contains(@class, "name")]',
                        ]
                        
                        for parent_selector in parent_selectors:
                            try:
                                parent = await link.locator(parent_selector).first
                                if await parent.count():
                                    parent_text = await parent.inner_text()
                                    if parent_text and len(parent_text.strip()) > 3:
                                        course_name = parent_text.strip()
                                        print(f"    📝 Found course name in parent: {course_name}")
                                        break
                            except:
                                continue
                    except Exception as e:
                        print(f"    WARNING: Error finding parent text: {e}")
                
                # Clean up course name
                if course_name:
                    course_name = course_name.strip()
                    # Remove extra whitespace and newlines
                    course_name = re.sub(r'\s+', ' ', course_name)
                    # Limit length
                    if len(course_name) > 100:
                        course_name = course_name[:100] + "..."
                else:
                    course_name = f"Course {course_id}"
                
                # Avoid duplicates
                if not any(cid == course_id for _, cid in courses):
                    courses.append((course_name, course_id))
                    print(f"    📚 Added course: {course_name} (ID: {course_id})")
                else:
                    print(f"    WARNING: Duplicate course ID: {course_id}")
                
            except Exception as e:
                print(f"  WARNING: Error processing link: {e}")
                continue
        
        print(f"SUCCESS: Found {len(courses)} unique courses on dashboard")
        return courses
        
    except Exception as e:
        print(f"ERROR: Error extracting course links: {e}")
        return []

def manual_course_input() -> Tuple[str, str]:
    """Allow manual input of course details when automatic detection fails."""
    print("\n🔧 Manual course input mode")
    print("If automatic course detection failed, you can manually enter course details.")
    
    while True:
        try:
            course_id = input("Enter course ID (e.g., 1006419): ").strip()
            if course_id and course_id.isdigit():
                break
            else:
                print("ERROR: Please enter a valid numeric course ID")
        except KeyboardInterrupt:
            print("\nERROR: Manual input cancelled")
            return None, None
    
    course_name = input("Enter course name (optional, press Enter to skip): ").strip()
    if not course_name:
        course_name = f"Course {course_id}"
    
    return course_name, course_id

def display_course_selection(courses: List[Tuple[str, str]]) -> int:
    """Display courses to user and get their selection."""
    if not courses:
        print("ERROR: No courses found on dashboard")
        return -1
    
    print("\nLIST: Courses found:")
    for i, (name, course_id) in enumerate(courses, 1):
        print(f"[{i}] {name} (ID: {course_id})")
    
    while True:
        try:
            selection = input(f"\nEnter the number of the course to scrape (1-{len(courses)}): ").strip()
            course_index = int(selection) - 1
            
            if 0 <= course_index < len(courses):
                selected_course = courses[course_index]
                print(f"SUCCESS: Selected: {selected_course[0]} (ID: {selected_course[1]})")
                return course_index
            else:
                print(f"ERROR: Please enter a number between 1 and {len(courses)}")
        except ValueError:
            print("ERROR: Please enter a valid number")
        except KeyboardInterrupt:
            print("\nERROR: Selection cancelled")
            return -1

async def scrape_onq_files_with_authentication(browser, context, page, scrape_batch_id: str = None) -> Dict:
    """
    Main scraping function that accepts authenticated browser, context, and page objects.
    Assumes starting from OnQ dashboard (already logged in).
    
    Returns:
        Dict with keys:
        - 'files': List of file dictionaries
        - 'course_id': Selected course ID
        - 'course_name': Selected course name
        - 'course_json_path': Path to the course metadata JSON file
        - 'scrape_batch_id': The batch ID used for scraping
    """
    try:
        if scrape_batch_id is None:
            scrape_batch_id = datetime.datetime.now().strftime('batch_%Y%m%d-%H%M%S')
        
        print(f"STARTING: Starting OnQ file scraping (batch: {scrape_batch_id})")
        
        # Extract course links from the dashboard
        courses = await extract_course_links(page)
        
        # Handle case when no courses are found automatically
        if not courses:
            print("\nWARNING: No courses found automatically.")
            print("This could be due to:")
            print("  - Dashboard still loading")
            print("  - Different page layout")
            print("  - Session expired")
            
            # Offer manual input option
            use_manual = input("\nWould you like to manually enter course details? (y/n): ").strip().lower()
            if use_manual in ['y', 'yes']:
                course_name, course_id = manual_course_input()
                if course_name and course_id:
                    courses = [(course_name, course_id)]
                    selected_course_index = 0
                else:
                    print("ERROR: Manual input cancelled")
                    return {'files': [], 'course_id': None, 'course_name': None, 'course_json_path': None, 'scrape_batch_id': scrape_batch_id}
            else:
                print("ERROR: No course selected")
                return {'files': [], 'course_id': None, 'course_name': None, 'course_json_path': None, 'scrape_batch_id': scrape_batch_id}
        else:
            # Display course selection
            selected_course_index = display_course_selection(courses)
        
        if selected_course_index != -1:
            # Get the selected course details
            selected_course_name, selected_course_id = courses[selected_course_index]
            print(f"\nSTARTING: Starting scraping for: {selected_course_name} (ID: {selected_course_id})")
            
            # First navigate to the course home page
            course_home_url = f"https://onq.queensu.ca/d2l/home/{selected_course_id}"
            print(f"📚 Navigating to course home: {course_home_url}")
            await page.goto(course_home_url)
            await page.wait_for_load_state("networkidle")
            
            # Now try to navigate to the content page from within the course
            try:
                print("🔍 Looking for Content link in course navigation...")
                # Wait for course navigation to load
                await page.wait_for_selector('a[href*="content"], [class*="content"], [class*="nav"]', timeout=10000)
                
                # Try to find and click the Content link
                content_selectors = [
                    'a[href*="/content/"]',
                    'a:has-text("Content")',
                    '[class*="content"] a',
                    '[class*="nav"] a:has-text("Content")',
                    'a[title*="Content"]',
                    'a[aria-label*="Content"]'
                ]
                
                content_clicked = False
                for selector in content_selectors:
                    try:
                        content_link = await page.query_selector(selector)
                        if content_link and await content_link.is_visible():
                            print(f"SUCCESS: Found Content link with selector: {selector}")
                            await content_link.click()
                            await page.wait_for_load_state("networkidle")
                            content_clicked = True
                            break
                    except Exception as e:
                        print(f"  WARNING: Selector '{selector}' failed: {e}")
                        continue
                
                if not content_clicked:
                    print("WARNING: Could not find Content link, trying direct navigation...")
                    # Fallback: try direct navigation to content page
                    content_url = f"https://onq.queensu.ca/d2l/le/content/{selected_course_id}/Home"
                    await page.goto(content_url)
                    await page.wait_for_load_state("networkidle")
                    
            except Exception as e:
                print(f"WARNING: Error navigating to content: {e}")
                # Try direct navigation as fallback
                content_url = f"https://onq.queensu.ca/d2l/le/content/{selected_course_id}/Home"
                print(f"🔄 Trying direct navigation to: {content_url}")
                await page.goto(content_url)
                await page.wait_for_load_state("networkidle")
            
            # Scrape the files from the selected course
            files = await scrape_course_files(page, selected_course_id, selected_course_name, scrape_batch_id=scrape_batch_id)
            
            # Print results
            print("\nLIST: Scraped Files:")
            for i, file_info in enumerate(files, 1):
                print(f"\n{i}. {file_info['filename']}")
                print(f"   Path: {file_info['path']}")
                print(f"   Type: {file_info['file_type']}")
                print(f"   Source: {file_info['source']}")
            
            # Show download summary
            print("\nFILES: Downloaded files to 'downloads/' folder:")
            for file_info in files:
                print(f"   * {file_info['filename']} ({file_info['file_type']})")
            
            # Construct the course JSON path
            safe_course_name = sanitize_filename(selected_course_name)
            course_json_path = os.path.join("downloads", f'course_files_from_zip_{selected_course_id}_{safe_course_name}.json')
            
            return {
                'files': files,
                'course_id': selected_course_id,
                'course_name': selected_course_name,
                'course_json_path': course_json_path,
                'scrape_batch_id': scrape_batch_id
            }
        else:
            print("No course selected or selected course not found.")
            return {'files': [], 'course_id': None, 'course_name': None, 'course_json_path': None, 'scrape_batch_id': scrape_batch_id}
        
    except Exception as e:
        print(f"ERROR: Error during scraping: {e}")
        return {'files': [], 'course_id': None, 'course_name': None, 'course_json_path': None, 'scrape_batch_id': scrape_batch_id}


async def main():
    """Legacy main function for standalone testing (will be removed in production)."""
    args = parse_scraper_args()
    duplicate_strategy = 'rename'
    if args.overwrite:
        duplicate_strategy = 'overwrite'
    elif args.skip_duplicates:
        duplicate_strategy = 'skip'
    
    # Generate a scrape_batch_id for this run
    scrape_batch_id = datetime.datetime.now().strftime('batch_%Y%m%d-%H%M%S')
    print(f"[Scraper] Using scrape_batch_id: {scrape_batch_id}")
    
    """Legacy standalone testing function."""
    async with async_playwright() as p:
        try:
            # Launch browser
            browser = await p.chromium.launch(headless=False)  # Set to True for production

            # Use saved session if available
            if os.path.exists("onq_state.json"):
                context = await browser.new_context(storage_state="onq_state.json")
                page = await context.new_page()
                print("SUCCESS: Loaded existing OnQ session.")
            else:
                context = await browser.new_context()
                page = await context.new_page()
                print("*** Please log in manually to OnQ...")
                print("1. Navigate to https://onq.queensu.ca/")
                print("2. Complete the login and 2FA process")
                print("3. Wait for the page to load completely")
                print("4. Press Enter in this terminal when ready...")
                
                input("Press Enter when you're logged in...")
                await context.storage_state(path="onq_state.json")
                print("SUCCESS: Session saved to onq_state.json.")
            
            # Use the new integrated function
            scrape_result = await scrape_onq_files_with_authentication(browser, context, page, scrape_batch_id)
            files = scrape_result.get('files', [])
            
            if files:
                print(f"\nSUCCESS: Successfully scraped {len(files)} files")
            else:
                print("\nERROR: No files were scraped")
            
        except Exception as e:
            print(f"ERROR: Error in main: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main()) 
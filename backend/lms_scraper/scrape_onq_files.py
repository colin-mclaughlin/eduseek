import asyncio
import json
import time
import os
import re
from typing import List, Dict, Optional
from playwright.async_api import async_playwright, Page, Browser
import tempfile
import zipfile

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

def get_file_extension(file_type: str, title: str) -> str:
    """Get appropriate file extension based on file type and title."""
    # Check file type first
    if "PDF" in file_type:
        return ".pdf"
    elif "Word" in file_type:
        return ".docx"
    elif "PowerPoint" in file_type:
        return ".pptx"
    elif "Excel" in file_type:
        return ".xlsx"
    elif "Text" in file_type:
        return ".txt"
    elif "Compressed" in file_type:
        return ".zip"
    
    # Fallback: check title for common extensions
    title_lower = title.lower()
    if title_lower.endswith('.pdf'):
        return ".pdf"
    elif title_lower.endswith('.doc') or title_lower.endswith('.docx'):
        return ".docx"
    elif title_lower.endswith('.ppt') or title_lower.endswith('.pptx'):
        return ".pptx"
    elif title_lower.endswith('.xls') or title_lower.endswith('.xlsx'):
        return ".xlsx"
    elif title_lower.endswith('.txt'):
        return ".txt"
    elif title_lower.endswith('.zip') or title_lower.endswith('.rar'):
        return ".zip"
    
    # Default to PDF if no clear indication
    return ".pdf"

class OnQFileScraper:
    def __init__(self, page: Page):
        self.page = page
        self.course_id = "1006419"  # Hardcoded for now, can be made configurable
        self.base_url = "https://onq.queensu.ca"
        self.files = []
        
    async def validate_session(self) -> bool:
        """Check if the session is still valid by trying to access the home page."""
        try:
            await self.page.goto(f"{self.base_url}/d2l/home")
            await self.page.wait_for_load_state("networkidle")
            
            # Check if we're redirected to login page
            if "login.microsoftonline.com" in self.page.url or "signin" in self.page.url.lower():
                print("❌ Session expired - redirected to login page")
                print("💡 Delete onq_state.json to re-authenticate")
                return False
                
            print("✅ Session is valid")
            return True
        except Exception as e:
            print(f"❌ Error validating session: {e}")
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
            print("✅ Successfully navigated to course content")
            return True
            
        except Exception as e:
            print(f"❌ Error navigating to course content: {e}")
            return False
    
    async def expand_all_modules(self):
        """Expand all collapsed modules to reveal their content."""
        try:
            print("🔽 Expanding all collapsed modules...")
            
            # Look for expand/collapse buttons
            expand_buttons = await self.page.locator('[aria-label*="Expand"], [aria-label*="expand"], .d2l-expand-collapse-button').all()
            
            for button in expand_buttons:
                try:
                    # Check if the button is for expanding (not collapsing)
                    aria_label = await button.get_attribute('aria-label') or ''
                    if 'expand' in aria_label.lower() or 'collapsed' in aria_label.lower():
                        await button.click()
                        await asyncio.sleep(0.5)  # Small delay to let content load
                        print(f"  ✅ Expanded module: {aria_label}")
                except Exception as e:
                    print(f"  ⚠️ Could not expand module: {e}")
                    continue
            
            # Wait a bit for all content to load
            await asyncio.sleep(2)
            print("✅ Module expansion complete")
            
        except Exception as e:
            print(f"⚠️ Error expanding modules: {e}")
    
    async def extract_file_links(self) -> List[Dict]:
        """Extract all file links from the content page."""
        files = []
        
        try:
            print("📄 Extracting file links from content...")
            
            # Wait for at least one preview link to appear
            await self.page.wait_for_selector('a.d2l-link[href*="/viewContent/"]', timeout=10000)
            
            # Select all file links directly
            file_links = await self.page.locator('a.d2l-link[href*="/viewContent/"]').all()
            
            print(f"🔍 Found {len(file_links)} file links to process...")
            
            for i, link in enumerate(file_links, 1):
                try:
                    # Extract title
                    title = await link.inner_text()
                    if not title or not title.strip():
                        title = "Unknown Title"
                    title = title.strip()
                    
                    # Extract preview URL
                    preview_url = await link.get_attribute("href")
                    if not preview_url:
                        print(f"  ⚠️ Skipping file {i}: No href attribute")
                        continue
                    
                    # Debug: Check for any "Viiew" typo in the original URL
                    if "Viiew" in preview_url:
                        print(f"  ⚠️ WARNING: Found 'Viiew' typo in original URL: {preview_url}")
                    
                    # Make URL absolute if it's relative
                    if preview_url.startswith('/'):
                        preview_url = f"{self.base_url}{preview_url}"
                    
                    # Debug: Check for any "Viiew" typo in the final URL
                    if "Viiew" in preview_url:
                        print(f"  ⚠️ WARNING: Found 'Viiew' typo in final URL: {preview_url}")
                        # Fix the typo - Brightspace URLs are case-sensitive
                        preview_url = preview_url.replace("Viiew", "View")
                        print(f"  🔧 Fixed URL: {preview_url}")
                    
                    # Infer file type from URL extension
                    file_type = "Unknown"
                    if '.' in preview_url:
                        extension = preview_url.split('.')[-1].lower()
                        if extension in ['pdf']:
                            file_type = "PDF document"
                        elif extension in ['doc', 'docx']:
                            file_type = "Word document"
                        elif extension in ['ppt', 'pptx']:
                            file_type = "PowerPoint presentation"
                        elif extension in ['xls', 'xlsx']:
                            file_type = "Excel spreadsheet"
                        elif extension in ['txt']:
                            file_type = "Text document"
                        elif extension in ['zip', 'rar']:
                            file_type = "Compressed file"
                        else:
                            file_type = f"{extension.upper()} file"
                    
                    # Try to get module/section heading (optional)
                    module_heading = "Unknown Module"
                    try:
                        # Look for the closest parent section
                        parent_section = await link.locator('xpath=ancestor::div[contains(@class, "d2l-module") or contains(@class, "d2l-section") or contains(@class, "d2l-content-item")]').first
                        if await parent_section.count():
                            # Try to find a heading within this section
                            heading_element = await parent_section.locator('h2, h3, .d2l-module-title, .d2l-section-title, [class*="title"]').first
                            if await heading_element.count():
                                module_text = await heading_element.text_content()
                                if module_text and module_text.strip():
                                    module_heading = module_text.strip()
                    except Exception as e:
                        # Module detection is optional, so we don't fail if it doesn't work
                        pass
                    
                    file_info = {
                        "title": title,
                        "type": file_type,
                        "module": module_heading,
                        "preview_url": preview_url,
                        "download_url": None  # Will be filled later
                    }
                    
                    files.append(file_info)
                    print(f"  📄 [{i}/{len(file_links)}] Found: {title} ({file_type}) → {preview_url}")
                    
                except Exception as e:
                    print(f"  ⚠️ Error extracting file {i}: {e}")
                    continue
            
            print(f"✅ Successfully extracted {len(files)} files from content")
            
            # TODO: Visit each preview page to extract actual download links
            print("📋 TODO: Implement download URL extraction for each file")
            
            return files
            
        except Exception as e:
            print(f"❌ Error extracting file links: {e}")
            return files
    
    async def get_download_url(self, preview_url: str, file_title: str = "Unknown", file_type: str = "Unknown") -> Optional[str]:
        """Visit the preview page and extract the download URL by clicking the download button."""
        try:
            print(f"🔗 Getting download URL for: {file_title}")
            
            # Navigate to preview page
            await self.page.goto(preview_url, wait_until="load", timeout=15000)
            await self.page.wait_for_load_state("networkidle")
            
            # Wait for the viewer to load
            await self.page.wait_for_selector('.d2l-fileviewer, .d2l-content-viewer', timeout=10000)
            
            # Scroll down to find download button
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1)
            
            # Try multiple download button selectors
            selectors = [
                'button.d2l-button:has-text("Download")',
                'button:has-text("Download")',
                'a:has-text("Download")',
                '[aria-label*="Download"]',
                '.d2l-download-button',
                '[data-testid="download-button"]',
                'button[title*="Download"]',
            ]
            
            # Try to click download button and capture the download
            for selector in selectors:
                try:
                    print(f"  🎯 Trying selector: {selector}")
                    async with self.page.expect_download(timeout=10000) as download_info:
                        await self.page.locator(selector).click()
                    download = await download_info.value
                    download_url = download.url
                    
                    # Debug: Check for any "Viiew" typo in the download URL
                    if "Viiew" in download_url:
                        print(f"  ⚠️ WARNING: Found 'Viiew' typo in download URL: {download_url}")
                        # Fix the typo - Brightspace URLs are case-sensitive
                        download_url = download_url.replace("Viiew", "View")
                        print(f"  🔧 Fixed download URL: {download_url}")
                    
                    print(f"  ✅ Success: {file_title} → {download_url}")
                    
                    # Save the file to disk
                    try:
                        # Ensure downloads directory exists
                        os.makedirs("downloads", exist_ok=True)
                        
                        # Get appropriate file extension
                        file_extension = get_file_extension(file_type, file_title)
                        
                        # Sanitize filename
                        safe_filename = sanitize_filename(file_title)
                        
                        # Create full file path
                        file_path = f"downloads/{safe_filename}{file_extension}"
                        
                        # Handle duplicate filenames
                        counter = 1
                        original_path = file_path
                        while os.path.exists(file_path):
                            name_without_ext = original_path.rsplit('.', 1)[0]
                            ext = original_path.rsplit('.', 1)[1]
                            file_path = f"{name_without_ext}_{counter}.{ext}"
                            counter += 1
                        
                        # Save the file
                        await download.save_as(file_path)
                        print(f"  💾 Saved file: {file_path}")
                        
                    except Exception as save_error:
                        print(f"  ⚠️ Failed to save file: {save_error}")
                    
                    # Add a small delay to be respectful to the server
                    await asyncio.sleep(1)
                    
                    return download_url
                    
                except Exception as e:
                    print(f"  ⚠️ Failed with selector '{selector}': {e}")
                    continue
            
            print(f"  ❌ Failed to get download URL for: {file_title}")
            return None
            
        except Exception as e:
            print(f"  ❌ Error getting download URL for {file_title}: {e}")
            return None
    
    async def scrape_course_files(self) -> List[Dict]:
        """Main method to scrape all course files."""
        try:
            print("🚀 Starting course file scraping...")
            # Validate session first
            if not await self.validate_session():
                raise Exception("Session is not valid")
            # Navigate to course content
            if not await self.navigate_to_course_content():
                raise Exception("Failed to navigate to course content")
            # --- REPLACE OLD SCRAPING LOGIC BELOW WITH TABLE OF CONTENTS ZIP METHOD ---
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
                    print("❌ Could not find Table of Contents tab. Make sure you are on the Content page.")
                    return []
                # Wait for overlays to disappear
                try:
                    await self.page.wait_for_selector('.d2l-partial-render-shimbg1', state='detached', timeout=10000)
                except Exception:
                    pass  # If overlay not found, continue
                await asyncio.sleep(0.5)  # Small extra delay
            except Exception as e:
                print(f"❌ Error navigating to Table of Contents: {e}")
                return []
            # Wait for Download button
            try:
                print("Waiting for Download button...")
                # Re-query the Download button right before clicking
                download_btn = await self.page.wait_for_selector('button.d2l-button:has-text("Download")', timeout=10000)
            except Exception:
                print("❌ Could not find Download button. Make sure you are on the Table of Contents page.")
                return []
            # Download ZIP
            print("Clicking Download button and waiting for ZIP...")
            try:
                # Re-query the Download button again right before clicking
                download_btn = await self.page.wait_for_selector('button.d2l-button:has-text("Download")', timeout=10000)
                async with self.page.expect_download(timeout=30000) as download_info:
                    await download_btn.click()
                download = await download_info.value
                downloads_dir = os.path.abspath('downloads')
                os.makedirs(downloads_dir, exist_ok=True)
                zip_path = os.path.join(downloads_dir, sanitize_filename(download.suggested_filename))
                await download.save_as(zip_path)
                print(f"Saved ZIP to: {zip_path}")
            except Exception as e:
                print(f"❌ Failed to download ZIP: {e}")
                return []
            # Extract and parse ZIP
            with tempfile.TemporaryDirectory() as extract_dir:
                try:
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall(extract_dir)
                    file_list = []
                    for root, _, files in os.walk(extract_dir):
                        for fname in files:
                            rel_path = os.path.relpath(os.path.join(root, fname), extract_dir)
                            file_list.append({
                                "filename": fname,
                                "path": rel_path,
                                "file_type": get_file_extension('', fname)[1:],
                                "source": "zip_download"
                            })
                    print(f"Found {len(file_list)} files in ZIP.")
                    output_path = os.path.join(downloads_dir, 'course_files_from_zip.json')
                    with open(output_path, 'w', encoding='utf-8') as f:
                        json.dump(file_list, f, indent=2)
                    print(f"✅ Saved file metadata to {output_path}")
                    return file_list
                except Exception as e:
                    print(f"❌ Failed to extract or parse ZIP: {e}")
                    return []
        except Exception as e:
            print(f"❌ Error during scraping: {e}")
            return []

async def scrape_course_files(page: Page) -> List[Dict]:
    """Convenience function to scrape course files from an authenticated page."""
    scraper = OnQFileScraper(page)
    return await scraper.scrape_course_files()

async def main():
    """Main function for local testing."""
    async with async_playwright() as p:
        try:
            # Launch browser
            browser = await p.chromium.launch(headless=False)  # Set to True for production

            # Use saved session if available
            if os.path.exists("onq_state.json"):
                context = await browser.new_context(storage_state="onq_state.json")
                page = await context.new_page()
                print("✅ Loaded existing OnQ session.")
            else:
                context = await browser.new_context()
                page = await context.new_page()
                print("🔐 Please log in manually to OnQ...")
                print("1. Navigate to https://onq.queensu.ca/")
                print("2. Complete the login and 2FA process")
                print("3. Wait for the page to load completely")
                print("4. Press Enter in this terminal when ready...")
                
                input("Press Enter when you're logged in...")
                await context.storage_state(path="onq_state.json")
                print("✅ Session saved to onq_state.json.")
            
            # Scrape the files
            files = await scrape_course_files(page)
            
            # Print results
            print("\n📋 Scraped Files:")
            for i, file_info in enumerate(files, 1):
                print(f"\n{i}. {file_info['filename']}")
                print(f"   Path: {file_info['path']}")
                print(f"   Type: {file_info['file_type']}")
                print(f"   Source: {file_info['source']}")
            # Save to JSON file for inspection
            with open('downloads/course_files_from_zip.json', 'w') as f:
                json.dump(files, f, indent=2)
            print(f"\n💾 Results saved to downloads/course_files_from_zip.json")
            
            # Show download summary
            # (No reference to 'download_url' since ZIP-based metadata does not include it)
            print("\n📁 Downloaded files to 'downloads/' folder:")
            for file_info in files:
                print(f"   • {file_info['filename']} ({file_info['file_type']})")
            
            # TODO: Send file data to backend or trigger ingestion
            print("\n📤 TODO: Implement backend integration")
            
        except Exception as e:
            print(f"❌ Error in main: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main()) 
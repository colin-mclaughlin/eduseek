import asyncio
import json
import time
import os
import re
from typing import List, Dict, Optional
from playwright.async_api import async_playwright, Page, Browser

# Set the correct browser path for Windows
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "C:\\Users\\colin\\AppData\\Local\\ms-playwright"

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
            
            # Wait for content to be fully loaded
            await self.page.wait_for_selector('a.d2l-link[href*="/viewContent/"]', timeout=10000)
            
            # Get all content items
            content_items = await self.page.locator('[data-testid="content-list"] > div').all()
            
            for item in content_items:
                try:
                    # Check if this is a file link
                    file_link = await item.locator('a[href*="viewContent"]').first
                    if not await file_link.count():
                        continue
                    
                    # Extract file information
                    title = await file_link.text_content() or "Unknown Title"
                    title = title.strip()
                    
                    # Get the preview URL
                    preview_url = await file_link.get_attribute('href')
                    if not preview_url:
                        continue
                    
                    # Make URL absolute if it's relative
                    if preview_url.startswith('/'):
                        preview_url = f"{self.base_url}{preview_url}"
                    
                    # Try to get file type from the item
                    file_type_element = await item.locator('.d2l-filetype-icon, [class*="filetype"]').first
                    file_type = "Unknown"
                    if await file_type_element.count():
                        file_type_text = await file_type_element.get_attribute('title') or await file_type_element.text_content()
                        if file_type_text:
                            file_type = file_type_text.strip()
                    
                    # Try to get module/section heading
                    module_heading = "Unknown Module"
                    parent_section = await item.locator('xpath=ancestor::div[contains(@class, "d2l-module") or contains(@class, "d2l-section")]').first
                    if await parent_section.count():
                        heading_element = await parent_section.locator('h2, h3, .d2l-module-title, .d2l-section-title').first
                        if await heading_element.count():
                            module_heading = await heading_element.text_content() or "Unknown Module"
                            module_heading = module_heading.strip()
                    
                    file_info = {
                        "title": title,
                        "type": file_type,
                        "module": module_heading,
                        "preview_url": preview_url,
                        "download_url": None  # Will be filled later
                    }
                    
                    files.append(file_info)
                    print(f"  📄 Found file: {title} ({file_type}) in {module_heading}")
                    
                except Exception as e:
                    print(f"  ⚠️ Error extracting file info: {e}")
                    continue
            
            print(f"✅ Extracted {len(files)} files from content")
            return files
            
        except Exception as e:
            print(f"❌ Error extracting file links: {e}")
            return files
    
    async def get_download_url(self, preview_url: str) -> Optional[str]:
        """Visit the preview page and extract the download URL."""
        try:
            print(f"🔗 Getting download URL for: {preview_url}")
            
            # Navigate to preview page
            await self.page.goto(preview_url)
            await self.page.wait_for_load_state("networkidle")
            
            # Wait for the viewer to load
            await self.page.wait_for_selector('.d2l-fileviewer, .d2l-content-viewer', timeout=10000)
            
            # Scroll down to find download button
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1)
            
            # Look for download button with various selectors
            download_selectors = [
                'a[href*="/content/enforced/"]',
                'a[href*="download"]',
                'button[aria-label*="Download"]',
                'a[aria-label*="Download"]',
                '.d2l-download-button',
                '[data-testid="download-button"]'
            ]
            
            download_url = None
            for selector in download_selectors:
                try:
                    download_element = await self.page.locator(selector).first
                    if await download_element.count():
                        download_url = await download_element.get_attribute('href')
                        if download_url:
                            # Make URL absolute if it's relative
                            if download_url.startswith('/'):
                                download_url = f"{self.base_url}{download_url}"
                            print(f"  ✅ Found download URL: {download_url}")
                            break
                except:
                    continue
            
            if not download_url:
                print(f"  ⚠️ No download URL found for: {preview_url}")
            
            # Add a small delay to be respectful to the server
            await asyncio.sleep(0.5)
            
            return download_url
            
        except Exception as e:
            print(f"  ❌ Error getting download URL: {e}")
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
            
            # Expand all modules
            await self.expand_all_modules()
            
            # Extract file links
            files = await self.extract_file_links()
            
            if not files:
                print("⚠️ No files found in course content")
                return []
            
            # Get download URLs for each file
            print(f"📥 Getting download URLs for {len(files)} files...")
            for i, file_info in enumerate(files):
                print(f"  [{i+1}/{len(files)}] Processing: {file_info['title']}")
                
                download_url = await self.get_download_url(file_info['preview_url'])
                file_info['download_url'] = download_url
                
                # Add to our files list
                self.files.append(file_info)
            
            print(f"✅ Scraping complete! Found {len(self.files)} files")
            return self.files
            
        except Exception as e:
            print(f"❌ Error during scraping: {e}")
            return self.files

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
                print(f"\n{i}. {file_info['title']}")
                print(f"   Type: {file_info['type']}")
                print(f"   Module: {file_info['module']}")
                print(f"   Preview: {file_info['preview_url']}")
                print(f"   Download: {file_info['download_url']}")
            
            # Save to JSON file for inspection
            with open('scraped_files.json', 'w') as f:
                json.dump(files, f, indent=2)
            print(f"\n💾 Results saved to scraped_files.json")
            
            # TODO: Send file data to backend or trigger ingestion
            print("\n📤 TODO: Implement backend integration")
            
        except Exception as e:
            print(f"❌ Error in main: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main()) 
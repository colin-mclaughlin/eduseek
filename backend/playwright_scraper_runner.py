import sys
import json
import asyncio
import os
import re
from playwright.async_api import async_playwright

async def login_and_get_session(p, username: str, password: str):
    # Set the correct browser path for Windows
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "C:\\Users\\colin\\AppData\\Local\\ms-playwright"
    
    # Try to use the regular Chromium browser with visible UI
    try:
        browser = await p.chromium.launch(headless=False, args=["--no-sandbox", "--disable-dev-shm-usage"])
    except Exception as e:
        print(f"Failed to launch Chromium: {e}")
        # Fallback: try to use the system Chrome if available
        try:
            browser = await p.chromium.launch(
                headless=False, 
                args=["--no-sandbox", "--disable-dev-shm-usage"],
                channel="chrome"  # Use system Chrome
            )
        except Exception as e2:
            print(f"Failed to launch system Chrome: {e2}")
            raise Exception("Could not launch any browser")
    context = await browser.new_context()
    page = await context.new_page()

    try:
        # Navigate to Queen's Brightspace login page
        await page.goto("https://onq.queensu.ca/")
        await asyncio.sleep(3)
        print(f"Current URL: {page.url}")

        # Look for various possible login elements
        login_selectors = [
            "text=Sign in with your organization",
            "text=Sign in",
            "text=Login",
            "button:has-text('Sign in')",
            "a:has-text('Sign in')"
        ]
        
        clicked_sso = False
        for selector in login_selectors:
            try:
                if await page.locator(selector).is_visible(timeout=2000):
                    print(f"Found login button: {selector}")
                    await page.locator(selector).click()
                    await page.wait_for_load_state("networkidle")
                    await asyncio.sleep(2)
                    clicked_sso = True
                    break
            except:
                continue
        
        print(f"SSO button clicked: {clicked_sso}")
        print(f"Current URL after SSO: {page.url}")

        # Check if we're on Microsoft login page
        if "login.microsoftonline.com" in page.url:
            print("Detected Microsoft login page")
            
            # Wait for page to fully load
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(3)
            
            # Wait for Microsoft login form with longer timeout
            try:
                await page.wait_for_selector('input[type="email"], input[name="loginfmt"], input[name="email"], input[type="text"]', timeout=15000)
            except:
                print("Timeout waiting for login form, trying to continue anyway...")
            
            # Debug: print all input elements on the page
            inputs = await page.query_selector_all('input')
            print(f"Found {len(inputs)} input elements on the page:")
            for i, inp in enumerate(inputs):
                input_type = await inp.get_attribute('type') or 'no-type'
                input_name = await inp.get_attribute('name') or 'no-name'
                input_id = await inp.get_attribute('id') or 'no-id'
                print(f"  Input {i}: type='{input_type}', name='{input_name}', id='{input_id}'")
            
            # Try to find the email field on Microsoft's page
            ms_username_selectors = ['input[name="loginfmt"]', 'input[type="email"]', 'input[name="email"]', 'input[type="text"]']
            username_field = None
            
            for selector in ms_username_selectors:
                try:
                    element = page.locator(selector)
                    if await element.count() > 0:
                        username_field = selector
                        print(f"Found Microsoft username field: {selector}")
                        break
                except Exception as e:
                    print(f"Error checking selector {selector}: {e}")
                    continue
            
            if not username_field:
                # Fallback: try by ID since we know it's 'i0116'
                try:
                    if await page.locator('#i0116').count() > 0:
                        username_field = '#i0116'
                        print("Found Microsoft username field by ID: #i0116")
                except:
                    pass
            
            if not username_field:
                print("Could not find username field on Microsoft page")
                page_content = await page.content()
                print(f"Page content: {page_content[:1000]}...")
                raise Exception("Username field not found on Microsoft login page")
            
            # Fill in username (NetID@queensu.ca format)
            if "@queensu.ca" not in username:
                full_username = f"{username}@queensu.ca"
            else:
                full_username = username
            
            await page.fill(username_field, full_username)
            print(f"Filled username: {full_username}")
            
        else:
            # Original logic for non-Microsoft pages
            username_selectors = ['input[type="email"]', 'input[name="userName"]', 'input[name="username"]', 'input[type="text"]']
            username_field = None
            
            for selector in username_selectors:
                try:
                    if await page.locator(selector).is_visible(timeout=3000):
                        username_field = selector
                        print(f"Found username field: {selector}")
                        break
                except:
                    continue
            
            if not username_field:
                print("Could not find username field")
                page_content = await page.content()
                print(f"Page content: {page_content[:500]}...")
                raise Exception("Username field not found")

            # Fill in username
            await page.fill(username_field, username)
            print("Filled username")
        
        # Look for submit button
        submit_selectors = ['input[type="submit"]', 'button[type="submit"]', 'button:has-text("Next")', 'button:has-text("Continue")']
        submit_clicked = False
        
        for selector in submit_selectors:
            try:
                if await page.locator(selector).is_visible(timeout=2000):
                    print(f"Found submit button: {selector}")
                    await page.locator(selector).click()
                    await page.wait_for_load_state("networkidle")
                    await asyncio.sleep(2)
                    submit_clicked = True
                    break
            except:
                continue
        
        if not submit_clicked:
            print("Could not find submit button, trying to press Enter")
            await page.keyboard.press("Enter")
            await asyncio.sleep(2)
        
        print(f"Current URL after username: {page.url}")

        # Wait for password field
        await page.wait_for_selector('input[type="password"]', timeout=10000)
        await page.fill('input[type="password"]', password)
        print("Filled password")
        
        # Submit password
        submit_clicked = False
        for selector in submit_selectors:
            try:
                if await page.locator(selector).is_visible(timeout=2000):
                    print(f"Found password submit button: {selector}")
                    await page.locator(selector).click()
                    await page.wait_for_load_state("networkidle")
                    await asyncio.sleep(3)
                    submit_clicked = True
                    break
            except:
                continue
        
        if not submit_clicked:
            print("Could not find password submit button, trying to press Enter")
            await page.keyboard.press("Enter")
            await asyncio.sleep(3)
        
        print(f"Current URL after password: {page.url}")
        
        # Wait for potential 2FA or redirect
        print("Waiting for login result or 2FA prompt...")
        await asyncio.sleep(10)  # Wait longer for 2FA to appear
        
        # Check if we're still on the same page or if there's been a redirect
        current_url = page.url
        print(f"Current URL after waiting: {current_url}")
        
        # Wait for any page changes
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except:
            print("Page load timeout, continuing anyway...")
        
        # Check for 2FA prompts or success
        current_url = page.url
        page_content = (await page.content()).lower()
        
        # --- Direct selector-based 2FA number detection ---
        print("Attempting direct selector-based 2FA number detection...")
        page_title = await page.title()
        print(f"Page title: {page_title}")
        
        twofa_number = None
        
        # Try to get 2FA number directly from the Microsoft Authenticator display element
        try:
            print("Looking for 2FA number using selector '#idRichContext_DisplaySign'...")
            display_sign_element = await page.wait_for_selector('#idRichContext_DisplaySign', timeout=30000)
            
            if display_sign_element:
                element_text = (await display_sign_element.inner_text()).strip()
                print(f"Found #idRichContext_DisplaySign element with text: '{element_text}'")
                
                # Extract 2-digit number from the element
                numbers = re.findall(r'\b(\d{2})\b', element_text)
                if numbers:
                    twofa_number = numbers[0]
                    print(f"SUCCESS: 2FA number extracted from selector: {twofa_number}")
                    print(f">>> ENTER THIS NUMBER ON YOUR AUTHENTICATOR APP: {twofa_number} <<<")
                else:
                    print(f"WARNING: Found selector but no 2-digit number in text: '{element_text}'")
            else:
                print("Selector found but element is None")
                
        except Exception as e:
            print(f"Direct selector method failed: {str(e)}")
            print("Falling back to context-based detection...")
        
        # --- Fallback: Line-by-line 2FA number detection logic ---
        if not twofa_number:
            print("Using fallback line-by-line targeted detection...")
            
            # 1. Collect all 2-digit numbers and their line context from visible elements
            visible_elements = await page.query_selector_all('p, div, span, h1, h2, h3, h4, h5, h6, label, button')
            all_candidates = []  # List of (number, line_text, element_full_text, line_index)
        
            target_phrases = [
                "enter the number shown to sign in",
                "open your authenticator app"
            ]
            
            exclusion_phrases = [
                "don't ask again for",
                "remember this device",
                "stay signed in"
            ]
            
            for element in visible_elements:
                try:
                    if await element.is_visible():
                        full_text = (await element.inner_text()).strip()
                        if full_text and len(full_text) > 0:
                            # Split element text into lines
                            lines = [line.strip() for line in full_text.split('\n') if line.strip()]
                            
                            for line_idx, line in enumerate(lines):
                                line_lower = line.lower()
                                numbers = re.findall(r'\b(\d{2})\b', line)
                                
                                for num in numbers:
                                    all_candidates.append((num, line, full_text, line_idx))
                                    print(f"DEBUG: Found number '{num}' in line {line_idx}: '{line}'")
                except:
                    continue
        
            print(f"DEBUG: Total candidates found: {len(all_candidates)}")
            
            # 2. Process candidates with line-by-line logic
            strong_candidates = []
            weak_candidates = []
            excluded_candidates = []
        
            for num, line, full_text, line_idx in all_candidates:
                line_lower = line.lower()
                
                # Check if number is in same line as target phrase
                has_target_in_same_line = any(phrase in line_lower for phrase in target_phrases)
                
                # Check if number is in line following a target phrase
                has_target_in_previous_line = False
                if line_idx > 0:
                    lines = [l.strip() for l in full_text.split('\n') if l.strip()]
                    if line_idx < len(lines):
                        prev_line = lines[line_idx - 1].lower()
                        has_target_in_previous_line = any(phrase in prev_line for phrase in target_phrases)
                
                # Check if number should be excluded (exclusion phrase in SAME line as number)
                has_exclusion_in_same_line = any(exclusion in line_lower for exclusion in exclusion_phrases)
                
                if has_exclusion_in_same_line:
                    excluded_candidates.append((num, line))
                    print(f"DEBUG: EXCLUDED number '{num}' - exclusion phrase in same line: '{line}'")
                elif has_target_in_same_line:
                    strong_candidates.append((num, line, "same_line"))
                    print(f"DEBUG: STRONG candidate '{num}' - target phrase in same line: '{line}'")
                elif has_target_in_previous_line:
                    strong_candidates.append((num, line, "following_line"))
                    print(f"DEBUG: STRONG candidate '{num}' - follows target phrase: '{line}'")
                else:
                    # Check for general 2FA context in the line
                    general_phrases = ["authenticator", "verification", "approve", "sign in"]
                    if any(phrase in line_lower for phrase in general_phrases):
                        weak_candidates.append((num, line, "general_context"))
                        print(f"DEBUG: WEAK candidate '{num}' - general 2FA context: '{line}'")
                    else:
                        print(f"DEBUG: IGNORED number '{num}' - no relevant context: '{line}'")
            
            print(f"DEBUG: Strong candidates: {[(num, reason) for num, line, reason in strong_candidates]}")
            print(f"DEBUG: Weak candidates: {[(num, reason) for num, line, reason in weak_candidates]}")
            print(f"DEBUG: Excluded candidates: {[num for num, line in excluded_candidates]}")
            
            # 3. Pick the best candidate
            selected_reason = None
            
            if strong_candidates:
                # Prefer numbers in same line as target phrase, then following lines
                same_line_candidates = [c for c in strong_candidates if c[2] == "same_line"]
                if same_line_candidates:
                    twofa_number = same_line_candidates[0][0]
                    selected_reason = f"same line as target phrase: '{same_line_candidates[0][1]}'"
                else:
                    twofa_number = strong_candidates[0][0]
                    selected_reason = f"line following target phrase: '{strong_candidates[0][1]}'"
                print(f"Selected 2FA number from strong candidates: {twofa_number} ({selected_reason})")
            elif weak_candidates:
                twofa_number = weak_candidates[0][0]
                selected_reason = f"general 2FA context: '{weak_candidates[0][1]}'"
                print(f"Selected 2FA number from weak candidates: {twofa_number} ({selected_reason})")
            
            if twofa_number:
                print(f"Final 2FA number detected: {twofa_number}")
            else:
                print("No 2FA number found with line-by-line targeted detection")

        # Check for various success and 2FA indicators
        success_indicators = [
            "/d2l/home" in current_url,
            "onq.queensu.ca/d2l" in current_url,
            "brightspace" in current_url
        ]
        
        # Check for 2FA indicators
        twofa_indicators = [
            "verification" in page_content,
            "authenticator" in page_content,
            "approve" in page_content,
            "notification" in page_content,
            "microsoft authenticator" in page_content,
            "enter the number" in page_content,
            "enter this number" in page_content,
            "verification code" in page_content
        ]
        
        success = any(success_indicators)
        twofa_required = any(twofa_indicators)
        
        print(f"Success indicators found: {success}")
        print(f"2FA indicators found: {twofa_required}")
        print(f"Current URL: {current_url}")
        
        # Check if already at dashboard
        if success:
            print(f"Login successful - dashboard already detected at: {current_url}")
            return browser, context, page
        
        # Handle 2FA if required
        if twofa_required:
            message = "Two-factor authentication required"
            if twofa_number:
                message = f"Two-factor authentication required - enter {twofa_number} on your phone"
            print(f"2FA detected: {message}")
            
            # Wait for post-2FA events: "Stay signed in?" or OnQ dashboard
            print("Waiting for 2FA completion - monitoring for 'Stay signed in?' prompt or OnQ dashboard...")
            import time
            start_time = time.time()
            timeout_seconds = 120  # 2 minutes
            
            while time.time() - start_time < timeout_seconds:
                await asyncio.sleep(1)
                current_url = page.url
                
                # Event 1: Check for "Stay Signed In" page - both URL and DOM detection
                stay_signed_in_detected = False
                detection_method = None
                
                # Method 1: URL-based detection
                if "/SAS/ProcessAuth" in current_url:
                    stay_signed_in_detected = True
                    detection_method = f"URL detection: {current_url}"
                
                # Method 2: DOM-based detection - check for "No" button presence
                if not stay_signed_in_detected:
                    no_button_selectors = [
                        'input#idBtn_Back',
                        'input[type="button"][value="No"]'
                    ]
                    
                    for selector in no_button_selectors:
                        try:
                            if await page.locator(selector).is_visible():  # No timeout argument
                                stay_signed_in_detected = True
                                detection_method = f"DOM detection: found button '{selector}'"
                                break
                        except:
                            continue
                
                # Handle "Stay signed in?" prompt if detected
                if stay_signed_in_detected:
                    print(f"EVENT DETECTED: 'Stay signed in?' prompt via {detection_method}")
                    print("Automatically clicking 'No' to proceed to dashboard...")
                    
                    # Improved "No" button clicking with tab management
                    clicked_no = False
                    click_method = None
                    
                    # Record initial tab count
                    initial_pages = len(context.pages)
                    
                    # Try primary selector: input#idBtn_Back
                    try:
                        if await page.locator('input#idBtn_Back').is_visible():
                            print("Found 'No' button with primary selector: input#idBtn_Back")
                            await page.click('input#idBtn_Back')
                            clicked_no = True
                            click_method = "Primary selector: input#idBtn_Back"
                    except Exception as e:
                        print(f"Error with primary selector input#idBtn_Back: {e}")
                    
                    # Try fallback selector if primary failed
                    if not clicked_no:
                        try:
                            if await page.locator('input[type="button"][value="No"]').is_visible():
                                print("Found 'No' button with fallback selector: input[type=\"button\"][value=\"No\"]")
                                await page.click('input[type="button"][value="No"]')
                                clicked_no = True
                                click_method = "Fallback selector: input[type=\"button\"][value=\"No\"]"
                        except Exception as e:
                            print(f"Error with fallback selector: {e}")
                    
                    # Check for new tabs and close them if they appeared
                    current_pages = len(context.pages)
                    if current_pages > initial_pages:
                        print(f"Detected {current_pages - initial_pages} new tab(s) opened, closing them...")
                        # Close all new tabs and refocus on original
                        for i in range(initial_pages, current_pages):
                            try:
                                await context.pages[i].close()
                                print(f"Closed new tab {i}")
                            except:
                                pass
                        # Ensure we're focused on the original page
                        await page.bring_to_front()
                        print("Refocused on original tab")
                    
                    # Keyboard navigation as last resort
                    if not clicked_no:
                        print("Both selectors failed - attempting keyboard navigation (Tab+Enter)")
                        try:
                            await page.keyboard.press("Tab")
                            await page.keyboard.press("Enter")
                            clicked_no = True
                            click_method = "Keyboard navigation: Tab+Enter"
                        except Exception as e:
                            print(f"Keyboard navigation failed: {e}")
                    
                    if clicked_no:
                        print(f"Successfully handled 'Stay signed in?' prompt using method: {click_method}")
                        print("Waiting for navigation to dashboard...")
                        try:
                            await page.wait_for_load_state("networkidle", timeout=10000)
                        except:
                            print("Navigation timeout, continuing anyway...")
                        await asyncio.sleep(2)
                    else:
                        print("WARNING: All methods failed to click 'No' button")
                    
                    current_url = page.url
                    print(f"URL after handling 'Stay signed in?' prompt: {current_url}")
                    
                    # After handling "Stay signed in?", continue waiting for dashboard
                    continue
                
                # Event 2: Check for OnQ dashboard navigation
                dashboard_url_detected = "/d2l/home" in current_url or "onq.queensu.ca" in current_url
                
                if dashboard_url_detected:
                    print(f"EVENT DETECTED: OnQ dashboard URL at: {current_url}")
                    
                    # Wait a moment for dashboard elements to load
                    await asyncio.sleep(2)
                    
                    # Check for dashboard-specific elements
                    dashboard_selectors = [
                        'd2l-navigation-sidenav',
                        '.d2l-navigation',
                        '[data-role="navigation"]'
                    ]
                    
                    dashboard_element_found = False
                    for selector in dashboard_selectors:
                        try:
                            if await page.locator(selector).is_visible(timeout=3000):
                                print(f"Dashboard element confirmed with selector: {selector}")
                                dashboard_element_found = True
                                break
                        except:
                            continue
                    
                    # Also check for dashboard text content
                    page_content = await page.content()
                    dashboard_text_found = any(text in page_content for text in ["Dashboard", "My Courses"])
                    
                    if dashboard_element_found or dashboard_text_found:
                        print(f"SUCCESS: OnQ dashboard fully loaded and confirmed at: {current_url}")
                        return browser, context, page
                    else:
                        print("OnQ URL detected but dashboard elements not yet loaded, continuing to wait...")
                        continue
            
            # Timeout handling
            elapsed_time = time.time() - start_time
            print(f"TIMEOUT: No dashboard detected after {elapsed_time:.1f} seconds")
            print(f"Final URL: {page.url}")
            raise Exception(f"Post-2FA timeout: Dashboard not detected within {timeout_seconds} seconds. Final URL: {page.url}")
        else:
            raise Exception(f"Login failed - could not detect 2FA or reach dashboard. Current URL: {current_url}")

    except Exception as e:
        print(f"Exception occurred: {str(e)}")
        raise e

async def main():
    if len(sys.argv) < 3:
        print("Usage: python playwright_scraper_runner.py <username> <password>")
        sys.exit(1)

    username = sys.argv[1]
    password = sys.argv[2]
    
    try:
        print("Starting login process...")
        async with async_playwright() as p:
            browser, context, page = await login_and_get_session(p, username, password)
            print("Login function completed successfully!")
            print(f"Browser object: {browser}")
            print(f"Context object: {context}")
            print(f"Page object: {page}")
            print(f"Current URL: {page.url}")
            print("Browser will remain open for testing. Close manually when done.")
            
            # Keep the script running so browser stays open
            input("Press Enter to close the browser and exit...")
            await browser.close()
        
    except Exception as e:
        print(f"Login failed with error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
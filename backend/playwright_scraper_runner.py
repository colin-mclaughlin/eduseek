import sys
import json
import time
import os
import re
from playwright.sync_api import sync_playwright

def login_and_get_session(username: str, password: str):
    # Set the correct browser path for Windows
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "C:\\Users\\colin\\AppData\\Local\\ms-playwright"
    
    with sync_playwright() as p:
        # Try to use the regular Chromium browser with visible UI
        try:
            browser = p.chromium.launch(headless=False, args=["--no-sandbox", "--disable-dev-shm-usage"])
        except Exception as e:
            print(f"Failed to launch Chromium: {e}")
            # Fallback: try to use the system Chrome if available
            try:
                browser = p.chromium.launch(
                    headless=False, 
                    args=["--no-sandbox", "--disable-dev-shm-usage"],
                    channel="chrome"  # Use system Chrome
                )
            except Exception as e2:
                print(f"Failed to launch system Chrome: {e2}")
                raise Exception("Could not launch any browser")
        context = browser.new_context()
        page = context.new_page()

        try:
            # Navigate to Queen's Brightspace login page
            page.goto("https://onq.queensu.ca/")
            time.sleep(3)
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
                    if page.locator(selector).is_visible(timeout=2000):
                        print(f"Found login button: {selector}")
                        page.locator(selector).click()
                        page.wait_for_load_state("networkidle")
                        time.sleep(2)
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
                page.wait_for_load_state("networkidle")
                time.sleep(3)
                
                # Wait for Microsoft login form with longer timeout
                try:
                    page.wait_for_selector('input[type="email"], input[name="loginfmt"], input[name="email"], input[type="text"]', timeout=15000)
                except:
                    print("Timeout waiting for login form, trying to continue anyway...")
                
                # Debug: print all input elements on the page
                inputs = page.query_selector_all('input')
                print(f"Found {len(inputs)} input elements on the page:")
                for i, inp in enumerate(inputs):
                    input_type = inp.get_attribute('type') or 'no-type'
                    input_name = inp.get_attribute('name') or 'no-name'
                    input_id = inp.get_attribute('id') or 'no-id'
                    print(f"  Input {i}: type='{input_type}', name='{input_name}', id='{input_id}'")
                
                # Try to find the email field on Microsoft's page
                ms_username_selectors = ['input[name="loginfmt"]', 'input[type="email"]', 'input[name="email"]', 'input[type="text"]']
                username_field = None
                
                for selector in ms_username_selectors:
                    try:
                        element = page.locator(selector)
                        if element.count() > 0:
                            username_field = selector
                            print(f"Found Microsoft username field: {selector}")
                            break
                    except Exception as e:
                        print(f"Error checking selector {selector}: {e}")
                        continue
                
                if not username_field:
                    # Fallback: try by ID since we know it's 'i0116'
                    try:
                        if page.locator('#i0116').count() > 0:
                            username_field = '#i0116'
                            print("Found Microsoft username field by ID: #i0116")
                    except:
                        pass
                
                if not username_field:
                    print("Could not find username field on Microsoft page")
                    print(f"Page content: {page.content()[:1000]}...")
                    raise Exception("Username field not found on Microsoft login page")
                
                # Fill in username (NetID@queensu.ca format)
                if "@queensu.ca" not in username:
                    full_username = f"{username}@queensu.ca"
                else:
                    full_username = username
                
                page.fill(username_field, full_username)
                print(f"Filled username: {full_username}")
                
            else:
                # Original logic for non-Microsoft pages
                username_selectors = ['input[type="email"]', 'input[name="userName"]', 'input[name="username"]', 'input[type="text"]']
                username_field = None
                
                for selector in username_selectors:
                    try:
                        if page.locator(selector).is_visible(timeout=3000):
                            username_field = selector
                            print(f"Found username field: {selector}")
                            break
                    except:
                        continue
                
                if not username_field:
                    print("Could not find username field")
                    print(f"Page content: {page.content()[:500]}...")
                    raise Exception("Username field not found")

                # Fill in username
                page.fill(username_field, username)
                print("Filled username")
            
            # Look for submit button
            submit_selectors = ['input[type="submit"]', 'button[type="submit"]', 'button:has-text("Next")', 'button:has-text("Continue")']
            submit_clicked = False
            
            for selector in submit_selectors:
                try:
                    if page.locator(selector).is_visible(timeout=2000):
                        print(f"Found submit button: {selector}")
                        page.locator(selector).click()
                        page.wait_for_load_state("networkidle")
                        time.sleep(2)
                        submit_clicked = True
                        break
                except:
                    continue
            
            if not submit_clicked:
                print("Could not find submit button, trying to press Enter")
                page.keyboard.press("Enter")
                time.sleep(2)
            
            print(f"Current URL after username: {page.url}")

            # Wait for password field
            page.wait_for_selector('input[type="password"]', timeout=10000)
            page.fill('input[type="password"]', password)
            print("Filled password")
            
            # Submit password
            submit_clicked = False
            for selector in submit_selectors:
                try:
                    if page.locator(selector).is_visible(timeout=2000):
                        print(f"Found password submit button: {selector}")
                        page.locator(selector).click()
                        page.wait_for_load_state("networkidle")
                        time.sleep(3)
                        submit_clicked = True
                        break
                except:
                    continue
            
            if not submit_clicked:
                print("Could not find password submit button, trying to press Enter")
                page.keyboard.press("Enter")
                time.sleep(3)
            
            print(f"Current URL after password: {page.url}")
            
            # Wait for potential 2FA or redirect
            print("Waiting for login result or 2FA prompt...")
            time.sleep(10)  # Wait longer for 2FA to appear
            
            # Check if we're still on the same page or if there's been a redirect
            current_url = page.url
            print(f"Current URL after waiting: {current_url}")
            
            # Wait for any page changes
            try:
                page.wait_for_load_state("networkidle", timeout=15000)
            except:
                print("Page load timeout, continuing anyway...")
            
            # Check for 2FA prompts or success
            current_url = page.url
            page_content = page.content().lower()
            
            # --- Direct selector-based 2FA number detection ---
            print("Attempting direct selector-based 2FA number detection...")
            print(f"Page title: {page.title()}")
            
            twofa_number = None
            
            # Try to get 2FA number directly from the Microsoft Authenticator display element
            try:
                print("Looking for 2FA number using selector '#idRichContext_DisplaySign'...")
                display_sign_element = page.wait_for_selector('#idRichContext_DisplaySign', timeout=30000)
                
                if display_sign_element:
                    element_text = display_sign_element.inner_text().strip()
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
                visible_elements = page.query_selector_all('p, div, span, h1, h2, h3, h4, h5, h6, label, button')
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
                        if element.is_visible():
                            full_text = element.inner_text().strip()
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
                
                # Wait for user to complete 2FA and monitor for navigation
                print("Waiting for 2FA completion and navigation...")
                for i in range(120):  # Wait up to 2 minutes for 2FA completion
                    time.sleep(1)
                    current_url = page.url
                    
                    # Check for "Stay Signed In" page (SAS/ProcessAuth)
                    if "/SAS/ProcessAuth" in current_url:
                        print(f"Detected 'Stay Signed In' page at: {current_url}")
                        print("Automatically clicking 'No' to continue...")
                        
                        # Try multiple selectors for the "No" button
                        no_button_selectors = [
                            'input#idBtn_Back',
                            'input[type="button"][value="No"]',
                            'button:has-text("No")',
                            'input[value="No"]'
                        ]
                        
                        clicked_no = False
                        for selector in no_button_selectors:
                            try:
                                if page.locator(selector).is_visible(timeout=2000):
                                    print(f"Found 'No' button with selector: {selector}")
                                    page.locator(selector).click()
                                    print("Clicked 'No' button")
                                    page.wait_for_load_state("networkidle", timeout=10000)
                                    time.sleep(2)
                                    clicked_no = True
                                    break
                            except:
                                continue
                        
                        if not clicked_no:
                            print("Could not find 'No' button, trying keyboard navigation")
                            page.keyboard.press("Tab")
                            page.keyboard.press("Enter")
                            time.sleep(2)
                        
                        current_url = page.url
                        print(f"URL after clicking 'No': {current_url}")
                    
                    # Check for successful navigation to OnQ dashboard
                    if "/d2l/home" in current_url or "onq.queensu.ca/d2l" in current_url:
                        print(f"Navigation to OnQ detected at: {current_url}")
                        
                        # Wait for dashboard elements to load
                        time.sleep(3)
                        try:
                            # Look for dashboard-specific elements
                            dashboard_selectors = [
                                'd2l-navigation-sidenav',
                                '[data-role="navigation"]',
                                '.d2l-navigation',
                                'nav[role="navigation"]'
                            ]
                            
                            dashboard_found = False
                            for selector in dashboard_selectors:
                                try:
                                    if page.locator(selector).is_visible(timeout=5000):
                                        print(f"Dashboard element confirmed with selector: {selector}")
                                        dashboard_found = True
                                        break
                                except:
                                    continue
                            
                            if dashboard_found or "Dashboard" in page.content():
                                print(f"Login complete - OnQ dashboard confirmed at: {current_url}")
                                return browser, context, page
                            else:
                                print("OnQ URL detected but dashboard elements not found, continuing to wait...")
                        except:
                            print("Error checking for dashboard elements, but URL looks correct")
                            return browser, context, page
                
                print("2FA/navigation timeout - returning browser for manual completion")
                return browser, context, page
            else:
                raise Exception(f"Login failed - could not detect 2FA or reach dashboard. Current URL: {current_url}")

        except Exception as e:
            print(f"Exception occurred: {str(e)}")
            raise e

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python playwright_scraper_runner.py <username> <password>")
        sys.exit(1)

    username = sys.argv[1]
    password = sys.argv[2]
    
    try:
        print("Starting login process...")
        browser, context, page = login_and_get_session(username, password)
        print("Login function completed successfully!")
        print(f"Browser object: {browser}")
        print(f"Context object: {context}")
        print(f"Page object: {page}")
        print(f"Current URL: {page.url}")
        print("Browser will remain open for testing. Close manually when done.")
        
        # Keep the script running so browser stays open
        input("Press Enter to close the browser and exit...")
        browser.close()
        
    except Exception as e:
        print(f"Login failed with error: {str(e)}")
        sys.exit(1) 
import sys
import json
import time
import os
import re
from playwright.sync_api import sync_playwright

def scrape_brightspace(username: str, password: str):
    # Set the correct browser path for Windows
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "C:\\Users\\colin\\AppData\\Local\\ms-playwright"
    
    with sync_playwright() as p:
        # Try to use the regular Chromium browser instead of headless shell
        try:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        except Exception as e:
            print(f"Failed to launch Chromium: {e}")
            # Fallback: try to use the system Chrome if available
            try:
                browser = p.chromium.launch(
                    headless=True, 
                    args=["--no-sandbox", "--disable-dev-shm-usage"],
                    channel="chrome"  # Use system Chrome
                )
            except Exception as e2:
                print(f"Failed to launch system Chrome: {e2}")
                raise Exception("Could not launch any browser")
        page = browser.new_page()

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
            
            # Debug: Let's look for the actual 2FA number element
            print("Looking for 2FA number elements...")
            
            # First, let's see what the page actually contains
            page_content_full = page.content()
            print(f"Page title: {page.title()}")
            
            # Look for any text that might contain 2FA information
            all_text_elements = page.query_selector_all('*')
            twofa_number = None
            
            # First, let's look for the number in the page title or main heading
            page_title = page.title()
            if page_title:
                title_numbers = re.findall(r'\b(\d{2})\b', page_title)
                if title_numbers:
                    twofa_number = title_numbers[0]
                    print(f"Found 2FA number in page title: {twofa_number}")
            
            # If not in title, look for numbers in prominent text elements
            if not twofa_number:
                # Look for numbers in headings, paragraphs, and divs
                prominent_selectors = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div[class*="message"]', 'div[class*="notification"]', 'div[class*="verification"]']
                
                for selector in prominent_selectors:
                    try:
                        elements = page.query_selector_all(selector)
                        for element in elements:
                            text = element.inner_text().strip()
                            if text and len(text) > 0:
                                # Look for 2FA-related keywords
                                if any(keyword in text.lower() for keyword in ['enter', 'number', 'approve', 'authenticator', 'sign in request', 'verification']):
                                    print(f"Found 2FA-related text in {selector}: '{text[:200]}...'")
                                    # Look for 2-digit numbers in this text
                                    numbers = re.findall(r'\b(\d{2})\b', text)
                                    if numbers:
                                        twofa_number = numbers[0]
                                        print(f"Found 2FA number in {selector}: {twofa_number}")
                                        break
                        if twofa_number:
                            break
                    except:
                        continue
            
            # If still no 2FA number found, let's look for any large numbers on the page
            if not twofa_number:
                print("No 2FA number found in prominent text, looking for any 2-digit numbers...")
                
                # Look for numbers in visible, selectable text elements first
                print("Looking for numbers in visible text elements...")
                visible_elements = page.query_selector_all('p, div, span, h1, h2, h3, h4, h5, h6, label, button')
                visible_numbers = []
                
                for element in visible_elements:
                    try:
                        # Check if element is visible
                        if element.is_visible():
                            text = element.inner_text().strip()
                            if text and len(text) > 0:
                                # Look for 2-digit numbers in this visible text
                                numbers = re.findall(r'\b(\d{2})\b', text)
                                for num in numbers:
                                    visible_numbers.append((num, text[:100]))  # Store number and context
                                    print(f"Found number '{num}' in visible element: '{text[:200]}...'")
                    except:
                        continue
                
                print(f"All numbers found in visible elements: {visible_numbers}")
                
                # Also try to find the largest/most prominent number (likely the 2FA number)
                print("Looking for the most prominent number on the page...")
                try:
                    # Look for numbers in larger text or prominent positions
                    large_text_elements = page.query_selector_all('h1, h2, h3, div[style*="font-size"], div[class*="large"], div[class*="prominent"]')
                    for element in large_text_elements:
                        if element.is_visible():
                            text = element.inner_text().strip()
                            if text:
                                numbers = re.findall(r'\b(\d{2})\b', text)
                                for num in numbers:
                                    print(f"Found number '{num}' in large/prominent element: '{text[:200]}...'")
                except:
                    pass
                
                # If we found numbers in visible elements, use the first one
                if visible_numbers:
                    # Look for the number that appears in 2FA-related context
                    for num, context in visible_numbers:
                        if any(keyword in context.lower() for keyword in ['approve', 'authenticator', 'enter', 'number', 'sign in']):
                            twofa_number = num
                            print(f"Found 2FA number in visible text: {twofa_number} (context: {context})")
                            break
                    else:
                        # If no 2FA-related context found, use the first number
                        twofa_number = visible_numbers[0][0]
                        print(f"Found number in visible text (fallback): {twofa_number} (context: {visible_numbers[0][1]})")
                else:
                    # Fallback: Get all text content and look for numbers
                    all_text = page.evaluate("() => document.body.innerText")
                    try:
                        print(f"Full page text (first 1000 chars): {all_text[:1000]}")
                    except UnicodeEncodeError:
                        print("Full page text (first 1000 chars): [Content contains special characters]")
                    
                    numbers = re.findall(r'\b(\d{2})\b', all_text)
                    print(f"All 2-digit numbers found: {numbers}")
                    if numbers:
                        twofa_number = numbers[0]
                        print(f"Found number in page text: {twofa_number}")
                        
                        # Let's also check where this number appears in the HTML
                        page_html = page.content()
                        # Find the context around this number
                        number_index = page_html.find(twofa_number)
                        if number_index != -1:
                            start = max(0, number_index - 100)
                            end = min(len(page_html), number_index + 100)
                            context = page_html[start:end]
                            try:
                                print(f"Context around number '{twofa_number}': {context}")
                            except UnicodeEncodeError:
                                print(f"Context around number '{twofa_number}': [Content contains special characters]")
            
            # Check for various success indicators
            success_indicators = [
                "d2l/home" in current_url,
                "onq.queensu.ca/d2l" in current_url,
                "brightspace" in current_url,
                "dashboard" in page_content,
                "welcome" in page_content
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
            
            # Look for the 2-digit number on the page - be more specific
            
            # Try to find the number in specific 2FA-related elements first
            twofa_number = None
            
            # Look for numbers in specific 2FA-related text patterns
            twofa_patterns = [
                r'enter\s+(\d{2})\s+on\s+your\s+phone',
                r'enter\s+(\d{2})\s+in\s+your\s+app',
                r'enter\s+(\d{2})\s+to\s+sign\s+in',
                r'number\s+(\d{2})\s+shown',
                r'(\d{2})\s+to\s+approve',
                r'approve\s+(\d{2})',
                r'enter\s+(\d{2})',
                r'(\d{2})\s+to\s+continue',
                r'verification\s+code\s+(\d{2})',
            ]
            
            for pattern in twofa_patterns:
                match = re.search(pattern, page_content, re.IGNORECASE)
                if match:
                    twofa_number = match.group(1)
                    print(f"Found 2FA number using pattern '{pattern}': {twofa_number}")
                    break
            
            # If no specific pattern found, look for numbers in larger text (likely the main 2FA number)
            if not twofa_number:
                # Look for numbers that appear in larger text or prominent positions
                # This is a fallback - we'll look for any 2-digit number
                all_numbers = re.findall(r'\b(\d{2})\b', page_content)
                if all_numbers:
                    # Take the first one found (usually the most prominent)
                    twofa_number = all_numbers[0]
                    print(f"Found 2FA number (fallback): {twofa_number}")
            
            if twofa_number:
                print(f"Final 2FA number: {twofa_number}")
            else:
                print("No 2FA number found")
            
            success = any(success_indicators)
            twofa_required = any(twofa_indicators)
            
            print(f"Success indicators found: {success}")
            print(f"2FA indicators found: {twofa_required}")
            print(f"Final URL: {current_url}")

            browser.close()

            if success:
                print(json.dumps({
                    "status": "success",
                    "message": "Login successful",
                    "url": current_url
                }))
            elif twofa_required:
                message = "Two-factor authentication required"
                if twofa_number:
                    message = f"Two-factor authentication required - enter {twofa_number} on your phone"
                
                print(json.dumps({
                    "status": "twofa_required",
                    "message": message,
                    "url": current_url,
                    "twofa_number": twofa_number
                }))
            else:
                print(json.dumps({
                    "status": "failure",
                    "message": "Login failed - could not reach dashboard",
                    "url": current_url
                }))

        except Exception as e:
            browser.close()
            print(json.dumps({
                "status": "error",
                "message": f"Exception occurred: {str(e)}"
            }))

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(json.dumps({"status": "error", "message": "Username and password required"}))
        sys.exit(1)

    username = sys.argv[1]
    password = sys.argv[2]
    scrape_brightspace(username, password) 
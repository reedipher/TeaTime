"""
Authentication component test to validate login functionality
"""

import os
import sys
import asyncio
import json
from datetime import datetime

# Add parent directory to path so we can import our modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.tests.functional.test_base import BaseTestCase, run_test
from src.functions.auth import login_to_club_caddie

class LoginTest(BaseTestCase):
    """Test case for validating Club Caddie login functionality"""
    
    def __init__(self):
        super().__init__("login_test")
        
    async def run(self):
        """Run the login test"""
        self.logger.info("Running login test")
        
        # Validate required configuration
        if not self.config["club_caddie_username"] or not self.config["club_caddie_password"]:
            self.logger.error("Missing Club Caddie credentials in environment variables")
            self.set_test_result(False, "Missing credentials in environment variables")
            return False
            
        # First, validate manual navigation to login page
        await self.navigate(
            "https://customer-cc36.clubcaddie.com/login?clubid=103412",
            "Navigating to Club Caddie login page"
        )
        
        # Check if login page loaded properly
        username_field = await self.wait_for_element("#Username", 10000, "Looking for username field")
        if not username_field:
            self.set_test_result(False, "Could not find username field - login page may not have loaded correctly")
            return False
            
        # Take snapshot of the page structure for future reference
        page_elements = await self._analyze_login_page()
        self.logger.info(f"Found {len(page_elements)} form elements on the login page")
        
        # Test filling in the login form manually
        await self.debug_pause("Before filling login form")
        
        # Fill username field
        username_success = await self.fill_form(
            "#Username",
            self.config["club_caddie_username"],
            "Filling username field"
        )
        
        # Fill password field
        password_success = await self.fill_form(
            "#Password", 
            self.config["club_caddie_password"],
            "Filling password field"
        )
        
        if not (username_success and password_success):
            self.set_test_result(False, "Failed to fill login form")
            return False
            
        # Click sign in button
        await self.debug_pause("Before clicking sign in button")
        signin_success = await self.click_element("#signIn", "Clicking sign in button")
        
        if not signin_success:
            self.set_test_result(False, "Failed to click sign in button")
            return False
            
        # Wait for login to complete
        await self.page.wait_for_load_state("networkidle")
        await self.debug_pause("After login submission")
        
        # Verify successful login
        current_url = self.page.url
        self.logger.info(f"Current URL after login: {current_url}")
        
        # Check if we're no longer on the login page
        if "login" in current_url.lower():
            self.logger.error("Still on login page after sign-in - authentication failed")
            
            # Check for error messages
            error_messages = await self._extract_error_messages()
            if error_messages:
                self.logger.error(f"Login error messages: {json.dumps(error_messages)}")
                
            self.set_test_result(False, "Authentication failed - still on login page")
            return False
        else:
            self.logger.info("Login successful - navigated away from login page")
            
            # Check for authentication cookies/storage to validate session
            auth_data = await self._check_auth_data()
            self.logger.info(f"Authentication data present: {auth_data['present']}")
            
            # Take screenshot of logged-in state
            await self._take_screenshot("logged_in_state")
            
            # Now try the consolidated login function to compare results
            self.logger.info("Testing consolidated login_to_club_caddie function")
            await self._test_login_function()
            
            self.set_test_result(True, "Authentication successful")
            return True
            
    async def _analyze_login_page(self):
        """Analyze the login page structure to identify key elements"""
        elements = await self.page.evaluate("""() => {
            const formElements = [];
            const inputs = document.querySelectorAll('input');
            const buttons = document.querySelectorAll('button');
            
            inputs.forEach(input => {
                formElements.push({
                    type: 'input',
                    inputType: input.type,
                    id: input.id,
                    name: input.name,
                    placeholder: input.placeholder,
                    required: input.required
                });
            });
            
            buttons.forEach(button => {
                formElements.push({
                    type: 'button',
                    id: button.id,
                    text: button.innerText,
                    disabled: button.disabled
                });
            });
            
            return formElements;
        }""")
        
        # Add this information to the test results
        self._add_step("analyze_login_page", "Analyzing login page structure", {
            "form_elements": elements
        })
        
        return elements
        
    async def _extract_error_messages(self):
        """Extract error messages from the login page"""
        error_messages = await self.page.evaluate("""() => {
            const errors = [];
            const errorElements = document.querySelectorAll('.validation-summary-errors, .field-validation-error, [class*="error"], [role="alert"]');
            
            errorElements.forEach(el => {
                const text = el.innerText.trim();
                if (text) {
                    errors.push({
                        text: text,
                        element: el.tagName,
                        class: el.className
                    });
                }
            });
            
            return errors;
        }""")
        
        return error_messages
        
    async def _check_auth_data(self):
        """Check for authentication data in cookies and local storage"""
        cookies = await self.context.cookies()
        
        # Check localStorage for auth tokens
        local_storage = await self.page.evaluate("""() => {
            const data = {};
            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                if (key.toLowerCase().includes('token') || 
                    key.toLowerCase().includes('auth') || 
                    key.toLowerCase().includes('session')) {
                    data[key] = localStorage.getItem(key);
                }
            }
            return data;
        }""")
        
        # Check for relevant cookies
        auth_cookies = [c for c in cookies if c['name'].lower().find('auth') >= 0 or 
                                               c['name'].lower().find('session') >= 0 or
                                               c['name'].lower().find('token') >= 0]
        
        result = {
            "present": bool(auth_cookies or local_storage),
            "cookies": auth_cookies,
            "local_storage": local_storage
        }
        
        self._add_step("check_auth_data", "Checking authentication data", result)
        return result
        
    async def _test_login_function(self):
        """Test the consolidated login function"""
        # First close current browser
        await self.browser.close()
        
        step_id = "consolidated_login"
        self._add_step(step_id, "Testing consolidated login_to_club_caddie function")
        
        try:
            # Use the existing login function
            page, browser, playwright = await login_to_club_caddie()
            
            if page and browser and playwright:
                self.logger.info("Consolidated login function successful")
                
                # Take screenshot of the result
                current_url = page.url
                await page.screenshot(path=f"{self.test_output_dir}/screenshots/consolidated_login.png")
                self.results["screenshots"].append(f"{self.test_output_dir}/screenshots/consolidated_login.png")
                
                # Clean up
                await browser.close()
                await playwright.stop()
                
                self._update_step_status(step_id, "success", {
                    "url": current_url,
                    "successful": True
                })
                return True
            else:
                self.logger.error("Consolidated login function failed")
                self._update_step_status(step_id, "failed", {
                    "successful": False
                })
                return False
                
        except Exception as e:
            self.logger.error(f"Error testing consolidated login: {str(e)}")
            self._add_error(step_id, f"Consolidated login failed: {str(e)}")
            self._update_step_status(step_id, "failed")
            return False

async def main():
    """Run the login test"""
    test = LoginTest()
    success = await run_test(test)
    print(f"Test {'successful' if success else 'failed'}")

if __name__ == "__main__":
    asyncio.run(main())

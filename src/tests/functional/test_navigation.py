"""
Navigation component test to validate tee sheet and booking page functionality
"""

import os
import sys
import asyncio
import json
from datetime import datetime, timedelta

# Add parent directory to path so we can import our modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from tests.functional.test_base import BaseTestCase, run_test
from functions.auth import login_to_club_caddie
from functions.booking import navigate_to_tee_sheet, navigate_to_booking_page
from utils.date_utils import calculate_target_sunday, calculate_available_dates

class NavigationTest(BaseTestCase):
    """Test case for validating navigation and tee time slot finding"""
    
    def __init__(self):
        super().__init__("navigation_test")
        
    async def run(self):
        """Run the navigation test"""
        self.logger.info("Running navigation test")
        
        # Validate required configuration
        if not self.config["club_caddie_username"] or not self.config["club_caddie_password"]:
            self.logger.error("Missing Club Caddie credentials in environment variables")
            self.set_test_result(False, "Missing credentials in environment variables")
            return False
            
        # First, log in to the site
        self.logger.info("Logging in to Club Caddie")
        page, browser, playwright = await login_to_club_caddie()
        
        if not (page and browser and playwright):
            self.logger.error("Login failed")
            self.set_test_result(False, "Could not login to Club Caddie")
            return False
            
        # Set our test's page, browser, and playwright
        self.page = page
        self.browser = browser
        self.playwright = playwright
        
        # Test navigation to tee sheet
        self.logger.info("Testing navigation to tee sheet")
        success = await self._test_tee_sheet_navigation()
        if not success:
            return False
            
        # Test navigation to booking page
        self.logger.info("Testing navigation to booking page")
        success = await self._test_booking_page_navigation()
        if not success:
            return False
            
        # Test direct URL navigation
        self.logger.info("Testing direct URL navigation")
        success = await self._test_direct_url_navigation()
        if not success:
            return False
            
        # Test finding available slots
        self.logger.info("Testing finding available slots")
        success = await self._test_finding_slots()
        if not success:
            return False
            
        # Set test result
        self.set_test_result(True, "Navigation test completed successfully")
        return True
    
    async def _test_tee_sheet_navigation(self):
        """Test navigation to tee sheet"""
        step_id = "tee_sheet_navigation"
        self._add_step(step_id, "Testing navigation to tee sheet")
        
        try:
            # Use the navigate_to_tee_sheet function
            target_date = await navigate_to_tee_sheet(self.page)
            
            if not target_date:
                self.logger.error("Failed to navigate to tee sheet")
                self._update_step_status(step_id, "failed")
                return False
                
            # Verify we're on the tee sheet page
            current_url = self.page.url
            self.logger.info(f"Current URL: {current_url}")
            
            if "TeeSheet" not in current_url:
                self.logger.error("Not on tee sheet page after navigation")
                self._update_step_status(step_id, "failed", {
                    "current_url": current_url,
                    "target_date": target_date
                })
                return False
                
            # Take screenshot of tee sheet
            screenshot_path = await self._take_screenshot("tee_sheet")
            
            # Analyze tee sheet for key elements
            tee_sheet_data = await self._analyze_tee_sheet()
            
            self._update_step_status(step_id, "success", {
                "current_url": current_url,
                "target_date": target_date,
                "screenshot": screenshot_path,
                "tee_sheet_data": tee_sheet_data
            })
            
            # Check visibility and interactivity of key elements
            await self.debug_pause("On tee sheet page")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error testing tee sheet navigation: {str(e)}")
            self._add_error(step_id, f"Tee sheet navigation failed: {str(e)}")
            self._update_step_status(step_id, "failed")
            return False
            
    async def _test_booking_page_navigation(self):
        """Test navigation to booking page"""
        step_id = "booking_page_navigation"
        self._add_step(step_id, "Testing navigation to booking page")
        
        try:
            # Get target date (next Sunday or other available date)
            target_date = calculate_target_sunday()
            if not target_date:
                available_dates = calculate_available_dates()
                if not available_dates:
                    self.logger.error("No available dates within booking window")
                    self._update_step_status(step_id, "failed")
                    return False
                target_date = available_dates[-1]['date']
                
            self.logger.info(f"Using target date: {target_date}")
                
            # Use the navigate_to_booking_page function
            success = await navigate_to_booking_page(self.page, target_date)
            
            if not success:
                self.logger.error("Failed to navigate to booking page")
                self._update_step_status(step_id, "failed")
                return False
                
            # Verify we're on a booking-related page
            current_url = self.page.url
            self.logger.info(f"Current URL: {current_url}")
            
            # Take screenshot of booking page
            screenshot_path = await self._take_screenshot("booking_page")
            
            # Analyze booking page for key elements
            booking_page_data = await self._analyze_booking_page()
            
            self._update_step_status(step_id, "success", {
                "current_url": current_url,
                "target_date": target_date,
                "screenshot": screenshot_path,
                "booking_page_data": booking_page_data
            })
            
            # Check visibility and interactivity of key elements
            await self.debug_pause("On booking page")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error testing booking page navigation: {str(e)}")
            self._add_error(step_id, f"Booking page navigation failed: {str(e)}")
            self._update_step_status(step_id, "failed")
            return False
            
    async def _test_direct_url_navigation(self):
        """Test direct URL navigation to booking page"""
        step_id = "direct_url_navigation"
        self._add_step(step_id, "Testing direct URL navigation to booking page")
        
        try:
            # Calculate target date (7 days from today)
            today = datetime.now()
            target_date = (today + timedelta(days=7)).strftime("%Y-%m-%d")
            target_date_formatted = target_date.replace('-', '')
            
            # Direct booking URL
            booking_url = f"https://customer-cc36.clubcaddie.com/booking?date={target_date_formatted}"
            self.logger.info(f"Navigating directly to booking URL: {booking_url}")
            
            # Navigate to the URL
            await self.navigate(booking_url, "Navigating directly to booking URL")
            
            # Verify if we reached the booking page
            current_url = self.page.url
            self.logger.info(f"Current URL after direct navigation: {current_url}")
            
            # Wait for page to stabilize
            await asyncio.sleep(2)
            
            # Take screenshot of the result
            screenshot_path = await self._take_screenshot("direct_url_result")
            
            # Check if we're on a booking-related page
            booking_related = "booking" in current_url.lower()
            if not booking_related:
                self.logger.warning("Direct URL navigation may not have reached booking page")
                
            # Update step status
            self._update_step_status(step_id, "success" if booking_related else "warning", {
                "current_url": current_url,
                "target_date": target_date,
                "screenshot": screenshot_path,
                "booking_related": booking_related
            })
            
            # This test is informational, so return true even if navigation wasn't successful
            # We're trying to understand if direct URL is a viable approach
            return True
            
        except Exception as e:
            self.logger.error(f"Error testing direct URL navigation: {str(e)}")
            self._add_error(step_id, f"Direct URL navigation failed: {str(e)}")
            self._update_step_status(step_id, "failed")
            return False
            
    async def _test_finding_slots(self):
        """Test finding available tee time slots"""
        step_id = "find_slots"
        self._add_step(step_id, "Testing finding available tee time slots")
        
        try:
            # First navigate to booking page
            target_date = calculate_target_sunday()
            if not target_date:
                available_dates = calculate_available_dates()
                if not available_dates:
                    self.logger.error("No available dates within booking window")
                    self._update_step_status(step_id, "failed")
                    return False
                target_date = available_dates[-1]['date']
                
            await navigate_to_booking_page(self.page, target_date)
            
            # Search for time slots using our custom logic
            target_time = self.config["target_time"]
            self.logger.info(f"Searching for available slots near {target_time}")
            
            # Take screenshot before search
            await self._take_screenshot("before_slot_search")
            
            # Find available slots
            slots = await self._find_available_slots(target_time)
            
            if not slots:
                self.logger.warning("No available slots found")
                self._update_step_status(step_id, "warning", {
                    "slots_found": 0
                })
                return True  # Not finding slots isn't a critical failure
                
            self.logger.info(f"Found {len(slots)} available slots")
            
            # Take screenshots of each slot
            for i, slot in enumerate(slots[:5]):  # Limit to first 5 slots
                # Highlight the slot
                await self.page.evaluate("""(element) => {
                    const originalBackground = element.style.backgroundColor;
                    const originalBorder = element.style.border;
                    element.style.backgroundColor = 'rgba(255, 255, 0, 0.3)';
                    element.style.border = '2px solid red';
                    return { originalBackground, originalBorder };
                }""", slot["element"])
                
                # Take screenshot with highlight
                await self._take_screenshot(f"slot_{i+1}_highlight")
                
                # Remove highlight
                await self.page.evaluate("""(element, original) => {
                    element.style.backgroundColor = original.originalBackground;
                    element.style.border = original.originalBorder;
                }""", slot["element"], {"originalBackground": "", "originalBorder": ""})
            
            # Update step status
            self._update_step_status(step_id, "success", {
                "slots_found": len(slots),
                "slots": [{"time": s["time"], "distance": s["distance"]} for s in slots[:5]]
            })
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error testing slot finding: {str(e)}")
            self._add_error(step_id, f"Slot finding failed: {str(e)}")
            self._update_step_status(step_id, "failed")
            return False
            
    async def _analyze_tee_sheet(self):
        """Analyze tee sheet page structure"""
        try:
            # Extract key information from the tee sheet
            tee_sheet_info = await self.page.evaluate("""() => {
                // Get the date display
                const dateDisplay = document.querySelector('h1, h2, h3, [class*="date"], [id*="date"]');
                
                // Count total rows/slots
                const rows = document.querySelectorAll('tr');
                
                // Look for booking-related elements
                const bookingElements = document.querySelectorAll(
                    'a[href*="book"], button:not([disabled])[class*="book"], [onclick*="book"]'
                );
                
                return {
                    dateDisplayText: dateDisplay ? dateDisplay.innerText : null,
                    totalRows: rows.length,
                    bookingElementCount: bookingElements.length
                };
            }""")
            
            return tee_sheet_info
        except Exception as e:
            self.logger.error(f"Error analyzing tee sheet: {str(e)}")
            return {"error": str(e)}
            
    async def _analyze_booking_page(self):
        """Analyze booking page structure"""
        try:
            # Extract key information from the booking page
            booking_info = await self.page.evaluate("""() => {
                // Check for date selection elements
                const dateElements = document.querySelectorAll('[type="date"], [class*="date"], [class*="calendar"]');
                
                // Check for time selection elements
                const timeElements = document.querySelectorAll('[class*="time"], [id*="time"], [data-time]');
                
                // Check for player/golfer count elements
                const playerElements = document.querySelectorAll(
                    'select[name*="player"], select[name*="golfer"], input[name*="player"], input[name*="golfer"]'
                );
                
                return {
                    dateElementCount: dateElements.length,
                    timeElementCount: timeElements.length,
                    playerElementCount: playerElements.length,
                    pageTitle: document.title,
                    bodyText: document.body.innerText.substring(0, 200) + '...' // First 200 chars
                };
            }""")
            
            return booking_info
        except Exception as e:
            self.logger.error(f"Error analyzing booking page: {str(e)}")
            return {"error": str(e)}
            
    async def _find_available_slots(self, target_time):
        """Find available tee time slots"""
        import re
        from datetime import datetime
        
        # Helper function to parse time to minutes since midnight
        def parse_time_to_minutes(time_str):
            try:
                if ':' in time_str:
                    if 'am' in time_str.lower() or 'pm' in time_str.lower():
                        # 12-hour format
                        time_obj = datetime.strptime(time_str.strip(), "%I:%M %p")
                    else:
                        # 24-hour format
                        time_obj = datetime.strptime(time_str.strip(), "%H:%M")
                    return time_obj.hour * 60 + time_obj.minute
                return None
            except ValueError:
                return None
                
        try:
            # Parse target time to minutes
            if ':' in target_time:
                target_time_obj = datetime.strptime(target_time, "%H:%M")
                target_minutes = target_time_obj.hour * 60 + target_time_obj.minute
            else:
                target_minutes = int(target_time) * 60
                
            self.logger.info(f"Target time in minutes: {target_minutes}")
            
            # Find elements containing time text
            time_pattern = re.compile(r'\d{1,2}:\d{2}\s*[AP]M', re.IGNORECASE)
            
            # Strategy 1: Look for elements in a table structure
            time_elements = await self.page.evaluate(f"""() => {{
                const results = [];
                const allElements = Array.from(document.querySelectorAll('*'));
                const timeRegex = /{time_pattern.pattern}/i;
                
                for (const el of allElements) {{
                    if (el.childNodes.length > 0 && 
                        el.childNodes[0].nodeType === Node.TEXT_NODE &&
                        timeRegex.test(el.textContent)) {{
                            
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) {{  // Only visible elements
                            results.push({{
                                text: el.textContent.trim(),
                                tag: el.tagName,
                                classList: Array.from(el.classList),
                                isClickable: (
                                    el.tagName === 'A' || 
                                    el.tagName === 'BUTTON' || 
                                    el.getAttribute('onclick') ||
                                    el.getAttribute('role') === 'button' ||
                                    Array.from(el.classList).some(c => c.includes('click') || c.includes('slot'))
                                ),
                                boundingBox: {{
                                    x: rect.x,
                                    y: rect.y, 
                                    width: rect.width,
                                    height: rect.height
                                }}
                            }});
                        }}
                    }}
                }}
                return results;
            }}""")
            
            self.logger.info(f"Found {len(time_elements)} elements containing time text")
            
            # Filter for potential time slots
            available_slots = []
            
            for elem_info in time_elements:
                # Extract time from text
                match = time_pattern.search(elem_info["text"])
                if match:
                    time_text = match.group(0)
                    minutes = parse_time_to_minutes(time_text)
                    
                    if minutes is not None:
                        # Get the actual element
                        selector = f"//*/text()[contains(., '{time_text}')]/parent::*"
                        elements = await self.page.query_selector_all(selector)
                        
                        if elements:
                            element = elements[0]  # Use the first matching element
                            
                            # Calculate distance from target time
                            distance = abs(minutes - target_minutes)
                            
                            available_slots.append({
                                "element": element,
                                "time": time_text,
                                "minutes": minutes,
                                "distance": distance,
                                "info": elem_info
                            })
            
            # Sort by distance to target time
            available_slots.sort(key=lambda x: x["distance"])
            
            # Log the best options
            for i, slot in enumerate(available_slots[:5]):
                self.logger.info(f"Available slot {i+1}: {slot['time']} (distance: {slot['distance']} mins)")
            
            return available_slots
            
        except Exception as e:
            self.logger.error(f"Error finding available slots: {str(e)}")
            return []

async def main():
    """Run the navigation test"""
    test = NavigationTest()
    success = await run_test(test)
    print(f"Test {'successful' if success else 'failed'}")

if __name__ == "__main__":
    asyncio.run(main())

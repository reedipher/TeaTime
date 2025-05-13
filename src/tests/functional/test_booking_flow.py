"""
End-to-end booking flow test to validate the complete booking process
"""

import os
import sys
import asyncio
import json
import re
from datetime import datetime, timedelta

# Add parent directory to path so we can import our modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from tests.functional.test_base import BaseTestCase, run_test
from functions.auth import login_to_club_caddie
from functions.booking import navigate_to_tee_sheet, navigate_to_booking_page, book_tee_time
from utils.date_utils import calculate_target_sunday, calculate_available_dates

class BookingFlowTest(BaseTestCase):
    """Test case for validating end-to-end booking flow"""
    
    def __init__(self):
        super().__init__("booking_flow_test")
        
    async def run(self):
        """Run the booking flow test"""
        self.logger.info("Running booking flow test")
        
        # Force dry run mode regardless of environment setting
        original_dry_run = self.config["dry_run"]
        self.config["dry_run"] = True
        self.logger.info("Forced DRY RUN mode for booking flow test")
        
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
        
        # Get target date (next Sunday or other available date)
        target_date = calculate_target_sunday()
        if not target_date:
            available_dates = calculate_available_dates()
            if not available_dates:
                self.logger.error("No available dates within booking window")
                self.set_test_result(False, "No dates available within booking window")
                return False
            target_date = available_dates[-1]['date']
            
        self.logger.info(f"Using target date: {target_date}")
        
        # Set target time from config
        target_time = self.config["target_time"]
        player_count = self.config["player_count"]
        self.logger.info(f"Target time: {target_time}, Players: {player_count}")
        
        # 1. Test integrated booking flow
        try:
            self._add_step("integrated_booking", "Testing integrated booking flow")
            
            success = await book_tee_time(
                page, 
                target_date,
                target_time,
                player_count,
                dry_run=True
            )
            
            if success:
                self.logger.info("Integrated booking flow completed successfully")
                self._update_step_status("integrated_booking", "success")
            else:
                self.logger.error("Integrated booking flow failed")
                self._update_step_status("integrated_booking", "failed")
                self.set_test_result(False, "Integrated booking flow failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Error during integrated booking flow: {str(e)}")
            self._add_error("integrated_booking", f"Integrated booking flow error: {str(e)}")
            self._update_step_status("integrated_booking", "failed")
            self.set_test_result(False, f"Integrated booking flow error: {str(e)}")
            return False
        
        # 2. Test step-by-step booking flow
        self.logger.info("Testing step-by-step booking flow")
        
        # Navigate to booking page
        await self.debug_pause("Before navigating to booking page")
        await navigate_to_booking_page(self.page, target_date)
        
        # Find available slots
        await self.debug_pause("Before searching for slots")
        slot = await self._find_best_slot(target_time)
        
        if not slot:
            self.logger.warning("No available slots found for step-by-step test")
            self.set_test_result(False, "No available slots found for step-by-step test")
            return False
            
        self.logger.info(f"Found slot at {slot['time']} - attempting to book")
        
        # Try to book the slot
        await self.debug_pause("Before booking attempt")
        success = await self._attempt_booking(slot, player_count)
        
        if success:
            self.logger.info("Step-by-step booking flow completed successfully")
            self.set_test_result(True, "Booking flow test completed successfully")
            return True
        else:
            self.logger.error("Step-by-step booking flow failed")
            self.set_test_result(False, "Step-by-step booking flow failed")
            return False
        
    async def _find_best_slot(self, target_time):
        """Find the best available slot near the target time"""
        step_id = "find_slot"
        self._add_step(step_id, f"Finding available slot near {target_time}")
        
        try:
            # Take screenshot before search
            await self._take_screenshot("before_find_slot")
            
            # Parse target time to minutes
            if ':' in target_time:
                target_time_obj = datetime.strptime(target_time, "%H:%M")
                target_minutes = target_time_obj.hour * 60 + target_time_obj.minute
            else:
                target_minutes = int(target_time) * 60
                
            self.logger.info(f"Target time in minutes: {target_minutes}")
            
            # Record visible page content for debugging
            page_content = await self.page.evaluate("""() => {
                return {
                    title: document.title,
                    url: window.location.href,
                    bodyText: document.body.innerText.substring(0, 500) + '...'
                };
            }""")
            
            self.logger.info(f"Current page: {page_content['title']}, URL: {page_content['url']}")
            
            # Enhanced slot finding: Try multiple strategies
            
            # Strategy 1: Look for time pattern in clickable elements
            time_pattern = re.compile(r'\d{1,2}:\d{2}\s*[AP]M', re.IGNORECASE)
            slot_elements = await self.page.query_selector_all("a, button, [onclick], [class*='clickable'], [class*='slot']")
            
            slots = []
            for elem in slot_elements:
                try:
                    text = await elem.text_content()
                    if not text:
                        continue
                        
                    match = time_pattern.search(text)
                    if match:
                        time_text = match.group(0)
                        self.logger.info(f"Found slot with time: {time_text}")
                        
                        # Parse time
                        time_obj = self._parse_time(time_text)
                        if time_obj:
                            minutes = time_obj.hour * 60 + time_obj.minute
                            
                            # Check for availability indicators in text
                            is_likely_available = (
                                "book" in text.lower() or 
                                "reserve" in text.lower() or
                                "available" in text.lower() or
                                not any(x in text.lower() for x in ["booked", "taken", "unavailable", "reserved"])
                            )
                            
                            if is_likely_available:
                                slots.append({
                                    "element": elem,
                                    "time": time_text,
                                    "minutes": minutes,
                                    "distance": abs(minutes - target_minutes),
                                    "text": text
                                })
                except Exception as e:
                    self.logger.warning(f"Error processing element: {str(e)}")
                    continue
            
            # Sort by distance to target time
            slots.sort(key=lambda x: x["distance"])
            
            if slots:
                # Log the best options
                for i, slot in enumerate(slots[:3]):
                    self.logger.info(f"Slot option {i+1}: {slot['time']} (distance: {slot['distance']} mins)")
                    
                # Take screenshot with highlighted best slot
                best_slot = slots[0]
                await self.page.evaluate("""(element) => {
                    const originalBackground = element.style.backgroundColor;
                    const originalBorder = element.style.border;
                    element.style.backgroundColor = 'rgba(255, 255, 0, 0.3)';
                    element.style.border = '2px solid red';
                    return { originalBackground, originalBorder };
                }""", best_slot["element"])
                
                await self._take_screenshot("best_slot_highlight")
                
                self._update_step_status(step_id, "success", {
                    "slots_found": len(slots),
                    "best_slot": {
                        "time": best_slot["time"],
                        "distance_mins": best_slot["distance"]
                    }
                })
                
                # Return the best slot
                return best_slot
            else:
                self.logger.warning("No available slots found")
                await self._take_screenshot("no_slots_found")
                
                self._update_step_status(step_id, "warning", {
                    "slots_found": 0
                })
                return None
                
        except Exception as e:
            self.logger.error(f"Error finding best slot: {str(e)}")
            self._add_error(step_id, f"Slot finding failed: {str(e)}")
            self._update_step_status(step_id, "failed")
            await self._take_screenshot("slot_find_error")
            return None
            
    def _parse_time(self, time_str):
        """Parse a time string like '7:30 AM' into a time object"""
        time_str = time_str.strip()
        formats = [
            "%I:%M %p",  # 7:30 AM
            "%I:%M%p",   # 7:30AM
            "%H:%M"      # 14:30
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(time_str, fmt)
            except ValueError:
                continue
                
        return None
    
    async def _attempt_booking(self, slot, player_count):
        """Attempt to book a slot (in dry run mode)"""
        step_id = "attempt_booking"
        self._add_step(step_id, f"Attempting to book slot: {slot['time']} for {player_count} players (DRY RUN)")
        
        try:
            # Take screenshot before attempt
            await self._take_screenshot("before_booking_attempt")
            
            # Click on the slot element
            self.logger.info("Clicking on slot element")
            
            await slot["element"].click()
            await self.page.wait_for_load_state("networkidle")
            
            # Take screenshot after click
            await self._take_screenshot("after_slot_click")
            
            # Check for booking form/dialog/modal
            form_selectors = [
                "form", 
                "[role='dialog']", 
                "[class*='modal']",
                "[class*='booking']",
                "[class*='reservation']"
            ]
            
            form = None
            for selector in form_selectors:
                form = await self.page.query_selector(selector)
                if form:
                    self.logger.info(f"Found booking form using selector: {selector}")
                    break
                    
            if not form:
                self.logger.error("No booking form/dialog detected after clicking slot")
                self._update_step_status(step_id, "failed")
                return False
                
            # Log form structure
            form_html = await self.page.evaluate("(form) => form.outerHTML", form)
            self.logger.debug(f"Form HTML: {form_html[:200]}...")  # Log first 200 chars
            
            # Look for player count field
            player_selectors = [
                "select[name*='player']", 
                "select[name*='golfer']",
                "input[name*='player']",
                "input[name*='golfer']",
                "[class*='player'] select",
                "[class*='golfer'] select",
                "select",  # Fallback to any select
                "input[type='number']"  # Fallback to any number input
            ]
            
            player_field = None
            for selector in player_selectors:
                player_field = await form.query_selector(selector)
                if player_field:
                    self.logger.info(f"Found player count field using selector: {selector}")
                    break
                    
            if player_field:
                # Determine field type to handle appropriately
                tag_name = await player_field.evaluate("el => el.tagName.toLowerCase()")
                
                if tag_name == "select":
                    # It's a dropdown
                    options = await player_field.query_selector_all("option")
                    option_values = []
                    for opt in options:
                        value = await opt.get_attribute("value")
                        text = await opt.text_content()
                        option_values.append({"value": value, "text": text})
                        
                    self.logger.info(f"Select options: {json.dumps(option_values)}")
                    
                    # Find option closest to player_count
                    best_option = None
                    for opt in option_values:
                        try:
                            opt_val = int(opt["value"])
                            if best_option is None or abs(opt_val - player_count) < abs(int(best_option["value"]) - player_count):
                                best_option = opt
                        except (ValueError, TypeError):
                            continue
                            
                    if best_option:
                        self.logger.info(f"Selecting option: {best_option['value']} ({best_option['text']})")
                        await player_field.select_option(value=best_option["value"])
                    else:
                        # Just try with string value of player_count
                        await player_field.select_option(value=str(player_count))
                        
                else:
                    # It's likely an input field
                    self.logger.info(f"Setting input field to {player_count}")
                    await player_field.fill(str(player_count))
                
                # Take screenshot after setting player count
                await self._take_screenshot("after_set_player_count")
            else:
                self.logger.warning("No player count field found")
            
            # Look for the booking button
            button_selectors = [
                "button:text('Book')", 
                "button:text('Reserve')",
                "button:text('Continue')",
                "button:text('Submit')",
                "button[type='submit']",
                "[class*='book'] button",
                "[class*='submit'] button",
                "input[type='submit']"
            ]
            
            book_button = None
            for selector in button_selectors:
                try:
                    book_button = await form.wait_for_selector(selector, timeout=1000)
                    if book_button:
                        self.logger.info(f"Found booking button using selector: {selector}")
                        break
                except:
                    continue
                    
            if not book_button:
                self.logger.warning("No booking button found, looking for any button in form")
                buttons = await form.query_selector_all("button")
                if buttons:
                    # Use the last button as it's often the submit button
                    book_button = buttons[-1]
            
            if book_button:
                # In DRY RUN mode, don't actually click the button
                button_text = await book_button.text_content()
                self.logger.info(f"Found booking button with text: '{button_text}' - WOULD CLICK IN LIVE MODE")
                
                # Take screenshot showing the button we would click
                await self.page.evaluate("""(element) => {
                    const originalBackground = element.style.backgroundColor;
                    const originalBorder = element.style.border;
                    element.style.backgroundColor = 'rgba(0, 255, 0, 0.3)';
                    element.style.border = '2px solid green';
                    element.style.boxShadow = '0 0 10px green';
                    return { originalBackground, originalBorder };
                }""", book_button)
                
                await self._take_screenshot("would_click_book_button")
                
                self._update_step_status(step_id, "success", {
                    "found_form": True,
                    "found_player_field": player_field is not None,
                    "found_book_button": True,
                    "button_text": button_text,
                    "dry_run": True
                })
                
                return True
            else:
                self.logger.error("No booking button found")
                await self._take_screenshot("no_book_button")
                
                self._update_step_status(step_id, "failed", {
                    "found_form": True,
                    "found_player_field": player_field is not None,
                    "found_book_button": False
                })
                
                return False
                
        except Exception as e:
            self.logger.error(f"Error attempting booking: {str(e)}")
            self._add_error(step_id, f"Booking attempt failed: {str(e)}")
            self._update_step_status(step_id, "failed")
            await self._take_screenshot("booking_attempt_error")
            return False

async def main():
    """Run the booking flow test"""
    test = BookingFlowTest()
    success = await run_test(test)
    print(f"Test {'successful' if success else 'failed'}")

if __name__ == "__main__":
    asyncio.run(main())

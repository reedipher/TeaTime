# src/functions/booking.py
import asyncio
import logging
import re
import json
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

# Import utilities
from src.utils.screenshot import take_screenshot, take_detailed_screenshot, debug_interactive
from src.utils.date_utils import calculate_target_day, calculate_available_dates
from src.utils.config_loader import get_value, get_booking_config, get_runtime_config, get_debug_config

# Set up logger
logger = logging.getLogger("teatime")

async def wait_for_element_with_retry(page, selector, timeout=10000, retries=3):
    """
    Wait for an element with retries
    
    Args:
        page: Playwright page object
        selector: Selector to wait for
        timeout: Timeout in ms for each attempt
        retries: Number of retry attempts
        
    Returns:
        element or None: The found element or None if not found
    """
    for attempt in range(retries):
        try:
            element = await page.wait_for_selector(selector, timeout=timeout)
            return element
        except Exception as e:
            if attempt == retries - 1:
                logger.error(f"Failed to find element {selector} after {retries} attempts: {str(e)}")
                return None
            logger.info(f"Retry {attempt+1}/{retries} waiting for {selector}")
            await asyncio.sleep(1)

async def navigate_to_tee_sheet(page, target_date=None):
    """
    Navigate to the tee sheet for the specified date
    
    Args:
        page: Playwright page object
        target_date: Date string in YYYY-MM-DD format, defaults to calculated target Sunday
        
    Returns:
        str: The target date used
    """
    if target_date is None:
        # Get the next target day within the booking window
        booking_window_days = get_value("system", "booking_window_days", 7)
        target_date = calculate_target_day(max_days_ahead=booking_window_days)
        target_day_name = get_value("booking", "target_day", "Sunday")  # Get the name for logging
        
        # If no target day is available within the booking window, show all available dates
        if not target_date:
            available_dates = calculate_available_dates()
            logger.info(f"No {target_day_name} available within booking window. Available dates:")
            for date_info in available_dates:
                logger.info(f"{date_info['date']} ({date_info['weekday']}) - {date_info['days_ahead']} days ahead")
            
            # Default to the furthest available date
            target_date = available_dates[-1]['date']
            logger.info(f"Defaulting to furthest available date: {target_date}")
    
    tee_sheet_url = f"https://customer-cc36.clubcaddie.com/TeeSheet/view/cbfdabab/sheet?date={target_date}"
    logger.info(f"Navigating to tee sheet for date: {target_date}")
    logger.info(f"URL: {tee_sheet_url}")
    
    try:
        await page.goto(tee_sheet_url)
        await page.wait_for_load_state("domcontentloaded") # faster than networkidle
    
        logger.info(f"Current URL: {page.url}")
        await take_screenshot(page, "tee_sheet")
    except Exception as e:
        logger.error(f"Error navigating to tee sheet: {str(e)}")
        await take_screenshot(page, "navigation_error")
        raise
    
    return target_date

async def navigate_to_booking_page(page, target_date):
    """
    Navigate to the booking page and set the correct date
    
    Args:
        page: Playwright page object
        target_date: Date string in YYYY-MM-DD format
    """
    # Format date for different uses
    try:
        date_obj = datetime.strptime(target_date, "%Y-%m-%d")
        mm_dd_yyyy = date_obj.strftime("%m/%d/%Y")
        yyyymmdd = date_obj.strftime("%Y%m%d")
    except Exception as e:
        logger.warning(f"Error formatting date {target_date}: {e} - using as provided")
        yyyymmdd = target_date.replace('-', '')
        mm_dd_yyyy = target_date  # Best effort
    try:
        # Try direct navigation to booking URL with correct path structure
        formatted_date = target_date.replace('-', '')  # Remove dashes for URL
        
        # Use the fully correct URL structure with proper date formatting and parameters
        # Format date as MM/DD/YYYY for URL
        try:
            date_obj = datetime.strptime(target_date, "%Y-%m-%d")
            mm_dd_yyyy = date_obj.strftime("%m/%d/%Y")
            # URL encode the slashes
            url_date = mm_dd_yyyy.replace("/", "%2F") 
        except Exception as e:
            logger.warning(f"Error formatting date {target_date}: {e} - using fallback format")
            url_date = formatted_date
            
        direct_booking_url = f"https://customer-cc36.clubcaddie.com/TeeTimes/view/cbfdabab/slots?date={url_date}&player=1&ratetype=any"
        logger.info(f"Trying direct booking URL: {direct_booking_url}")
        
        await page.goto(direct_booking_url)
        await page.wait_for_load_state("domcontentloaded") # faster than networkidle
        await take_detailed_screenshot(page, "direct_booking_url")
        
        # Check if we reached the booking page
        if "TeeTimes" in page.url:
            # Log page details to debug date issues
            page_info = await page.evaluate("""
                () => {
                    return {
                        url: window.location.href,
                        title: document.title,
                        elementCounts: {
                            buttons: document.querySelectorAll('button').length,
                            links: document.querySelectorAll('a').length,
                            forms: document.querySelectorAll('form').length,
                            inputs: document.querySelectorAll('input').length,
                            selects: document.querySelectorAll('select').length
                        }
                    };
                }
            """)
            logger.info(f"Page info for direct_booking_url: {json.dumps(page_info)}")
            
            # Store the HTML content using absolute paths
            html_content = await page.content()
            import os
            from pathlib import Path
            # Get the project root directory
            project_root = Path(__file__).parents[2].absolute()
            html_dir = project_root / "artifacts" / "html"
            os.makedirs(html_dir, exist_ok=True)
            html_path = html_dir / "direct_booking_url.html"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            logger.info(f"HTML content saved to {html_path}")
            
            # We already have the correct date in the URL, no need to set it again
            logger.info("Using date from URL parameter - skipping date input field manipulation")
            
            logger.info("Direct booking URL successful")
            return True
            
        # If the first structure failed, try the alternate URL format
        alternate_booking_url = f"https://customer-cc36.clubcaddie.com/TeeTimes/booking/cbfdabab/slots?date={url_date}&player=1&ratetype=any"
        logger.info(f"Trying alternate booking URL: {alternate_booking_url}")
        
        await page.goto(alternate_booking_url)
        await page.wait_for_load_state("domcontentloaded") # faster than networkidle
        await take_detailed_screenshot(page, "alternate_booking_url")
        
        if "TeeTimes" in page.url:
            logger.info("Alternate booking URL successful")
            return True
        
    except Exception as e:
        logger.info(f"Direct URL failed, falling back to UI navigation: {str(e)}")
    
    # Fall back to UI navigation through the tee sheet
    try:
        # First navigate to the tee sheet
        await navigate_to_tee_sheet(page, target_date)
        await take_detailed_screenshot(page, "tee_sheet_before_booking_nav")
        
        # Look for "Book a Member Tee Time" in the sidebar
        logger.info("Looking for 'Book a Member Tee Time' link in sidebar")
        
        # Find the booking link by looking for specific text
        links = await page.query_selector_all("a")
        booking_link = None
        for link in links:
            link_text = await link.text_content()
            if "Book a Member Tee Time" in link_text:
                booking_link = link
                break
        if booking_link:
            logger.info("Found 'Book a Member Tee Time' link, clicking to access booking page...")
            await booking_link.click()
            await page.wait_for_load_state("domcontentloaded") # faster than networkidle
            await take_screenshot(page, "after_booking_link")
            return True
        else:
            logger.warning("'Book a Member Tee Time' link not found in sidebar")
            
        # Try clicking on an available tee time directly from the tee sheet
        logger.info("Looking for bookable tee time slots")
        forms = await page.query_selector_all("form[action*='TeeTimes/booking']")
        if forms:
            logger.info(f"Found {len(forms)} booking forms on tee sheet")
            # Click the submit button on the first form
            submit_btn = await forms[0].query_selector("button[type='submit'], input[type='submit']")
            if submit_btn:
                await submit_btn.click()
                await page.wait_for_load_state("domcontentloaded") # faster than networkidle
                await take_screenshot(page, "after_form_submit")
                return True
            else:
                logger.info("No submit button found, trying to submit the form directly")
                await page.evaluate("document.getElementById('TeeSheetForm0').submit()")
                await page.wait_for_load_state("domcontentloaded") # faster than networkidle
                await take_screenshot(page, "after_form_submit_js")
                return True
    except Exception as e:
        logger.error(f"Error navigating to booking page: {str(e)}")
        await take_screenshot(page, "booking_nav_error")
    
    return False

async def parse_time(time_str):
    """
    Parse a time string like '7:30 AM' into minutes since midnight
    
    Args:
        time_str: Time string in format like '7:30 AM'
        
    Returns:
        int: Minutes since midnight
    """
    try:
        # Handle various formats and clean the string
        time_str = time_str.strip()
        
        # Try with a space between time and AM/PM
        try:
            time_obj = datetime.strptime(time_str, "%I:%M %p")
            return time_obj.hour * 60 + time_obj.minute
        except ValueError:
            pass
            
        # Try without space between time and AM/PM
        try:
            time_obj = datetime.strptime(time_str, "%I:%M%p")
            return time_obj.hour * 60 + time_obj.minute
        except ValueError:
            pass
            
        # Try 24-hour format
        try:
            time_obj = datetime.strptime(time_str, "%H:%M")
            return time_obj.hour * 60 + time_obj.minute
        except ValueError:
            pass
        
        # Try special format without separation
        if re.match(r'^\d{1,2}\:\d{2}(AM|PM|am|pm)$', time_str):
            # Extract components
            hour_min = time_str[:-2]
            period = time_str[-2:].upper()
            # Reconstruct with space
            fixed_time = f"{hour_min} {period}"
            try:
                time_obj = datetime.strptime(fixed_time, "%I:%M %p")
                return time_obj.hour * 60 + time_obj.minute
            except ValueError:
                pass
        
        logger.warning(f"Could not parse time: {time_str}")
        return None
    except Exception as e:
        logger.error(f"Error parsing time '{time_str}': {str(e)}")
        return None

async def search_for_available_slots(page, target_time="14:00"):
    """
    Search for available tee time slots on the booking page
    
    Args:
        page: Playwright page object
        target_time: Target time string in HH:MM format
        
    Returns:
        dict: Information about the selected tee time or None if not found
    """
    # Helper function to extract times from elements
    async def extract_time_info(element):
        text = await element.text_content()
        time_match = time_pattern.search(text)
        if time_match:
            time_text = time_match.group(0)
            minutes = await parse_time(time_text)
            return {
                'element': element,
                'time': time_text,
                'minutes': minutes,
                'full_text': text.strip(),
                'distance': abs(minutes - target_minutes) if minutes else 9999
            }
        return None

    logger.info(f"Searching for available slots near {target_time}...")
    target_time_obj = datetime.strptime(target_time, "%H:%M")
    target_minutes = target_time_obj.hour * 60 + target_time_obj.minute
    logger.info(f"Target time in minutes: {target_minutes}")
    
    # Quick screenshot and debug - optimized for performance
    await take_screenshot(page, "before_slot_search")
    await debug_interactive(page, "Before searching for slots")
    
    try:
        # Look for time patterns like "2:00 PM"
        time_pattern = re.compile(r'\d{1,2}:\d{2}\s*[AP]M', re.IGNORECASE)
        
        # Strategy 1: Look for time slots in a table structure
        rows = await page.query_selector_all("tr")
        logger.info(f"Found {len(rows)} table rows to check")
        
        available_slots = []
        
        for i, row in enumerate(rows):
            text = await row.text_content()
            time_match = time_pattern.search(text)
            
            if time_match:
                time_text = time_match.group(0)
                minutes = await parse_time(time_text)
                logger.info(f"Row {i+1} contains time: {time_text} ({minutes} minutes)")
                
                # Check if this row appears to be an available slot (not booked)
                # Use a simpler check - faster performance
                book_elements = await row.query_selector_all('button, a')
                text = await row.text_content()
                is_available = (len(book_elements) > 0) or ("Available" in text or "Book" in text)
                
                if is_available:
                    # This row might contain an available slot
                    logger.info(f"Row {i+1} appears to be available")
                    
                    # Look for booking links or buttons in this row
                    book_elements = await row.query_selector_all("button, a")
                    if book_elements:
                        for j, btn in enumerate(book_elements):
                            btn_text = await btn.text_content()
                            logger.info(f"Potential booking element {j+1} in row {i+1}: '{btn_text}'")
                        
                        # Use the first button/link as the booking element
                        booking_element = book_elements[0]
                    else:
                        # If no buttons found, use the row itself
                        booking_element = row
                    
                    available_slots.append({
                        'element': booking_element,
                        'row': row,
                        'time': time_text,
                        'minutes': minutes,
                        'distance': abs(minutes - target_minutes)
                    })
        
        if not available_slots:
            # Strategy 2: Look for any clickable elements containing time text
            logger.info("No table slots found, checking for any clickable elements with times")
            all_elements = await page.query_selector_all("a, button, [onclick], [class*='clickable'], [class*='slot'], [role='button']")
            
            for i, elem in enumerate(all_elements):
                time_info = await extract_time_info(elem)
                if time_info:
                    logger.info(f"Found clickable element {i+1} with time {time_info['time']}")
                    available_slots.append(time_info)
        
        if available_slots:
            # Sort by distance to target time
            available_slots.sort(key=lambda x: x['distance'])
            
            # Log the best options
            for i, slot in enumerate(available_slots[:5]):
                logger.info(f"Available slot {i+1}: {slot['time']} (distance: {slot['distance']} mins)")
            
            # Return the closest match to target time
            return available_slots[0]
        else:
            logger.info("No available slots found that match our criteria")
            return None
            
    except Exception as e:
        logger.error(f"Error searching for available slots: {str(e)}")
        await take_screenshot(page, "slot_search_error")
        return None

async def attempt_booking(page, slot_info, player_count=4, dry_run=True):
    """
    Attempt to book the selected tee time slot
    
    Args:
        page: Playwright page object
        slot_info: Information about the selected tee time slot
        player_count: Number of players to book
        dry_run: If True, simulate booking without completing
        
    Returns:
        bool: Whether the booking attempt was successful
    """
    logger.info(f"Attempting to book slot: {slot_info['time']} for {player_count} players")
    logger.info(f"Mode: {'DRY RUN' if dry_run else 'LIVE BOOKING'}")
    await take_detailed_screenshot(page, "before_booking_attempt")
    
    # Enable interactive debugging if configured
    await debug_interactive(page, "Before booking attempt")
    
    try:
        # Check if this is a form element or a button
        if 'form_id' in slot_info:
            # It's a form, so we should submit it
            form_id = slot_info['form_id']
            logger.info(f"Booking using form submission for form: {form_id}")
            
            if dry_run:
                logger.info("DRY RUN: Would submit the booking form here")
                # Highlight the form to show which one would be submitted
                await page.evaluate(f"document.getElementById('{form_id}').style.border = '2px solid red'")
                await take_detailed_screenshot(page, "would_submit_form")
                return True
            else:
                # Submit the form
                await page.evaluate(f"document.getElementById('{form_id}').submit()")
                await page.wait_for_load_state("domcontentloaded") # faster than networkidle
                await take_detailed_screenshot(page, "after_form_submit")
        else:
            # It's a regular element, click on it
            element = slot_info['element']
            logger.info("Clicking on booking element")
            
            try:
                # Check if element is still attached to DOM
                await element.evaluate("el => el.isConnected")
                
                if dry_run:
                    logger.info("DRY RUN: Would click booking element here")
                    # Highlight the element to show which one would be clicked
                    await page.evaluate("""(element) => {
                        const originalBackground = element.style.backgroundColor;
                        const originalBorder = element.style.border;
                        element.style.backgroundColor = 'rgba(255, 0, 0, 0.3)';
                        element.style.border = '2px solid red';
                        return { originalBackground, originalBorder };
                    }""", element)
                    await take_detailed_screenshot(page, "would_click_element")
                    return True
                else:
                    await element.click()
            except Exception as e:
                logger.warning(f"Error accessing booking element: {str(e)}")
                return False
                
        # After form submission or element click, look for the booking form
        await page.wait_for_load_state("domcontentloaded") # faster than networkidle
        await take_detailed_screenshot(page, "after_booking_action")
        
        # Wait a moment for any modal dialogs to appear
        await asyncio.sleep(1)
        
        # Now handle the booking form process
        form = await page.query_selector("form, [role='dialog'], [class*='modal']")
        if form:
            logger.info("Booking form detected")
            
            # Look for player count selection
            player_selector = await form.query_selector("select, [class*='player'], input[type='number']")
            if player_selector:
                logger.info(f"Setting player count to {player_count}")
                
                # Handle different types of player count inputs
                tag_name = await player_selector.get_property("tagName")
                tag_name = await tag_name.json_value()
                
                if not dry_run:
                    if tag_name.lower() == "select":
                        # It's a dropdown
                        await player_selector.select_option(value=str(player_count))
                    else:
                        # It's likely an input field
                        await player_selector.fill(str(player_count))
                
                await take_screenshot(page, "player_count_set")
            
            if dry_run:
                logger.info("DRY RUN: Would complete booking here")
                return True
            
            # Look for the final booking button
            book_button = await form.query_selector("button[type='submit'], [type='submit']")
            if not book_button:
                # Find button by text
                buttons = await form.query_selector_all("button")
                for btn in buttons:
                    btn_text = await btn.text_content()
                    if "book" in btn_text.lower() or "reserve" in btn_text.lower() or "submit" in btn_text.lower():
                        book_button = btn
                        break
            if book_button:
                logger.info("Clicking final booking button")
                await book_button.click()
                await page.wait_for_load_state("domcontentloaded") # faster than networkidle
                await take_screenshot(page, "booking_complete")
                
                # Look for confirmation
                confirmation = await page.query_selector("[class*='success'], [class*='confirmation']")
                if confirmation:
                    confirmation_text = await confirmation.text_content()
                    logger.info(f"Booking confirmation: {confirmation_text.strip()}")
                    return True
                else:
                    logger.warning("No confirmation element found, but booking may still be successful")
                    return True
            else:
                logger.warning("No final booking button found")
                return False
        else:
            logger.warning("No booking form detected after action")
            return False
            
    except Exception as e:
        logger.error(f"Error during booking attempt: {str(e)}")
        await take_screenshot(page, "booking_error")
        return False

async def find_tee_time_slots_on_tee_sheet(page, target_time="14:00"):
    """
    Find available tee time slots on either the tee sheet or booking page view
    
    Args:
        page: Playwright page object
        target_time: Target time string in HH:MM format
        
    Returns:
        list: List of available slots with details, sorted by proximity to target time
    """
    logger.info(f"Searching for tee time slots near {target_time}...")
    target_time_obj = datetime.strptime(target_time, "%H:%M")
    target_minutes = target_time_obj.hour * 60 + target_time_obj.minute
    
    # Take detailed screenshot for debugging
    await take_detailed_screenshot(page, "tee_sheet_slots_search")
    
    # Enable interactive debugging if configured
    await debug_interactive(page, "Before searching for tee time slots")
    
    # Add additional wait time for page to fully load, especially for booking view
    if "TeeTimes" in page.url:
        logger.info("Booking view detected - adding extra wait time for page to stabilize")
        await asyncio.sleep(2)  # Give booking page extra time to load completely
        
        # Wait for key elements that indicate the page is ready
        try:
            await page.wait_for_selector(".teetime-card, .time-slot, [class*='time'], [class*='slot'], [role='button'], tr, button", timeout=5000)
            logger.info("Key page elements found, page appears to be ready")
        except Exception as e:
            logger.warning(f"Timed out waiting for key elements, but will attempt to find slots anyway: {str(e)}")
    
    # Determine which view we're on (tee sheet or booking page)
    current_url = page.url
    is_booking_view = "TeeTimes/view" in current_url or "TeeTimes/booking" in current_url
    is_tee_sheet_view = "TeeSheet/view" in current_url
    
    logger.info(f"Detected view: {'Booking View' if is_booking_view else 'Tee Sheet View' if is_tee_sheet_view else 'Unknown View'}")
    
    # Capture the HTML structure for better diagnostics
    html_structure = await page.evaluate("""
    () => {
        // Create a simple HTML element counter
        const getElementCounts = () => {
            return {
                forms: document.querySelectorAll('form').length,
                buttons: document.querySelectorAll('button').length,
                links: document.querySelectorAll('a').length,
                tables: document.querySelectorAll('table').length,
                trs: document.querySelectorAll('tr').length,
                divs: document.querySelectorAll('div').length
            };
        };
        
        // Check for common time/slot related elements
        const getTimeElementInfo = () => {
            const timeElements = {
                timeCards: document.querySelectorAll('[class*="time"]').length,
                slotElements: document.querySelectorAll('[class*="slot"]').length,
                teeTimeElements: document.querySelectorAll('[class*="tee-time"]').length,
                bookingElements: document.querySelectorAll('button, a').length
            };
            return timeElements;
        };
        
        return {
            url: window.location.href,
            title: document.title,
            elementCounts: getElementCounts(),
            timeElements: getTimeElementInfo()
        };
    }
    """)
    
    logger.info(f"Page structure: {json.dumps(html_structure)}")
    
    available_slots = []
    time_pattern = re.compile(r'\d{1,2}:\d{2}\s*[AP]M', re.IGNORECASE)
    
    try:
        if is_tee_sheet_view:
            # ===== TEE SHEET VIEW LOGIC =====
            # Extract the form data which contains the tee time information
            forms = await page.query_selector_all("form[id*='TeeSheetForm']")
            logger.info(f"Found {len(forms)} tee time forms")
            
            for i, form in enumerate(forms):
                # Extract time from the form
                time_elem = await form.query_selector(".slotTime b")
                if time_elem:
                    time_text = await time_elem.text_content()
                    time_text = time_text.strip()
                    minutes = await parse_time(time_text)
                    logger.info(f"Form {i+1} contains time: {time_text}")
                    
                    # Check if this slot is available by looking for green boxes without names
                    # or any booking elements
                    
                    # Method 1: Check for forms that allow submission (these should be bookable)
                    is_bookable = await form.evaluate("""form => {
                        // Check for "Book" buttons in the form
                        const bookButton = form.querySelector('button[type="submit"], [type="submit"]');
                        const bookTextButton = Array.from(form.querySelectorAll('button')).find(btn => 
                            btn.textContent.toLowerCase().includes('book') || btn.textContent.toLowerCase().includes('reserve')
                        );
                        
                        if (bookButton || bookTextButton) return true;
                        
                        // Check slot status - non-green might be available
                        const slots = Array.from(form.querySelectorAll('.slot-box'));
                        const availableSlots = slots.filter(slot => 
                            !slot.classList.contains('Green') &&
                            !slot.classList.contains('Grey') &&
                            !slot.classList.contains('Event') &&
                            !slot.textContent.trim() // Empty slots are potentially available
                        );
                        
                        return availableSlots.length > 0;
                    }""")
                    
                    if is_bookable:
                        logger.info(f"Form {i+1} with time {time_text} appears to be bookable")
                        
                        # Set up the slot data
                        available_slots.append({
                            'element': form,  # Use the form itself as the element to click
                            'time': time_text,
                            'minutes': minutes,
                            'distance': abs(minutes - target_minutes) if minutes else 9999,
                            'form_id': await form.get_attribute('id')
                        })
                    else:
                        logger.debug(f"Form {i+1} with time {time_text} doesn't appear to be bookable")
        
        elif is_booking_view:
            # ===== BOOKING VIEW LOGIC =====
            logger.info("Detecting slots in booking view")
            
            # Attempt to wait for content to fully render (account for any AJAX content)
            try:
                # Look for any interactive elements or time displays
                await page.wait_for_selector(
                    ".teetime-card, .time-slot, [class*='time'], [class*='slot'], button:visible", 
                    timeout=5000,
                    state="visible"  # Wait until elements are visible, not just in DOM
                )
                logger.info("Interactive elements appear to be loaded")
            except Exception as e:
                logger.warning(f"Waiting for interactive elements timed out: {str(e)}")
                # Continue anyway - will try alternative approaches
            
            # Strategy 1: Look for time cards/panels that have booking elements
            time_cards = await page.query_selector_all(".teetime-card, .time-slot, [class*='time'], [class*='slot'], [class*='tee-time']")
            logger.info(f"Found {len(time_cards)} potential time cards/panels")
            
            for i, card in enumerate(time_cards):
                card_text = await card.text_content()
                time_match = time_pattern.search(card_text)
                
                if time_match:
                    time_text = time_match.group(0)
                    minutes = await parse_time(time_text)
                    logger.info(f"Time card {i+1} contains time: {time_text}")
                    
                    # Check if bookable by looking for book buttons or indicators
                    book_button = await card.query_selector("button, a")
                    if book_button:
                        button_text = await book_button.text_content()
                        logger.info(f"Found potential booking button with text: {button_text}")
                        
                        is_bookable = "book" in button_text.lower() or "reserve" in button_text.lower()
                        if is_bookable:
                            logger.info(f"Time card with time {time_text} appears to be bookable")
                            available_slots.append({
                                'element': book_button,
                                'time': time_text,
                                'minutes': minutes,
                                'distance': abs(minutes - target_minutes) if minutes else 9999,
                                'is_button': True
                            })
            
            # Strategy 2: Look for time texts that are near booking buttons
            if not available_slots:
                logger.info("No slots found with card approach, trying button-based approach")
                book_buttons = await page.query_selector_all("button, a")
                
                for i, button in enumerate(book_buttons):
                    button_text = await button.text_content()
                    
                    if "book" in button_text.lower() or "reserve" in button_text.lower():
                        logger.info(f"Found booking button {i+1}")
                        
                        # Look for time near this button - check parent containers
                        time_text = await button.evaluate("""btn => {
                            // Try to find the time in the parent containers
                            let parent = btn.parentElement;
                            let maxDepth = 5; // Don't go too far up the tree
                            let timeRegex = /\\d{1,2}:\\d{2}\\s*[AP]M/i;
                            
                            while (parent && maxDepth > 0) {
                                if (parent.textContent.match(timeRegex)) {
                                    const match = parent.textContent.match(timeRegex);
                                    return match ? match[0].trim() : null;
                                }
                                parent = parent.parentElement;
                                maxDepth--;
                            }
                            return null;
                        }""")
                        
                        if time_text:
                            minutes = await parse_time(time_text)
                            logger.info(f"Button {i+1} associated with time: {time_text}")
                            
                            available_slots.append({
                                'element': button,
                                'time': time_text,
                                'minutes': minutes,
                                'distance': abs(minutes - target_minutes) if minutes else 9999,
                                'is_button': True
                            })
                
                # Strategy 3: Look for any clickable elements that have time text
                if not available_slots:
                    logger.info("No slots found with button approach, trying general element approach")
                    all_elements = await page.query_selector_all("a, button, [onclick], [class*='clickable'], [class*='slot'], [role='button']")
                    
                    for i, elem in enumerate(all_elements):
                        elem_text = await elem.text_content()
                        time_match = time_pattern.search(elem_text)
                        
                        if time_match:
                            time_text = time_match.group(0)
                            minutes = await parse_time(time_text)
                            
                            # Check if this element appears to be a booking element
                            is_likely_booking = (
                                "book" in elem_text.lower() or
                                "reserve" in elem_text.lower() or
                                "select" in elem_text.lower() or
                                "available" in elem_text.lower()
                            )
                            
                            if is_likely_booking:
                                logger.info(f"Element {i+1} with time {time_text} appears to be bookable")
                                available_slots.append({
                                    'element': elem,
                                    'time': time_text,
                                    'minutes': minutes,
                                    'distance': abs(minutes - target_minutes) if minutes else 9999,
                                })
        else:
            # Generic approach for unknown view
            logger.info("Unknown view type, using generic slot detection approach")
            # Try the fallback method from original code
            book_buttons = await page.query_selector_all("button, a")
            book_buttons = [
                btn for btn in book_buttons 
                if await btn.evaluate("el => el.textContent.toLowerCase().includes('book')")
            ]
            
            if book_buttons:
                logger.info(f"Found {len(book_buttons)} potential 'Book' buttons")
                
                # For each booking button, try to find the associated time
                for i, button in enumerate(book_buttons):
                    # Look at parent containers to find the time
                    time_text = await button.evaluate("""btn => {
                        // Try to find the time in the parent containers
                        let parent = btn.parentElement;
                        let maxDepth = 5; // Don't go too far up the tree
                        let timeRegex = /\\d{1,2}:\\d{2}\\s*[AP]M/i;
                        
                        while (parent && maxDepth > 0) {
                            if (parent.textContent.match(timeRegex)) {
                                const match = parent.textContent.match(timeRegex);
                                return match ? match[0].trim() : null;
                            }
                            parent = parent.parentElement;
                            maxDepth--;
                        }
                        return null;
                    }""")
                    
                    if time_text:
                        minutes = await parse_time(time_text)
                        logger.info(f"Button {i+1} associated with time: {time_text}")
                        
                        available_slots.append({
                            'element': button,
                            'time': time_text,
                            'minutes': minutes,
                            'distance': abs(minutes - target_minutes) if minutes else 9999,
                            'is_button': True
                        })
        
        # Sort and return if we found any slots
        if available_slots:
            available_slots.sort(key=lambda x: x['distance'])
            
            for i, slot in enumerate(available_slots[:5]):
                logger.info(f"Available slot {i+1}: {slot['time']} (distance from target: {slot['distance']} mins)")
            
            return available_slots
            
        logger.warning("No available tee time slots found on the page")
        return []
        
    except Exception as e:
        logger.error(f"Error finding tee time slots: {str(e)}")
        await take_screenshot(page, "find_slots_error")
        return []

async def book_tee_time(page, target_date, target_time=None, player_count=None, dry_run=None, max_retries=None):
    # Get configuration values if not specified
    if target_time is None:
        target_time = get_value("booking", "target_time", "14:00")
    if player_count is None:
        player_count = get_value("booking", "player_count", 4)
    if dry_run is None:
        dry_run = get_value("runtime", "dry_run", True)
    if max_retries is None:
        max_retries = get_value("runtime", "max_retries", 2)
    """
    Complete tee time booking process with retry logic
    
    Args:
        page: Playwright page object
        target_date: Target date in YYYY-MM-DD format
        target_time: Target time in HH:MM format
        player_count: Number of players to book
        dry_run: If True, simulate booking without completing
        max_retries: Maximum number of retry attempts
        
    Returns:
        bool: Whether the booking was successful
    """
    for attempt in range(max_retries + 1):
        try:
            logger.info(f"Booking attempt {attempt + 1} of {max_retries + 1}")
            
            # Always start with the tee sheet - this is the most reliable approach
            logger.info("Navigating to tee sheet page as starting point")
            await navigate_to_tee_sheet(page, target_date)
            await take_detailed_screenshot(page, f"tee_sheet_attempt_{attempt + 1}")
            
            # Add a delay to ensure page is fully loaded
            await asyncio.sleep(1)
            
            # For dry run tests, if no slots are found on first attempt, we can
            # simulate finding a slot to test the rest of the flow
            available_slots = await find_tee_time_slots_on_tee_sheet(page, target_time)
            
            if available_slots:
                # Get the best slot (closest to target time)
                best_slot = available_slots[0]
                logger.info(f"Found available slot at {best_slot['time']} (distance: {best_slot['distance']} mins)")
                
                # Attempt to book the slot
                success = await attempt_booking(page, best_slot, player_count, dry_run)
                if success:
                    logger.info("Booking attempt successful")
                    return True
            else:
                logger.warning(f"No available slots found near {target_time} on attempt {attempt + 1}")
                
                if dry_run and attempt == max_retries:
                    # For dry run in test mode, create a simulated slot if none found
                    # This allows us to test the booking functionality even when no slots are available
                    logger.info("DRY RUN: Creating a simulated slot for testing purposes")
                    
                    # Find a form on the page to use for simulating a booking
                    form = await page.query_selector("form[id*='TeeSheetForm']")
                    if form:
                        form_id = await form.get_attribute("id")
                        simulated_slot = {
                            'element': form,
                            'time': target_time,
                            'minutes': int(target_time.split(':')[0]) * 60 + int(target_time.split(':')[1]),
                            'distance': 0,
                            'form_id': form_id,
                            'simulated': True
                        }
                        
                        logger.info("Attempting booking with simulated slot")
                        success = await attempt_booking(page, simulated_slot, player_count, dry_run)
                        if success:
                            logger.info("Simulated booking attempt successful for dry run")
                            return True
                
                if attempt < max_retries:
                    # Try the booking page URL directly before retrying
                    logger.info("Trying direct booking page navigation before retry")
                    await navigate_to_booking_page(page, target_date)
                    await asyncio.sleep(1)
                else:
                    logger.error("Failed to find any available slots after all attempts")
                    return False
                
        except Exception as e:
            logger.error(f"Error in booking process (attempt {attempt + 1}): {str(e)}")
            await take_detailed_screenshot(page, f"booking_process_error_attempt_{attempt + 1}")
            
            if attempt < max_retries:
                logger.info(f"Retrying after error (attempt {attempt + 1} of {max_retries})")
                # Refresh the page before retrying
                try:
                    await page.goto("https://customer-cc36.clubcaddie.com/")
                    await page.wait_for_load_state("domcontentloaded") # faster than networkidle
                except Exception as nav_error:
                    logger.error(f"Navigation error during retry: {str(nav_error)}")
            else:
                logger.error("All booking attempts failed")
                return False
    
    return False
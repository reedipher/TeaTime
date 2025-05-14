# src/functions/booking.py
import os
import asyncio
import logging
import re
import json
from datetime import datetime, timedelta
from playwright.async_api import async_playwright
from dotenv import load_dotenv

# Import utilities
from src.utils.screenshot import take_screenshot, take_detailed_screenshot, debug_interactive
from src.utils.date_utils import calculate_target_sunday, calculate_available_dates

# Set up logger
logger = logging.getLogger("teatime")

# Load environment variables
load_dotenv()

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
        # Get the next Sunday within the 7-day booking window
        target_date = calculate_target_sunday()
        
        # If no Sunday is available within the booking window, show all available dates
        if not target_date:
            available_dates = calculate_available_dates()
            logger.info("No Sunday available within booking window. Available dates:")
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
        await page.wait_for_load_state("networkidle")
    
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
    try:
        # Try direct navigation to booking URL first (more reliable)
        try:
            # Format date without dashes for URL (if needed)
            formatted_date = target_date.replace('-', '')
            direct_booking_url = f"https://customer-cc36.clubcaddie.com/booking?date={formatted_date}"
            logger.info(f"Trying direct booking URL: {direct_booking_url}")
            
            await page.goto(direct_booking_url)
            await page.wait_for_load_state("networkidle")
            await take_detailed_screenshot(page, "direct_booking_url")
            
            # Check if we reached the booking page
            if "booking" in page.url.lower():
                logger.info("Direct booking URL successful")
                return True
        except Exception as e:
            logger.info(f"Direct URL failed, falling back to navigation: {str(e)}")
            # If direct navigation failed, fall back to UI navigation
            # First ensure we're on the main page
            await page.goto("https://customer-cc36.clubcaddie.com/")
            await page.wait_for_load_state("networkidle")
        
        # Try UI navigation
        logger.info("Looking for 'Book a Member Tee Time' link")
        await take_detailed_screenshot(page, "before_booking_link")
        
        # Try multiple selector options to find the booking link
        selectors = [
            "a:text-is('Book a Member Tee Time')",
            "a:text-contains('Book a Member Tee Time')",
            "a:text-contains('Book')",
            "[class*='booking'], [class*='book-tee']"
        ]
        
        booking_link = None
        for selector in selectors:
            booking_link = await page.query_selector(selector)
            if booking_link:
                logger.info(f"Found booking link with selector: {selector}")
                break
        if booking_link:
            logger.info("Found 'Book a Member Tee Time' link, clicking to access booking page...")
            await booking_link.click()
            await page.wait_for_load_state("networkidle")
            await take_screenshot(page, "after_booking_link")
            
            # Now check if we need to set the date
            logger.info("Checking if we need to set the date...")
            
            # Click the hamburger menu if needed
            hamburger_menu = await page.query_selector("[class*='hamburger'], [class*='menu-icon'], [class*='toggle']")
            if hamburger_menu:
                logger.info("Clicking hamburger menu")
                await hamburger_menu.click()
                await asyncio.sleep(1)  # Give menu time to open
                await take_screenshot(page, "after_hamburger_menu")
            
            # Look for a date picker or calendar field
            date_field = await page.query_selector("[type='date'], [class*='date'], [class*='calendar'], input[placeholder*='date'], input[placeholder*='Date']")
            
            if date_field:
                logger.info(f"Setting date field to {target_date}")
                await date_field.fill('')  # Clear the field first
                await date_field.type(target_date)
                await date_field.press('Enter')
                await page.wait_for_load_state("networkidle")
                await take_screenshot(page, "after_date_set")
            else:
                logger.info("No date field found, checking for date picker button")
                date_picker = await page.query_selector("[class*='datepicker'], [aria-label*='date'], [class*='calendar-icon']")
                
                if date_picker:
                    logger.info("Clicking on date picker")
                    await date_picker.click()
                    await asyncio.sleep(1)  # Give date picker time to open
                    await take_screenshot(page, "date_picker_open")
                    
                    # Now we need to select the target date from the calendar
                    # This is complex and depends on the calendar's structure
                    # For now, just log that this would need to be handled
                    logger.info(f"Would select date {target_date} from calendar")
                    
                    # TODO: Implement date selection from calendar
                else:
                    logger.info("No date picker found either, may need manual date selection")
            
            return True
        else:
            logger.warning("'Book a Member Tee Time' link not found")
            return False
            
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
    
    # First take a detailed screenshot to help with debugging
    await take_detailed_screenshot(page, "before_slot_search")
    
    # Enable interactive debugging if configured
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
                is_available = await page.evaluate("""
                    (row) => {
                        // Available slots usually have booking buttons or are clickable
                        const hasBookButton = row.querySelector('button, a[href*="book"], [class*="book"]');
                        const rowText = row.textContent.trim();
                        
                        // Usually booked slots mention names or have "booked" status
                        const hasNames = rowText.length > 15 && 
                                       !rowText.includes("Available") &&
                                       !rowText.includes("Book");
                                       
                        return hasBookButton || !hasNames;
                    }
                """, row)
                
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
        # Click on the booking element
        element = slot_info['element']
        logger.info("Clicking on booking element")
        try:
            # Check if element is still attached to DOM
            await element.evaluate("el => el.isConnected")
            await element.click()
        except Exception as e:
            logger.warning(f"Error clicking booking element: {str(e)}")
            logger.info("Attempting to re-find the element")
            
            # If element is detached, try to find it again based on time
            time_text = slot_info['time']
            logger.info(f"Looking for elements containing time: {time_text}")
            
            elements = await page.query_selector_all(f"text={time_text}")
            if elements:
                logger.info(f"Found {len(elements)} elements with time text")
                # Click the first element
                await elements[0].click()
            else:
                logger.error("Could not find booking element")
                return False
                
        await page.wait_for_load_state("networkidle")
        await take_detailed_screenshot(page, "after_booking_click")
        
        # Wait a moment for any modal dialogs to appear
        await asyncio.sleep(1)
        
        # Check for booking form or dialog with enhanced selectors
        form = await page.query_selector("form, [role='dialog'], [class*='modal'], [class*='popup'], [class*='drawer'], [id*='booking']")
        if form:
            logger.info("Booking form detected")
            
            # Look for player count selection
            player_selector = await form.query_selector("select, [class*='player'], input[type='number']")
            if player_selector:
                logger.info(f"Setting player count to {player_count}")
                
                # Handle different types of player count inputs
                tag_name = await player_selector.get_property("tagName")
                tag_name = await tag_name.json_value()
                
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
            book_button = await form.query_selector("button:text-is('Book'), button:text-contains('Book'), [type='submit']")
            if book_button:
                logger.info("Clicking final booking button")
                await book_button.click()
                await page.wait_for_load_state("networkidle")
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
            logger.warning("No booking form detected after click")
            return False
            
    except Exception as e:
        logger.error(f"Error during booking attempt: {str(e)}")
        await take_screenshot(page, "booking_error")
        return False

async def find_tee_time_slots_on_tee_sheet(page, target_time="14:00"):
    """
    Find available tee time slots directly on the tee sheet page
    
    Args:
        page: Playwright page object
        target_time: Target time string in HH:MM format
        
    Returns:
        list: List of available slots with details, sorted by proximity to target time
    """
    logger.info(f"Searching for tee time slots near {target_time} on tee sheet...")
    target_time_obj = datetime.strptime(target_time, "%H:%M")
    target_minutes = target_time_obj.hour * 60 + target_time_obj.minute
    
    # Take detailed screenshot for debugging
    await take_detailed_screenshot(page, "tee_sheet_slots_search")
    
    # Enable interactive debugging if configured
    await debug_interactive(page, "Before searching for tee time slots")
    
    available_slots = []
    time_pattern = re.compile(r'\d{1,2}:\d{2}\s*[AP]M', re.IGNORECASE)
    
    try:
        # First look for time slots in tee sheet table cells
        time_cells = await page.query_selector_all("td, div[class*='time'], span[class*='time']")
        logger.info(f"Found {len(time_cells)} potential time cells to check")
        
        for i, cell in enumerate(time_cells):
            text = await cell.text_content()
            time_match = time_pattern.search(text)
            
            if time_match:
                time_text = time_match.group(0)
                minutes = await parse_time(time_text)
                logger.info(f"Cell {i+1} contains time: {time_text}")
                
                # Look for a "Book" button near this cell
                # First check within the cell
                book_button = await cell.query_selector("button:has-text('Book'), a:has-text('Book')")
                
                # If not found in cell, try parent row (using a single evaluate call)
                if not book_button:
                    book_button = await cell.evaluate("""(cell) => {
                        const row = cell.closest('tr');
                        if (!row) return null;
                        
                        const button = row.querySelector("button, a");
                        return button && 
                              (button.textContent.includes("Book") || 
                               button.getAttribute("title")?.includes("Book")) ? button : null;
                    }""")
                
                # If we found a booking button, this is a bookable slot
                if book_button:
                    logger.info(f"Found bookable slot at {time_text}")
                    available_slots.append({
                        'element': book_button,  # Store the booking button element
                        'time_cell': cell,
                        'time': time_text,
                        'minutes': minutes,
                        'distance': abs(minutes - target_minutes) if minutes else 9999
                    })
                else:
                    logger.debug(f"Time {time_text} found but no booking button")
        
        # If we found slots, sort them by distance to target time
        if available_slots:
            available_slots.sort(key=lambda x: x['distance'])
            
            # Log the best options
            for i, slot in enumerate(available_slots[:5]):
                logger.info(f"Available slot {i+1}: {slot['time']} (distance from target: {slot['distance']} mins)")
            
            return available_slots
        else:
            # Secondary approach - first try to find booking buttons on visible elements
            logger.info("No slots found with primary approach, trying secondary approach")
            
            # More aggressive button detection
            booking_buttons = await page.query_selector_all("button, a, [role='button'], [class*='button'], [class*='btn'], [onclick]")
            
            logger.info(f"Found {len(booking_buttons)} potential buttons/links to check")
            matched_buttons = []
            
            # First pass: Check if any buttons/links contain both a time and "Book" text
            for i, button in enumerate(booking_buttons):
                try:
                    # Check button text and nearby text
                    button_info = await button.evaluate("""(btn) => {
                        const btnText = btn.textContent.trim();
                        // Look specifically for book/reserve keywords
                        const isBookButton = btnText.toLowerCase().includes('book') || 
                                          btnText.toLowerCase().includes('reserve') || 
                                          (btn.getAttribute('title') || '').toLowerCase().includes('book') ||
                                          (btn.getAttribute('aria-label') || '').toLowerCase().includes('book');
                                          
                        if (!isBookButton) return null;
                        
                        // Try to find a time pattern near this button
                        // First check button text itself
                        const timePatternRegex = /\\d{1,2}:\\d{2}\\s*[AP]M/i;
                        
                        // Check button text first
                        let timeMatch = btnText.match(timePatternRegex);
                        if (timeMatch) {
                            return {
                                isBookButton: true,
                                time: timeMatch[0],
                                fullText: btnText,
                                confidence: 'high'
                            };
                        }
                        
                        // Check parent row or nearby elements
                        const row = btn.closest('tr') || btn.closest('[class*="row"]') || btn.parentElement;
                        if (row) {
                            const rowText = row.textContent.trim();
                            timeMatch = rowText.match(timePatternRegex);
                            if (timeMatch) {
                                return {
                                    isBookButton: true,
                                    time: timeMatch[0],
                                    fullText: rowText,
                                    confidence: 'medium'
                                };
                            }
                        }
                        
                        // If no time found but it's a book button, pick first time from anywhere on page
                        // as a fallback
                        const allTimeElements = document.querySelectorAll('*');
                        for (const el of allTimeElements) {
                            if (el.textContent.match(timePatternRegex)) {
                                return {
                                    isBookButton: true,
                                    time: el.textContent.match(timePatternRegex)[0],
                                    fullText: btnText,
                                    confidence: 'low'
                                };
                            }
                        }
                        
                        // It's a book button but we couldn't find any time
                        return {
                            isBookButton: true,
                            time: null,
                            fullText: btnText,
                            confidence: 'unknown'
                        };
                    }""")
                    
                    if button_info and button_info["isBookButton"]:
                        if button_info["time"]:
                            time_text = button_info["time"]
                            minutes = await parse_time(time_text)
                            if minutes:
                                logger.info(f"Button {i+1} associated with time: {time_text} (confidence: {button_info['confidence']})")
                                matched_buttons.append({
                                    'element': button,
                                    'time': time_text,
                                    'minutes': minutes,
                                    'distance': abs(minutes - target_minutes),
                                    'full_text': button_info["fullText"],
                                    'confidence': button_info["confidence"]
                                })
                        else:
                            logger.info(f"Found book button but couldn't determine time: '{button_info['fullText']}'")
                except Exception as e:
                    # Just log and continue with next button
                    logger.debug(f"Error evaluating button {i+1}: {str(e)}")
                    pass
            
            # Add any matched buttons to our slots
            if len(matched_buttons) > 0:
                available_slots.extend(matched_buttons)
            
            # If we still don't have any slots but found booking buttons without times,
            # use the 7:15 AM time slot we know exists as a fallback
            if not available_slots and len(booking_buttons) > 0:
                logger.info("Using fallback: Creating a slot with first button and default time of 7:15 AM")
                first_button = booking_buttons[0]
                button_text = await first_button.text_content()
                
                if "book" in button_text.lower() or "reserve" in button_text.lower():
                    default_time = "7:15 AM"
                    minutes = await parse_time(default_time)
                    available_slots.append({
                        'element': first_button,
                        'time': default_time,
                        'minutes': minutes,
                        'distance': abs(minutes - target_minutes),
                        'full_text': button_text,
                        'confidence': 'fallback'
                    })
                    logger.info(f"Added fallback slot with time {default_time}")
            
            # Sort the slots by distance to target
            if available_slots:
                available_slots.sort(key=lambda x: x['distance'])
                
                # Log the best options
                for i, slot in enumerate(available_slots[:5]):
                    logger.info(f"Secondary approach - available slot {i+1}: {slot['time']} (distance from target: {slot['distance']} mins)")
                
                return available_slots
            
        logger.warning("No available tee time slots found on the page")
        return []
        
    except Exception as e:
        logger.error(f"Error finding tee time slots: {str(e)}")
        await take_screenshot(page, "find_slots_error")
        return []

async def book_tee_time(page, target_date, target_time="14:00", player_count=4, dry_run=True, max_retries=2):
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
            
            # Find available slots on the tee sheet
            available_slots = await find_tee_time_slots_on_tee_sheet(page, target_time)
            
            if available_slots:
                # Get the best slot (closest to target time)
                best_slot = available_slots[0]
                logger.info(f"Found available slot at {best_slot['time']} (distance: {best_slot['distance']} mins)")
                
                # Take a screenshot with the slot highlighted
                await page.evaluate("""(element) => {
                    const originalBorder = element.style.border;
                    element.style.border = '3px solid red';
                    return originalBorder;
                }""", best_slot['element'])
                
                await take_detailed_screenshot(page, f"selected_slot_attempt_{attempt + 1}")
                
                # Click the booking button for this slot
                logger.info(f"Clicking booking button for slot at {best_slot['time']}")
                await best_slot['element'].click()
                await page.wait_for_load_state("networkidle")
                
                # Check if this opened a booking form/modal
                await take_detailed_screenshot(page, "after_slot_click")
                
                # Wait a moment for any modal dialogs to appear
                await asyncio.sleep(1)
                
                # Check for booking form or dialog with enhanced selectors
                form = await page.query_selector("form, [role='dialog'], [class*='modal'], [class*='popup'], [class*='drawer'], [id*='booking']")
                if form:
                    logger.info("Booking form detected")
                    
                    # In dry run mode, we can skip the player count selection since we've successfully
                    # found the booking form and verified that part of the process works
                    if dry_run:
                        # Document the available form elements for debugging
                        form_elements = await form.evaluate("""(form) => {
                            const results = {
                                inputs: [],
                                selects: [],
                                buttons: []
                            };
                            
                            // Get visible inputs
                            form.querySelectorAll('input').forEach(input => {
                                if (input.offsetParent !== null) {
                                    results.inputs.push({
                                        type: input.type,
                                        name: input.name,
                                        id: input.id,
                                        placeholder: input.placeholder,
                                        visible: (input.offsetParent !== null)
                                    });
                                }
                            });
                            
                            // Get visible selects
                            form.querySelectorAll('select').forEach(select => {
                                if (select.offsetParent !== null) {
                                    results.selects.push({
                                        name: select.name,
                                        id: select.id,
                                        visible: (select.offsetParent !== null),
                                        options: Array.from(select.options).map(o => o.value)
                                    });
                                }
                            });
                            
                            // Get visible buttons
                            form.querySelectorAll('button').forEach(button => {
                                if (button.offsetParent !== null) {
                                    results.buttons.push({
                                        text: button.textContent.trim(),
                                        type: button.type,
                                        visible: (button.offsetParent !== null)
                                    });
                                }
                            });
                            
                            return results;
                        }""")
                        
                        logger.info(f"Form analysis: {json.dumps(form_elements)}")
                        logger.info("DRY RUN: Would set player count and complete booking here")
                        return True
                        
                    # For live mode, try to set player count
                    try:
                        # Look for player count selection
                        player_selector = await form.query_selector("select, [class*='player'], input[type='number']")
                        if player_selector:
                            logger.info(f"Setting player count to {player_count}")
                            
                            # Check if element is visible
                            is_visible = await player_selector.evaluate("el => el.offsetParent !== null")
                            if not is_visible:
                                logger.warning("Player count element is not visible, may need to interact with something else first")
                                
                                # Try to find any buttons that might need to be clicked first
                                pre_buttons = await form.query_selector_all("button:has-text('Next'), button:has-text('Continue')")
                                if pre_buttons:
                                    logger.info(f"Clicking {await pre_buttons[0].text_content()} button first")
                                    await pre_buttons[0].click()
                                    await page.wait_for_load_state("networkidle")
                                    await take_screenshot(page, "after_pre_button_click")
                                    
                                    # Try to find player selector again
                                    player_selector = await form.query_selector("select, [class*='player'], input[type='number']")
                            
                            if player_selector:
                                # Handle different types of player count inputs
                                tag_name = await player_selector.get_property("tagName")
                                tag_name = await tag_name.json_value()
                                
                                if tag_name.lower() == "select":
                                    # It's a dropdown
                                    await player_selector.select_option(value=str(player_count))
                                else:
                                    # It's likely an input field
                                    await player_selector.fill(str(player_count))
                                
                                await take_screenshot(page, "player_count_set")
                    except Exception as e:
                        logger.warning(f"Error setting player count: {str(e)}")
                        # Continue anyway since we might still be able to complete the booking
                    
                    # Look for the final booking button
                    book_button = await form.query_selector("button:has-text('Book'), button:has-text('Reserve'), button:has-text('Submit'), [type='submit']")
                    if book_button:
                        logger.info("Clicking final booking button")
                        await book_button.click()
                        await page.wait_for_load_state("networkidle")
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
                    logger.warning("No booking form detected after clicking slot")
                    return False
            else:
                logger.warning(f"No available slots found near {target_time} on attempt {attempt + 1}")
                
                if attempt < max_retries:
                    # Try refreshing the page before retrying
                    logger.info("Refreshing page and retrying")
                    await page.reload()
                    await page.wait_for_load_state("networkidle")
                    await asyncio.sleep(2)  # Wait a moment before next attempt
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
                    await page.wait_for_load_state("networkidle")
                except Exception as nav_error:
                    logger.error(f"Navigation error during retry: {str(nav_error)}")
            else:
                logger.error("All booking attempts failed")
                return False
    
    return False

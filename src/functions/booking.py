# src/functions/booking.py
import os
import asyncio
import logging
import re
from datetime import datetime, timedelta
from playwright.async_api import async_playwright
from dotenv import load_dotenv

# Import utilities
from ..utils.screenshot import take_screenshot
from ..utils.date_utils import calculate_target_sunday, calculate_available_dates

# Set up logger
logger = logging.getLogger("teatime")

# Load environment variables
load_dotenv()

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
        # First, click the "Book a Member Tee Time" link
        logger.info("Looking for 'Book a Member Tee Time' link")
        await take_screenshot(page, "before_booking_link")
        
        # Use a more flexible selector that should work even with slight text variations
        booking_link = await page.query_selector("a:text-is('Book a Member Tee Time'), a:text-contains('Book a Member Tee Time')")
        
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
    
    await take_screenshot(page, "before_slot_search")
    
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
    await take_screenshot(page, "before_booking_attempt")
    
    try:
        # Click on the booking element
        element = slot_info['element']
        logger.info("Clicking on booking element")
        await element.click()
        await page.wait_for_load_state("networkidle")
        await take_screenshot(page, "after_booking_click")
        
        # Check for booking form or dialog
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

async def book_tee_time(page, target_date, target_time="14:00", player_count=4, dry_run=True):
    """
    Complete tee time booking process
    
    Args:
        page: Playwright page object
        target_date: Target date in YYYY-MM-DD format
        target_time: Target time in HH:MM format
        player_count: Number of players to book
        dry_run: If True, simulate booking without completing
        
    Returns:
        bool: Whether the booking was successful
    """
    try:
        # First, navigate to the booking page and set the date
        if not await navigate_to_booking_page(page, target_date):
            logger.warning("Could not navigate to booking page properly")
            # Try using the tee sheet page directly
            logger.info("Falling back to tee sheet page for booking")
        
        # Search for available slots near the target time
        slot = await search_for_available_slots(page, target_time)
        
        if slot:
            logger.info(f"Found available slot at {slot['time']} - attempting to book")
            return await attempt_booking(page, slot, player_count, dry_run)
        else:
            logger.warning(f"No available slots found near {target_time}")
            return False
            
    except Exception as e:
        logger.error(f"Error in booking process: {str(e)}")
        await take_screenshot(page, "booking_process_error")
        return False
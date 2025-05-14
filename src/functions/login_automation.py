# src/functions/login_automation.py
import asyncio
import os
import json
import traceback
from datetime import datetime
from dotenv import load_dotenv

# Import our modules
from .auth import login_to_club_caddie
from .booking import navigate_to_tee_sheet, book_tee_time, debug_interactive
from ..utils.date_utils import calculate_target_day, calculate_available_dates
from ..utils.logger import setup_logger
from ..utils.screenshot import take_detailed_screenshot

# Set up logger
logger = setup_logger()

# Load environment variables
load_dotenv()

async def main():
    """
    Main function for the tee time booking automation
    """
    # Load configuration from environment variables
    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
    target_time = os.getenv("TARGET_TIME", "14:00")
    player_count = int(os.getenv("PLAYER_COUNT", "4"))
    max_retries = int(os.getenv("MAX_RETRIES", "2"))
    debug_mode = os.getenv("DEBUG_INTERACTIVE", "false").lower() == "true"
    
    # Create run info for logging
    run_info = {
        "timestamp": datetime.now().isoformat(),
        "config": {
            "dry_run": dry_run,
            "target_time": target_time,
            "player_count": player_count,
            "max_retries": max_retries,
            "debug_mode": debug_mode
        }
    }
    
    logger.info(f"Starting tee time booking automation with config: {json.dumps(run_info['config'], indent=2)}")
    logger.info(f"Running in {'DRY RUN' if dry_run else 'LIVE'} mode")
    
    # Step 1: Login
    page, browser, playwright = await login_to_club_caddie()
    
    if page and browser and playwright:
        try:
            # Enable debug mode if configured
            if debug_mode:
                logger.info("Debug mode enabled - will pause at key points")
                await debug_interactive(page, "After successful login")
            
            # Step 2: Show available booking dates
            available_dates = calculate_available_dates()
            logger.info("Available booking dates within the booking window:")
            for date_info in available_dates:
                logger.info(f"{date_info['date']} ({date_info['weekday']}) - {date_info['days_ahead']} days ahead")
            
            # Save available dates to run info
            run_info["available_dates"] = available_dates
            
            # Step 3: Calculate target date (using configured target day)
            target_date = calculate_target_day()
            target_day_name = os.getenv("TARGET_DAY", "Sunday")  # Get the name for logging
            if not target_date:
                logger.info(f"No {target_day_name} available within booking window, using furthest available date")
                target_date = available_dates[-1]['date']
            
            logger.info(f"Selected target date: {target_date}")
            run_info["target_date"] = target_date
            
            # Capture detailed screenshot before booking
            await take_detailed_screenshot(page, "before_booking_process")
            
            # Step 4: Attempt to book a tee time on the target date with retry logic
            logger.info(f"Attempting to book tee time for {player_count} players around {target_time}")
            success = await book_tee_time(
                page, 
                target_date, 
                target_time, 
                player_count, 
                dry_run,
                max_retries
            )
            
            # Update run info with booking result
            run_info["booking_result"] = {
                "success": success,
                "timestamp": datetime.now().isoformat()
            }
            
            if success:
                logger.info("Booking process completed successfully")
            else:
                logger.warning("Booking process did not complete successfully")
            
            # Final debug pause if in debug mode
            if debug_mode:
                logger.info("Pausing for final inspection in debug mode")
                await debug_interactive(page, "After booking process")
            elif success or os.getenv("WAIT_AFTER_COMPLETION", "true").lower() == "true":
                # Wait for manual inspection
                wait_time = int(os.getenv("WAIT_TIME", "30"))
                logger.info(f"Waiting {wait_time} seconds for manual inspection...")
                await asyncio.sleep(wait_time)
            
            # Save run report
            os.makedirs("artifacts/reports", exist_ok=True)
            report_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = f"artifacts/reports/booking_report_{report_timestamp}.json"
            with open(report_path, "w") as f:
                json.dump(run_info, f, indent=2)
            logger.info(f"Run report saved to {report_path}")
            
            logger.info("Script completed successfully")
            
        except Exception as e:
            logger.error(f"Error during automation: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Capture error screenshot
            try:
                await take_detailed_screenshot(page, "error_state")
            except:
                logger.error("Failed to capture error screenshot")
                
        finally:
            if browser:
                await browser.close()
            if playwright:
                await playwright.stop()
    else:
        logger.error("Automation failed: Could not login")

if __name__ == "__main__":
    asyncio.run(main())

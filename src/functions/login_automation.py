# src/functions/login_automation.py
import asyncio
import os
from dotenv import load_dotenv

# Import our modules
from .auth import login_to_club_caddie
from .booking import navigate_to_tee_sheet, book_tee_time
from ..utils.date_utils import calculate_target_sunday, calculate_available_dates
from ..utils.logger import setup_logger

# Set up logger
logger = setup_logger()

# Load environment variables
load_dotenv()

async def main():
    """
    Main function for the tee time booking automation
    """
    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
    logger.info(f"Running in {'DRY RUN' if dry_run else 'LIVE'} mode")
    
    # Step 1: Login
    page, browser, playwright = await login_to_club_caddie()
    
    if page and browser and playwright:
        try:
            # Step 2: Show available booking dates
            available_dates = calculate_available_dates()
            logger.info("Available booking dates within the booking window:")
            for date_info in available_dates:
                logger.info(f"{date_info['date']} ({date_info['weekday']}) - {date_info['days_ahead']} days ahead")
            
            # Step 3: Navigate to tee sheet (it will choose the appropriate date)
            target_date = await navigate_to_tee_sheet(page)
            logger.info(f"Selected target date: {target_date}")
            
            # Step 4: Attempt to book a tee time on the target date
            target_time = os.getenv("TARGET_TIME", "14:00")
            player_count = int(os.getenv("PLAYER_COUNT", "4"))
            
            logger.info(f"Attempting to book tee time for {player_count} players around {target_time}")
            success = await book_tee_time(page, target_date, target_time, player_count, dry_run)
            
            if success:
                logger.info("Booking process completed successfully")
            else:
                logger.warning("Booking process did not complete successfully")
            
            # Wait for manual inspection
            logger.info("Waiting 30 seconds for manual inspection...")
            await asyncio.sleep(30)
            
            logger.info("Script completed successfully")
        except Exception as e:
            logger.error(f"Error during automation: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
        finally:
            if browser:
                await browser.close()
            if playwright:
                await playwright.stop()
    else:
        logger.error("Automation failed: Could not login")

if __name__ == "__main__":
    asyncio.run(main())
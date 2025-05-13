# src/functions/login_automation.py
import asyncio
import os
from dotenv import load_dotenv

# Import our modules
from .auth import login_to_club_caddie
from .booking import navigate_to_tee_sheet, find_tee_time, book_tee_time
from ..utils.date_utils import calculate_target_saturday

# Load environment variables
load_dotenv()

async def main():
    """
    Main function for the tee time booking automation
    """
    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
    print(f"Running in {'DRY RUN' if dry_run else 'LIVE'} mode")
    
    # Step 1: Login
    page, browser = await login_to_club_caddie()
    
    if page and browser:
        try:
            # Step 2: Calculate target date (next Saturday at least 8 days out)
            target_date = calculate_target_saturday()
            print(f"Target date for booking: {target_date}")
            
            # Step 3: Navigate to tee sheet
            await navigate_to_tee_sheet(page, target_date)
            
            # Step 4: Find tee time
            tee_time = await find_tee_time(page, os.getenv("TARGET_TIME", "07:30"))
            
            # Step 5: Book tee time (if found)
            if tee_time:
                player_count = int(os.getenv("PLAYER_COUNT", "4"))
                await book_tee_time(page, tee_time, player_count, dry_run)
            
            # Wait for manual inspection
            print("\nWaiting 30 seconds for manual inspection...")
            await asyncio.sleep(30)
            
            print("Script completed successfully")
        except Exception as e:
            print(f"Error during automation: {str(e)}")
        finally:
            if browser:
                await browser.close()
    else:
        print("Automation failed: Could not login")

if __name__ == "__main__":
    asyncio.run(main())
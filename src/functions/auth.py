# src/functions/auth.py
import os
import asyncio
from playwright.async_api import async_playwright
from dotenv import load_dotenv
import logging

# Import utilities
from src.utils.screenshot import take_screenshot

# Set up logger
logger = logging.getLogger("teatime")

# Load environment variables
load_dotenv()

async def login_to_club_caddie():
    """
    Automate login to the Club Caddie system
    
    Returns:
        tuple: (page, browser, playwright) on success, (None, None, None) on failure
    """
    
    # Get credentials from environment variables
    username = os.getenv("CLUB_CADDIE_USERNAME")
    password = os.getenv("CLUB_CADDIE_PASSWORD")
    
    if not username or not password:
        print("Error: CLUB_CADDIE_USERNAME and CLUB_CADDIE_PASSWORD must be set in .env file")
        return None, None, None
    
    logger.info(f"Attempting login with username: {username[:3]}...{username[-3:] if len(username) > 3 else ''}")
    
    p = await async_playwright().start()
    try:
        # Launch browser (headless=False to see the automation)
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={"width": 1280, "height": 720})
        page = await context.new_page()
        
        try:
            logger.info("Navigating to login page...")
            await page.goto("https://customer-cc36.clubcaddie.com/login?clubid=103412")
            
            # Ensure the page loaded properly
            await page.wait_for_selector("#Username", state="visible")
            
            logger.info("Entering credentials...")
            await page.fill("#Username", username)
            await page.fill("#Password", password)
            
            # Click login button
            logger.info("Clicking sign in button...")
            await page.click("#signIn")
            
            # Wait for navigation after login
            await page.wait_for_load_state("networkidle")
            
            # Check if login was successful
            current_url = page.url
            print(f"Current URL after login attempt: {current_url}")
            
            # Take screenshot of the result
            await take_screenshot(page, "after_login")
            
            # Simple check - if we're not on the login page anymore, assume success
            if "login" not in current_url.lower():
                print("Login appears successful!")
                return page, browser, p  # Return the page, browser, and playwright instance
            else:
                print("Login appears to have failed.")
                await browser.close()
                await p.stop()
                return None, None, None
                
        except Exception as e:
            print(f"Error during login: {str(e)}")
            await take_screenshot(page, "login_error")
            await browser.close()
            await p.stop()
            return None, None, None
    except Exception as e:
        print(f"Error creating browser: {str(e)}")
        await p.stop()
        return None, None, None

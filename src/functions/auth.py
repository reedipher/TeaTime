# src/functions/auth.py
import os
import asyncio
from playwright.async_api import async_playwright
from dotenv import load_dotenv

# Import utilities
from ..utils.screenshot import take_screenshot

# Load environment variables
load_dotenv()

async def login_to_club_caddie():
    """
    Automate login to the Club Caddie system
    
    Returns:
        tuple: (page, browser) on success, (None, None) on failure
    """
    
    # Get credentials from environment variables
    username = os.getenv("CLUB_CADDIE_USERNAME")
    password = os.getenv("CLUB_CADDIE_PASSWORD")
    
    if not username or not password:
        print("Error: CLUB_CADDIE_USERNAME and CLUB_CADDIE_PASSWORD must be set in .env file")
        return None, None
    
    print(f"Attempting login with username: {username[:3]}...{username[-3:] if len(username) > 3 else ''}")
    
    async with async_playwright() as p:
        # Launch browser (headless=False to see the automation)
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={"width": 1280, "height": 720})
        page = await context.new_page()
        
        try:
            print("Navigating to login page...")
            await page.goto("https://customer-cc36.clubcaddie.com/login?clubid=103412")
            
            # Ensure the page loaded properly
            await page.wait_for_selector("#Username", state="visible")
            
            print("Entering credentials...")
            await page.fill("#Username", username)
            await page.fill("#Password", password)
            
            # Click login button
            print("Clicking sign in button...")
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
                return page, browser  # Return the page and browser for continued use
            else:
                print("Login appears to have failed.")
                await browser.close()
                return None, None
                
        except Exception as e:
            print(f"Error during login: {str(e)}")
            await take_screenshot(page, "login_error")
            await browser.close()
            return None, None
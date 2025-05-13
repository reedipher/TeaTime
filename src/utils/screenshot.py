# src/utils/screenshot.py
import os

# Global counter for screenshots
screenshot_counter = 0

async def take_screenshot(page, name):
    """
    Take a screenshot with sequential numbering
    
    Args:
        page: Playwright page object
        name: Base name for the screenshot
        
    Returns:
        str: Path to the saved screenshot
    """
    global screenshot_counter
    screenshot_counter += 1
    
    # Create screenshots directory if it doesn't exist
    os.makedirs("artifacts/screenshots", exist_ok=True)
    
    # Create filename with zero-padded counter
    filename = f"artifacts/screenshots/{screenshot_counter:02d}_{name}.png"
    
    # Take the screenshot
    await page.screenshot(path=filename)
    print(f"Screenshot saved to '{filename}'")
    
    return filename
# src/utils/screenshot.py
import os
import json
import logging

# Set up logger
logger = logging.getLogger("teatime")

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
    logger.info(f"Screenshot saved to '{filename}'")
    
    return filename

async def take_detailed_screenshot(page, name):
    """
    Take a full-page screenshot with additional page information for debugging
    
    Args:
        page: Playwright page object
        name: Base name for the screenshot
        
    Returns:
        str: Path to the saved screenshot
    """
    # Take regular screenshot
    screenshot_path = await take_screenshot(page, name)
    
    try:
        # Create HTML directory if it doesn't exist
        html_dir = "artifacts/html"
        os.makedirs(html_dir, exist_ok=True)
        
        # Save HTML content
        html_path = f"{html_dir}/{screenshot_counter:02d}_{name}.html"
        html_content = await page.content()
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        logger.info(f"HTML content saved to {html_path}")
        
        # Extract page info for debugging
        page_info = await page.evaluate("""() => {
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
            }
        }""")
        
        # Save page info
        info_dir = "artifacts/debug_info"
        os.makedirs(info_dir, exist_ok=True)
        info_path = f"{info_dir}/{screenshot_counter:02d}_{name}.json"
        with open(info_path, "w") as f:
            json.dump(page_info, f, indent=2)
        
        logger.info(f"Page info for {name}: {json.dumps(page_info)}")
    except Exception as e:
        logger.error(f"Error saving detailed debug info: {str(e)}")
    
    return screenshot_path

async def debug_interactive(page, message="Interactive debug mode"):
    """
    Pause for interactive debugging with browser inspection
    
    Args:
        page: Playwright page object
        message: Message to display
    """
    if os.getenv("DEBUG_INTERACTIVE", "false").lower() == "true":
        logger.info(f"{message} - Pausing for interactive debugging. Press Enter to continue...")
        await take_detailed_screenshot(page, "debug_interactive")
        
        # This would typically wait for user input, but in an async context
        # we'll use asyncio.sleep for a timeout instead
        import asyncio
        await asyncio.sleep(int(os.getenv("DEBUG_TIMEOUT", "30")))
        logger.info("Continuing execution after debug pause")

"""
Base testing infrastructure for functional tests
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from dotenv import load_dotenv

# Add parent directory to path so we can import our modules
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Import our modules
from utils.logger import setup_logger
from utils.screenshot import take_detailed_screenshot

class BaseTestCase:
    """Base class for all functional tests"""

    def __init__(self, test_name: str):
        self.test_name = test_name
        self.test_start_time = datetime.now()
        self.results = {
            "test_name": test_name,
            "start_time": self.test_start_time.isoformat(),
            "end_time": None,
            "success": False,
            "steps": [],
            "errors": [],
            "screenshots": [],
            "config": {},
        }
        
        # Set up test directories
        self.test_output_dir = Path(f"artifacts/test_results/{test_name}_{self.test_start_time.strftime('%Y%m%d_%H%M%S')}")
        os.makedirs(self.test_output_dir, exist_ok=True)
        os.makedirs(f"{self.test_output_dir}/screenshots", exist_ok=True)
        os.makedirs(f"{self.test_output_dir}/html", exist_ok=True)
        
        # Set up logging
        self.logger = setup_logger(
            name=f"test.{test_name}", 
            log_to_file=True, 
            log_file=f"{self.test_output_dir}/test.log"
        )
        self.logger.info(f"Starting test: {test_name}")
        
        # Load environment variables
        load_dotenv()
        self._load_config()
        
        # Instance variables to be set up during test
        self.page = None
        self.browser = None
        self.context = None
        self.playwright = None
        
    def _load_config(self):
        """Load configuration from environment variables"""
        self.config = {
            "dry_run": os.getenv("DRY_RUN", "true").lower() == "true",
            "target_time": os.getenv("TARGET_TIME", "14:00"),
            "player_count": int(os.getenv("PLAYER_COUNT", "4")),
            "club_caddie_username": os.getenv("CLUB_CADDIE_USERNAME"),
            "club_caddie_password": os.getenv("CLUB_CADDIE_PASSWORD"),
            "debug_interactive": os.getenv("DEBUG_INTERACTIVE", "false").lower() == "true",
            "debug_timeout": int(os.getenv("DEBUG_TIMEOUT", "30")),
            "max_retries": int(os.getenv("MAX_RETRIES", "2")),
            "booking_window_days": int(os.getenv("BOOKING_WINDOW_DAYS", "7")),
        }
        # Record config in results (but remove sensitive data)
        self.results["config"] = {k: v for k, v in self.config.items() 
                                if k not in ["club_caddie_username", "club_caddie_password"]}
        self.logger.info(f"Test configuration: {json.dumps(self.results['config'])}")

    async def setup(self):
        """Set up the browser for testing"""
        self.logger.info("Setting up browser")
        
        # Add setup step to results
        self._add_step("browser_setup", "Setting up browser for testing")
        
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=False)
            self.context = await self.browser.new_context(viewport={"width": 1280, "height": 720})
            self.page = await self.context.new_page()
            
            # Configure page to log console messages
            self.page.on("console", lambda msg: self.logger.info(f"BROWSER CONSOLE: {msg.text}"))
            
            # Handle page errors
            self.page.on("pageerror", lambda err: self.logger.error(f"PAGE ERROR: {err}"))
            
            return True
        except Exception as e:
            self.logger.error(f"Error setting up browser: {str(e)}")
            self._add_error("setup", f"Browser setup failed: {str(e)}")
            return False
            
    async def teardown(self):
        """Clean up after the test"""
        self.logger.info("Tearing down browser")
        
        # Add teardown step to results
        self._add_step("browser_teardown", "Tearing down browser")
        
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
            
        # Record test end time
        self.results["end_time"] = datetime.now().isoformat()
        
        # Save test results to file
        results_file = f"{self.test_output_dir}/results.json"
        with open(results_file, "w") as f:
            json.dump(self.results, f, indent=2)
        
        self.logger.info(f"Test results saved to {results_file}")

    async def navigate(self, url: str, description: str = None) -> bool:
        """Navigate to a URL and wait for it to load"""
        if description is None:
            description = f"Navigating to {url}"
            
        self.logger.info(description)
        step_id = f"navigate_{len(self.results['steps'])}"
        
        try:
            self._add_step(step_id, description, {"url": url})
            await self.page.goto(url)
            await self.page.wait_for_load_state("networkidle")
            
            # Take screenshot and save page HTML
            screenshot_path = await self._take_screenshot(f"{step_id}_after")
            
            self._update_step_status(step_id, "success", {
                "current_url": self.page.url,
                "screenshot": screenshot_path
            })
            return True
        except Exception as e:
            self.logger.error(f"Navigation error: {str(e)}")
            self._add_error(step_id, f"Navigation failed: {str(e)}")
            self._update_step_status(step_id, "failed")
            
            # Try to take error screenshot
            await self._take_screenshot(f"{step_id}_error")
            return False

    async def wait_for_element(self, selector: str, timeout: int = 10000, description: str = None) -> Optional[Any]:
        """Wait for an element to appear on the page"""
        if description is None:
            description = f"Waiting for element: {selector}"
            
        self.logger.info(description)
        step_id = f"wait_element_{len(self.results['steps'])}"
        
        try:
            self._add_step(step_id, description, {"selector": selector, "timeout": timeout})
            element = await self.page.wait_for_selector(selector, timeout=timeout)
            
            self._update_step_status(step_id, "success")
            return element
        except Exception as e:
            self.logger.error(f"Element wait error: {str(e)}")
            self._add_error(step_id, f"Element wait failed: {str(e)}")
            self._update_step_status(step_id, "failed")
            return None
            
    async def click_element(self, selector: str, description: str = None) -> bool:
        """Click on an element"""
        if description is None:
            description = f"Clicking element: {selector}"
            
        self.logger.info(description)
        step_id = f"click_{len(self.results['steps'])}"
        
        try:
            self._add_step(step_id, description, {"selector": selector})
            await self.page.click(selector)
            await self.page.wait_for_load_state("networkidle")
            
            # Take screenshot after click
            screenshot_path = await self._take_screenshot(f"{step_id}_after")
            
            self._update_step_status(step_id, "success", {
                "screenshot": screenshot_path
            })
            return True
        except Exception as e:
            self.logger.error(f"Click error: {str(e)}")
            self._add_error(step_id, f"Click failed: {str(e)}")
            self._update_step_status(step_id, "failed")
            
            # Try to take error screenshot
            await self._take_screenshot(f"{step_id}_error")
            return False
            
    async def fill_form(self, selector: str, value: str, description: str = None) -> bool:
        """Fill a form field"""
        if description is None:
            description = f"Filling form field {selector} with value: {value}"
            
        self.logger.info(description)
        step_id = f"fill_{len(self.results['steps'])}"
        
        try:
            self._add_step(step_id, description, {"selector": selector, "value": value})
            await self.page.fill(selector, value)
            
            # Take screenshot after fill
            screenshot_path = await self._take_screenshot(f"{step_id}_after")
            
            self._update_step_status(step_id, "success", {
                "screenshot": screenshot_path
            })
            return True
        except Exception as e:
            self.logger.error(f"Fill form error: {str(e)}")
            self._add_error(step_id, f"Fill form failed: {str(e)}")
            self._update_step_status(step_id, "failed")
            
            # Try to take error screenshot
            await self._take_screenshot(f"{step_id}_error")
            return False
            
    async def debug_pause(self, message: str = "Debug pause"):
        """Pause for debugging if enabled"""
        if self.config["debug_interactive"]:
            self.logger.info(f"DEBUG PAUSE: {message} - will continue in {self.config['debug_timeout']} seconds...")
            await take_detailed_screenshot(self.page, "debug_pause")
            await asyncio.sleep(self.config["debug_timeout"])
            
    async def _take_screenshot(self, name: str) -> str:
        """Take a screenshot and save it to the test output directory"""
        timestamp = datetime.now().strftime("%H%M%S")
        filename = f"{self.test_output_dir}/screenshots/{timestamp}_{name}.png"
        
        try:
            await self.page.screenshot(path=filename)
            self.logger.info(f"Screenshot saved to {filename}")
            self.results["screenshots"].append(filename)
            
            # Also save HTML
            html_filename = f"{self.test_output_dir}/html/{timestamp}_{name}.html"
            html_content = await self.page.content()
            with open(html_filename, "w", encoding="utf-8") as f:
                f.write(html_content)
                
            self.logger.info(f"HTML content saved to {html_filename}")
            return filename
        except Exception as e:
            self.logger.error(f"Screenshot error: {str(e)}")
            return None
            
    def _add_step(self, step_id: str, description: str, data: Dict[str, Any] = None) -> None:
        """Add a test step to the results"""
        step = {
            "id": step_id,
            "description": description,
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "status": "running",
            "data": data or {}
        }
        self.results["steps"].append(step)
        
    def _update_step_status(self, step_id: str, status: str, data: Dict[str, Any] = None) -> None:
        """Update the status of a test step"""
        for step in self.results["steps"]:
            if step["id"] == step_id:
                step["status"] = status
                step["end_time"] = datetime.now().isoformat()
                if data:
                    step["data"].update(data)
                break
                
    def _add_error(self, step_id: str, message: str) -> None:
        """Add an error message to the results"""
        error = {
            "step_id": step_id,
            "message": message,
            "time": datetime.now().isoformat()
        }
        self.results["errors"].append(error)

    def set_test_result(self, success: bool, message: str = None) -> None:
        """Set the overall test result"""
        self.results["success"] = success
        if message:
            if success:
                self.logger.info(f"Test result: {message}")
            else:
                self.logger.error(f"Test result: {message}")
                self._add_error("test_result", message)

async def run_test(test_instance):
    """Helper function to run a test"""
    try:
        # Set up the test
        if not await test_instance.setup():
            return False
            
        # Run the test
        try:
            success = await test_instance.run()
            test_instance.set_test_result(success)
        except Exception as e:
            test_instance.logger.error(f"Test execution error: {str(e)}")
            test_instance.set_test_result(False, f"Test execution error: {str(e)}")
            success = False
            
        # Tear down the test
        await test_instance.teardown()
        return success
    except Exception as e:
        test_instance.logger.error(f"Test infrastructure error: {str(e)}")
        return False

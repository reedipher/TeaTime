#!/usr/bin/env python

"""
Script to install and set up dependencies for Teatime testing
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("install_dependencies")

def run_command(command, description):
    """Run a shell command and log output"""
    logger.info(f"{description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, text=True, 
                                capture_output=True)
        logger.info(f"Success: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed: {e}")
        logger.error(f"Error output: {e.stderr}")
        return False

def install_python_dependencies():
    """Install Python package dependencies"""
    
    # Install core packages from requirements.txt
    if Path("requirements.txt").exists():
        logger.info("Installing packages from requirements.txt")
        if not run_command("pip install -r requirements.txt", "Installing requirements"):
            return False
    
    # Ensure Playwright is installed
    logger.info("Checking for Playwright...")
    try:
        import playwright
        logger.info("Playwright already installed")
    except ImportError:
        logger.info("Playwright not found, installing...")
        if not run_command("pip install playwright", "Installing Playwright"):
            return False
    
    # Install Playwright browsers
    logger.info("Installing Playwright browsers...")
    return run_command("python -m playwright install chromium", "Installing Chromium browser")

def create_directories():
    """Create necessary directories for artifacts"""
    directories = [
        "artifacts/logs",
        "artifacts/screenshots",
        "artifacts/test_results"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Created directory: {directory}")
    
    return True

def main():
    """Main entry point for installation"""
    logger.info("Starting Teatime dependency installation")
    
    # Install Python packages
    if not install_python_dependencies():
        logger.error("Failed to install Python dependencies")
        return 1
    
    # Create directories
    if not create_directories():
        logger.error("Failed to create directories")
        return 1
    
    logger.info("")
    logger.info("Installation complete! You can now run the tests:")
    logger.info("  python src/tests/run_tests.py login --debug")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

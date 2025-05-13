#!/usr/bin/env python

"""
Test runner script for Teatime functional tests
"""

import os
import sys
import asyncio
import argparse
import time
from datetime import datetime
from typing import List, Dict, Any, Tuple
import importlib
import inspect
import logging
from pathlib import Path

# Add parent directory to path so we can import our modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import test modules
from tests.functional.test_login import LoginTest
from tests.functional.test_navigation import NavigationTest
from tests.functional.test_booking_flow import BookingFlowTest
from tests.functional.test_base import run_test
from tests.utils.report_generator import generate_report, generate_index_report

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("test_runner")

# Global test registry
TEST_REGISTRY = {
    "login": LoginTest,
    "navigation": NavigationTest,
    "booking_flow": BookingFlowTest
}

async def run_single_test(test_name: str, debug: bool = False) -> Tuple[bool, Dict]:
    """Run a single test by name"""
    if test_name not in TEST_REGISTRY:
        logger.error(f"Test '{test_name}' not found in registry")
        return False, {}
        
    # Set debug mode if requested
    if debug:
        os.environ["DEBUG_INTERACTIVE"] = "true"
        os.environ["DEBUG_TIMEOUT"] = "20"  # Shorter timeout for debug mode
        print(f"Running {test_name} test in DEBUG mode - will pause at key points")
    else:
        os.environ["DEBUG_INTERACTIVE"] = "false"
        
    # Create test instance
    test_class = TEST_REGISTRY[test_name]
    test_instance = test_class()
    
    # Start time
    start_time = time.time()
    
    # Run the test
    try:
        success = await run_test(test_instance)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Return results
        results = {
            "name": test_name,
            "success": success,
            "duration": duration,
            "output_dir": str(test_instance.test_output_dir) if hasattr(test_instance, "test_output_dir") else None,
            "error_count": len(test_instance.results["errors"]) if hasattr(test_instance, "results") else 0
        }
        
        return success, results
        
    except Exception as e:
        logger.error(f"Error running test {test_name}: {str(e)}")
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Return results
        return False, {
            "name": test_name,
            "success": False,
            "duration": duration,
            "error": str(e)
        }

async def run_all_tests(debug: bool = False) -> List[Dict]:
    """Run all registered tests"""
    results = []
    
    for test_name in TEST_REGISTRY.keys():
        print(f"\n=== Running test: {test_name} ===\n")
        success, result = await run_single_test(test_name, debug)
        results.append(result)
        
        # Brief pause between tests to avoid browser conflicts
        await asyncio.sleep(2)
    
    return results

def print_results(results: List[Dict]) -> None:
    """Print test results in a nice format"""
    print("\n=== Test Results ===\n")
    
    successes = 0
    failures = 0
    total_duration = 0
    
    for result in results:
        status = "✅ PASS" if result.get("success", False) else "❌ FAIL"
        name = result.get("name", "Unknown")
        duration = result.get("duration", 0)
        total_duration += duration
        
        if result.get("success", False):
            successes += 1
        else:
            failures += 1
            
        error_count = result.get("error_count", 0)
        error_text = f" ({error_count} errors)" if error_count > 0 else ""
        output_dir = result.get("output_dir", "")
        
        print(f"{status} - {name} ({duration:.2f}s){error_text}")
        if output_dir:
            print(f"       Output directory: {output_dir}")
    
    print("\nSummary:")
    print(f"Total tests: {len(results)}")
    print(f"Passed: {successes}")
    print(f"Failed: {failures}")
    print(f"Total duration: {total_duration:.2f} seconds")

def print_available_tests():
    """Print a list of available tests"""
    print("\nAvailable tests:")
    for name in TEST_REGISTRY.keys():
        print(f"  - {name}")
    print("\nRun with: python run_tests.py <test_name> [--debug]")
    print("Or run all with: python run_tests.py all [--debug]")

async def main():
    """Main entry point for test runner"""
    parser = argparse.ArgumentParser(description="Run Teatime functional tests")
    parser.add_argument("test", nargs="?", default="list", help="Test to run or 'all' to run all tests")
    parser.add_argument("--debug", action="store_true", help="Run test in debug mode")
    parser.add_argument("--reports", action="store_true", help="Generate HTML reports after tests")
    parser.add_argument("--no-reports", action="store_true", help="Skip HTML report generation")
    
    args = parser.parse_args()
    
    if args.test == "list":
        print_available_tests()
        return
    
    # Determine whether to generate reports
    generate_reports = args.reports
    if not args.reports and not args.no_reports:
        # Default to generating reports unless explicitly disabled
        generate_reports = True
    
    results = []
    if args.test == "all":
        print("Running all tests...")
        results = await run_all_tests(args.debug)
        print_results(results)
    elif args.test in TEST_REGISTRY:
        print(f"Running test: {args.test}")
        success, result = await run_single_test(args.test, args.debug)
        print_results([result])
        results = [result]
    else:
        print(f"Test '{args.test}' not found")
        print_available_tests()
        return
    
    # Generate HTML reports if requested
    if generate_reports and results:
        print("\nGenerating HTML reports...")
        for result in results:
            output_dir = result.get("output_dir")
            if output_dir and os.path.exists(output_dir):
                generate_report(output_dir)
                
        # Generate index report
        generate_index_report()
        print("\nHTML reports generated in artifacts/test_results/")

if __name__ == "__main__":
    asyncio.run(main())

# Teatime Testing Framework

This directory contains a comprehensive test framework for the Teatime golf booking automation system. The testing framework provides detailed logging, screenshot capture, and HTML dumps to help debug and validate the booking flow.

## Test Structure

The tests are organized into several components to facilitate both targeted testing of specific functionality and end-to-end flow testing:

1. **Login Test**: Tests the authentication process to verify login to Club Caddie
2. **Navigation Test**: Tests navigation to the tee sheet and booking pages, including finding available slots
3. **Booking Flow Test**: End-to-end test of the booking process, always runs in DRY RUN mode

## Running Tests

### Prerequisites

Ensure you have configured your `.env` file with the required credentials:

```bash
cp config/.env.example .env
# Edit .env with your Club Caddie credentials
```

### Running Individual Tests

Use the `run_tests.py` script to run specific tests:

```bash
# See available tests
python src/tests/run_tests.py

# Run login test
python src/tests/run_tests.py login

# Run navigation test
python src/tests/run_tests.py navigation

# Run booking flow test
python src/tests/run_tests.py booking_flow
```

### Running All Tests

To run all tests in sequence:

```bash
python src/tests/run_tests.py all
```

### Debug Mode

Add the `--debug` flag to run tests in debug mode, which will pause at key points in the process:

```bash
python src/tests/run_tests.py login --debug
```

## Test Output

All test results are saved to the `artifacts/test_results` directory, organized by test name and timestamp. Each test run creates:

- Detailed JSON report of each step and result
- Screenshots at key points in the flow
- HTML dumps of pages for deep inspection
- Detailed logs of browser actions and responses

Example output structure:

```
artifacts/
└── test_results/
    └── login_test_20250513_110000/
        ├── results.json        # Overall test results
        ├── test.log            # Detailed log file
        ├── screenshots/        # Screenshots at key points
        │   ├── 001_login_page.png
        │   └── 002_after_login.png
        └── html/               # HTML page dumps
            ├── 001_login_page.html
            └── 002_after_login.html
```

## Understanding Test Results

The `results.json` file contains detailed information about each step in the test:

- Status of each step (success/failed/warning)
- Duration of the test
- Error messages if any
- Links to screenshots and HTML files

## Custom Testing

The base test framework in `test_base.py` can be extended to create additional tests. Each test has access to:

1. Page navigation and manipulation
2. Element selection and interaction
3. Detailed logging and screenshot capture
4. Form filling and submission

## Debugging Issues

When a test fails, check:

1. Screenshots in the test output directory
2. HTML dumps for page structure analysis
3. The log file for error messages and warnings
4. The interactive debug mode by running with `--debug` flag

## Integration with CI/CD

These tests can be integrated into a CI/CD pipeline by:

1. Running in headless mode (modify launch options in BaseTestCase)
2. Adding additional reporting formats (e.g., JUnit XML)
3. Setting up automatic runs on schedule or before deployment

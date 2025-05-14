# Teatime ☕⛳

An automated system to book golf tee times at your country club through the Club Caddie system.

## Overview

Teatime automates the process of booking tee times when the booking window opens (typically 7 days in advance at 6am). No more setting alarms to book your favorite tee times!

### Key Features

- Automatically book tee times as soon as the booking window opens
- Target specific times (e.g., Sunday at 2:00 PM)
- Support for booking a specific number of players (default: 4)
- Intelligent view detection to handle both tee sheet and booking page interfaces
- Robust retry mechanisms for handling website inconsistencies
- Improved timing logic to ensure pages are fully loaded before actions
- Detailed logging and screenshots for troubleshooting
- Comprehensive error handling and reporting
- Interactive debug mode for development
- Artifact cleanup utility for managing test outputs
- Clean, maintainable code structure for easy updating

## Project Structure

```
/
├── artifacts/            # Generated artifacts
│   ├── logs/            # Log files
│   ├── screenshots/     # Browser screenshots
│   ├── html/            # HTML page content dumps
│   ├── debug_info/      # Debug information
│   └── test_results/    # Test results and reports
├── config/              # Configuration files
│   └── .env.example     # Template for environment variables
├── doc/                 # Documentation
│   └── architecture/    # System architecture documentation
├── src/                 # Source code
│   ├── functions/       # Main automation functions
│   │   ├── auth.py      # Authentication functions
│   │   ├── booking.py   # Tee time booking functions
│   │   ├── inspector.py # Page inspection utilities
│   │   └── login_automation.py # Login automation
│   ├── tests/           # Test files
│   └── utils/           # Utility modules
│       ├── cleanup_artifacts.py # Utility to clean up artifacts
│       ├── config_loader.py # Configuration handling
│       ├── date_utils.py # Date manipulation utilities
│       ├── logger.py # Logging setup
│       └── screenshot.py # Screenshot capture utilities
└── README.md           # This file
```

## Getting Started

### Prerequisites

- Python 3.9+
- Anaconda or Miniconda (recommended)
- Club Caddie credentials

### Local Development Setup

1. Clone the repository

```bash
git clone <repository-url>
cd teatime
```

2. Create and activate conda environment

```bash
conda env create -f environment.yml
conda activate teatime
```

3. Install testing dependencies

```bash
python src/tests/install_dependencies.py
```

4. Configure environment variables

Copy the template and fill in your details:

```bash
# Option 1: Create .env in project root (recommended)
cp config/.env.example .env
# Edit .env with your credentials and preferences

# Option 2: Create .env in config directory
cp config/.env.example config/.env
# Edit config/.env with your credentials and preferences
```

5. Run a test booking flow (always runs in dry-run mode)

```bash
python src/tests/run_tests.py booking_flow
```

### Testing Framework

The project includes a comprehensive testing framework to validate the booking process:

```bash
# List available tests
python src/tests/run_tests.py

# Run login component test
python src/tests/run_tests.py login

# Run navigation component test 
python src/tests/run_tests.py navigation

# Run full booking flow test (always in dry-run mode)
python src/tests/run_tests.py booking_flow

# Run all tests
python src/tests/run_tests.py all

# Run any test with interactive debugging (pauses at key steps)
python src/tests/run_tests.py login --debug
```

Test results and HTML reports are saved in `artifacts/test_results/` directory.

### Artifact Cleanup

You can clean up test artifacts using the cleanup utility:

```bash
# Interactive cleanup (choose what to delete)
python src/utils/cleanup_artifacts.py

# List artifacts without deleting
python src/utils/cleanup_artifacts.py --list

# Delete specific categories
python src/utils/cleanup_artifacts.py --category screenshots
python src/utils/cleanup_artifacts.py --category test_results
python src/utils/cleanup_artifacts.py --category html
python src/utils/cleanup_artifacts.py --category debug_info

# Delete by age
python src/utils/cleanup_artifacts.py --category all --older-than 7
```

### Configuration Options

Teatime uses two types of configuration:

1. **Credentials** in the `.env` file:

```
# Club Caddie Credentials - place in .env file
CLUB_CADDIE_USERNAME=your_username_here
CLUB_CADDIE_PASSWORD=your_password_here
```

2. **Application settings** in the `config/config.json` file (will use defaults if not present):

```json
{
  "booking": {
    "target_day": "Sunday",
    "target_time": "14:00",
    "player_count": 4
  },
  "runtime": {
    "dry_run": true,
    "max_retries": 2
  },
  "debug": {
    "interactive": false,
    "timeout": 30,
    "wait_after_completion": true,
    "wait_time": 30
  },
  "system": {
    "booking_window_days": 7
  }
}
```

### Features Explained

#### Intelligent View Detection

The system automatically detects and adapts to different views in the Club Caddie interface:

- **Tee Sheet View**: Handles the calendar-style tee time layout
- **Booking View**: Handles the booking page with different HTML structure
- **Adaptive Strategies**: Uses the appropriate booking strategy based on the detected view

#### Reliable Booking with Retry Logic

The system implements robust retry mechanisms to handle website inconsistencies and connection issues:

- Automatic retry of failed booking attempts
- Multiple navigation paths to the booking page
- Fallback strategies if the primary booking method fails
- Improved timing mechanisms to ensure pages load fully before actions
- Detailed error handling and reporting

#### Comprehensive Debugging

The system includes features to help you debug issues:

- **Debug Mode**: When `DEBUG_INTERACTIVE=true`, the automation will pause at key points to let you inspect the browser state
- **Detailed Screenshots**: Full-page screenshots at critical steps in the flow
- **HTML Dumps**: Saves the HTML content of the page for debugging
- **JSON Reports**: Detailed logs of each booking attempt stored in `artifacts/test_results/`
- **Artifact Cleanup**: Utility to clean up test artifacts when they're no longer needed

#### Targeted Time Selection

The system aims to find the tee time closest to your specified target time:

1. Searches available slots around your target time
2. Ranks them by proximity to your preferred time
3. Attempts to book the closest available slot

## Future Enhancements

- Serverless deployment to AWS Lambda for automated execution
- Calendar interface for indicating player availability 
- Multi-user support for coordinating different groups
- Web interface for monitoring booking status

## License

[MIT License](LICENSE)

## Contact

For questions or feedback, please reach out to the project maintainer.
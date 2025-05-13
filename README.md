# Teatime ☕⛳

An automated system to book golf tee times at your country club through the Club Caddie system.

## Overview

Teatime automates the process of booking tee times when the booking window opens (typically 7 days in advance at 6am). No more setting alarms to book your favorite tee times!

### Key Features

- Automatically book tee times as soon as the booking window opens
- Target specific times (e.g., Sunday at 2:00 PM)
- Support for booking a specific number of players (default: 4)
- Robust retry mechanisms for handling website inconsistencies
- Detailed logging and screenshots for troubleshooting
- Comprehensive error handling and reporting
- Interactive debug mode for development
- Clean, maintainable code structure for easy updating

## Project Structure

```
/
├── artifacts/            # Generated artifacts
│   ├── logs/            # Log files
│   └── screenshots/     # Browser screenshots
├── config/              # Configuration files
│   └── .env.example     # Template for environment variables
├── doc/                 # Documentation
│   └── architecture/    # System architecture documentation
├── src/                 # Source code
│   ├── functions/       # Main automation functions
│   │   ├── auth.py      # Authentication functions
│   │   └── booking.py   # Tee time booking functions
│   ├── tests/           # Test files
│   └── utils/           # Utility modules
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
cp config/.env.example .env
# Edit .env with your credentials and preferences
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

# Run any test with interactive debugging (pauses at key steps)
python src/tests/run_tests.py login --debug
```

Test results and HTML reports are saved in `artifacts/test_results/` directory.

### Configuration Options

Key settings in the `.env` file:

```
# Club Caddie Credentials
CLUB_CADDIE_USERNAME=your_username_here
CLUB_CADDIE_PASSWORD=your_password_here

# Booking Preferences
TARGET_TIME=14:00       # Format: HH:MM in 24-hour time
PLAYER_COUNT=4          # Number of players to book for (typically 2-4)

# Runtime Mode
DRY_RUN=true            # Set to false for actual booking

# Advanced Configuration
MAX_RETRIES=2           # Number of retry attempts if booking fails
DEBUG_INTERACTIVE=false # Set to true for interactive debugging mode
DEBUG_TIMEOUT=30        # Seconds to wait at debug pauses
WAIT_AFTER_COMPLETION=true  # Whether to wait after completion
WAIT_TIME=30            # Seconds to wait for manual inspection after completion
```

### Features Explained

#### Reliable Booking with Retry Logic

The system implements robust retry mechanisms to handle website inconsistencies and connection issues:

- Automatic retry of failed booking attempts
- Multiple navigation paths to the booking page
- Fallback strategies if the primary booking method fails
- Detailed error handling and reporting

#### Comprehensive Debugging

The system includes features to help you debug issues:

- **Debug Mode**: When `DEBUG_INTERACTIVE=true`, the automation will pause at key points to let you inspect the browser state
- **Detailed Screenshots**: Full-page screenshots at critical steps in the flow
- **HTML Dumps**: Saves the HTML content of the page for debugging
- **JSON Reports**: Detailed logs of each booking attempt stored in `artifacts/reports/`

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

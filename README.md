# Tea Time ☕⛳

An automated system to book golf tee times at Rocky Bayou Country Club.

## Overview

Tea Time automates the process of booking tee times at a golf club when the booking window opens (typically 8 days in advance at midnight). No more setting alarms for midnight bookings!

### Key Features

- Automatically book earliest available tee time near 7:30 AM when booking opens
- Support for booking a specific number of players (default: 4)
- Notifications on booking success or failure
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

3. Configure environment variables

Copy the template and fill in your details:

```bash
cp config/.env.example .env
# Edit .env with your credentials and preferences
```

4. Run the tee time booking script

```bash
python src/functions/login_automation.py
```

### Configuration Options

Key settings in the `.env` file:

```
# Club Caddie Credentials
CLUB_CADDIE_USERNAME=your_username_here
CLUB_CADDIE_PASSWORD=your_password_here

# Booking Preferences
TARGET_TIME=07:30
PLAYER_COUNT=4

# Runtime Mode
DRY_RUN=true  # Set to false for actual booking
```

## Future Enhancements

- Serverless deployment to AWS Lambda for automated execution
- Calendar interface for indicating player availability 
- Multi-user support for coordinating different groups
- Web interface for monitoring booking status

## License

[MIT License](LICENSE)

## Contact

For questions or feedback, please reach out to the project maintainer.
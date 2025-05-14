# src/utils/config_loader.py
import os
import json
from pathlib import Path
from dotenv import load_dotenv
import logging

# Set up logger
logger = logging.getLogger("teatime")

# Define the root directory of the project
ROOT_DIR = Path(__file__).parents[2]

class Config:
    """Configuration manager that loads settings from both .env and config.json"""
    
    _instance = None  # Singleton instance
    _initialized = False  # Flag to track initialization
    
    def __new__(cls):
        # Implement as a singleton
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        # Only initialize once
        if Config._initialized:
            return
            
        # Load environment variables for credentials
        # First try the .env file in the project root
        load_dotenv()
        
        # Then try the .env file in the config directory
        env_file = ROOT_DIR / "config" / ".env"
        if env_file.exists():
            load_dotenv(env_file)
            logger.info("Loaded environment variables from config/.env")
        
        # Load settings from config file
        self.config = {}
        self._load_config()
        
        Config._initialized = True
    
    def _load_config(self):
        """Load configuration from config.json"""
        config_file = ROOT_DIR / "config" / "config.json"
        
        try:
            if config_file.exists():
                with open(config_file, "r") as f:
                    self.config = json.load(f)
                logger.info("Configuration loaded from config.json")
            else:
                logger.warning(f"Config file {config_file} not found. Using defaults.")
                # Set default configuration
                self.config = {
                    "booking": {
                        "target_day": "Sunday",
                        "target_time": "14:00",
                        "player_count": 4
                    },
                    "runtime": {
                        "dry_run": True,
                        "max_retries": 2
                    },
                    "debug": {
                        "interactive": False,
                        "timeout": 30,
                        "wait_after_completion": True,
                        "wait_time": 30
                    },
                    "system": {
                        "booking_window_days": 7
                    }
                }
        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}")
            raise
    
    def get_credentials(self):
        """Get credentials from environment variables"""
        return {
            "club_caddie_username": os.getenv("CLUB_CADDIE_USERNAME"),
            "club_caddie_password": os.getenv("CLUB_CADDIE_PASSWORD")
        }
    
    def get_booking_config(self):
        """Get booking configuration"""
        return self.config.get("booking", {})
    
    def get_runtime_config(self):
        """Get runtime configuration"""
        return self.config.get("runtime", {})
    
    def get_debug_config(self):
        """Get debug configuration"""
        return self.config.get("debug", {})
    
    def get_system_config(self):
        """Get system configuration"""
        return self.config.get("system", {})
    
    def get_value(self, section, key, default=None):
        """Get a specific configuration value"""
        return self.config.get(section, {}).get(key, default)
    
    def get_credential(self, key, default=None):
        """Get a specific credential"""
        return os.getenv(key, default)
    
    def get_all(self):
        """Get the complete configuration (excluding credentials)"""
        return self.config

# Create a singleton instance
config = Config()

# Simple access functions
def get_credentials():
    return config.get_credentials()

def get_booking_config():
    return config.get_booking_config()

def get_runtime_config():
    return config.get_runtime_config()

def get_debug_config():
    return config.get_debug_config()

def get_system_config():
    return config.get_system_config()

def get_value(section, key, default=None):
    return config.get_value(section, key, default)

def get_credential(key, default=None):
    return config.get_credential(key, default)

def get_all():
    return config.get_all()
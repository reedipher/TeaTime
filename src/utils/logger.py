# src/utils/logger.py
import os
import logging
from datetime import datetime

def setup_logger(name="teatime", log_to_console=True, log_to_file=True):
    """
    Set up a logger that can output to both console and file
    
    Args:
        name: Logger name
        log_to_console: Whether to log to console
        log_to_file: Whether to log to file
    
    Returns:
        logging.Logger: Configured logger
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Clear existing handlers
    if logger.hasHandlers():
        logger.handlers.clear()
    
    # Add console handler
    if log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # Add file handler
    if log_to_file:
        # Ensure logs directory exists
        os.makedirs("artifacts/logs", exist_ok=True)
        
        # Create timestamped log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = f"artifacts/logs/teatime_{timestamp}.log"
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        print(f"Logging to file: {log_file}")
    
    return logger
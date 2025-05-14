# app/utils/logging_utils.py
import logging
import os
from logging.handlers import RotatingFileHandler
import sys

def setup_logging(app=None, log_level=logging.INFO):
    """
    Set up logging for the application
    """
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Basic configuration
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(log_format)
    
    # App logger
    app_logger = logging.getLogger('app')
    app_logger.setLevel(log_level)
    app_logger.handlers = []  # Clear existing handlers
    
    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    app_logger.addHandler(console)
    
    # File handler
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'app.log'),
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    app_logger.addHandler(file_handler)
    
    # Scraper logger
    scraper_logger = logging.getLogger('scraper')
    scraper_logger.setLevel(log_level)
    scraper_logger.handlers = []  # Clear existing handlers
    
    scraper_file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'scraper.log'),
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5
    )
    scraper_file_handler.setFormatter(formatter)
    scraper_logger.addHandler(scraper_file_handler)
    scraper_logger.addHandler(console)
    
    # If Flask app is provided, configure it
    if app:
        # Flask's logger
        app.logger.handlers = []  # Clear existing handlers
        for handler in app_logger.handlers:
            app.logger.addHandler(handler)
        app.logger.setLevel(log_level)
        
        # Log to file unhandled exceptions
        if not app.debug:
            app.logger.info('Setting up production logging...')
    
    return {
        'app_logger': app_logger,
        'scraper_logger': scraper_logger
    }

# test_scraper.py
import os
import sys

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.init import create_app
from app.levitin_scraper import fetch_levitin_updates_comprehensive
from app.utils.logging_utils import setup_logging

if __name__ == "__main__":
    # Set up logging
    loggers = setup_logging(log_level=20)  # INFO level
    logger = loggers['scraper_logger']
    
    logger.info("Starting manual test of the scraper")
    
    # Create app context
    app = create_app()
    
    # Run within app context
    with app.app_context():
        try:
            logger.info("Running comprehensive scraper...")
            articles_added = fetch_levitin_updates_comprehensive()
            logger.info(f"Test completed. Added {articles_added} articles.")
        except Exception as e:
            logger.error(f"Error during testing: {e}", exc_info=True)
            
    logger.info("Test finished.")

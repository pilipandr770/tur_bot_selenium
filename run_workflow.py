#!/usr/bin/env python
# run_workflow.py - Manual test of the full workflow

import os
import sys
import logging
from datetime import datetime

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.init import create_app
from app.utils.logging_utils import setup_logging
from app.models import Article, db
from app.levitin_scraper import fetch_levitin_updates_comprehensive
from app.rewriter import rewrite_text
from app.image_editor import process_image_from_prompt
from app.publisher import send_to_telegram
import uuid

def process_article(app, article_id=None):
    """
    Process a single article through the entire workflow
    """
    with app.app_context():
        logger = app.logger
        
        # Get article to process
        if article_id:
            article = Article.query.get(article_id)
            if not article:
                logger.error(f"Article with ID {article_id} not found")
                return False
        else:
            # Get the oldest unpublished article
            article = Article.query.filter_by(is_posted=False).order_by(Article.created_at).first()
            if not article:
                logger.error("No unpublished articles found")
                return False
        
        try:
            article_id = article.id
            logger.info(f"Processing article ID={article_id}: {article.title}")
            
            # Step 1: Rewrite text
            logger.info(f"Rewriting text for article ID={article_id}")
            article.rewritten_text = rewrite_text(article.original_text)
            
            # If rewriting failed, use original text
            if not article.rewritten_text or article.rewritten_text.startswith("[Error"):
                logger.warning(f"Rewriting failed for ID={article_id}, using original text")
                article.rewritten_text = article.original_text
                
            db.session.commit()
            logger.info(f"Text processed for article ID={article_id}")

            # Step 2: Generate image
            logger.info(f"Generating image for article ID={article_id}")
            
            # Create images directory if it doesn't exist
            images_dir = os.path.join(os.path.dirname(__file__), "images")
            os.makedirs(images_dir, exist_ok=True)
            
            # Generate unique image name
            img_name = f"{uuid.uuid4()}.png"
            save_path = os.path.join(images_dir, img_name)
            
            # Use rewritten text for better image generation
            source_text = article.rewritten_text or article.original_text
            img_path = process_image_from_prompt(source_text, save_path)
            
            if img_path:
                article.image_path = img_path
                db.session.commit()
                logger.info(f"Image generated: {img_path}")
            else:
                logger.warning(f"Image generation failed for ID={article_id}")

            # Step 3: Publish to Telegram
            logger.info(f"Publishing to Telegram: ID={article_id}")
            publish_success = send_to_telegram(
                article.rewritten_text or article.original_text, 
                article.image_path,
                article.url
            )
            
            if publish_success:
                article.is_posted = True
                db.session.commit()
                logger.info(f"Published to Telegram (ID={article_id})")
                return True
            else:
                logger.error(f"Failed to publish to Telegram (ID={article_id})")
                return False

        except Exception as e:
            logger.error(f"Error processing article ID={article_id}: {e}", exc_info=True)
            return False

if __name__ == "__main__":
    # Set up logging
    loggers = setup_logging(log_level=logging.INFO)
    logger = loggers['app_logger']
    
    logger.info(f"=== Starting manual workflow test at {datetime.now()} ===")
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Run tourism content workflow')
    parser.add_argument('--scrape', action='store_true', help='Run scraping step')
    parser.add_argument('--process', action='store_true', help='Run processing step')
    parser.add_argument('--article-id', type=int, help='Process specific article by ID')
    args = parser.parse_args()
    
    # Create app context
    app = create_app()
    
    # Run operations based on arguments
    with app.app_context():
        if args.scrape or not (args.scrape or args.process):  # Default to running both if no args
            logger.info("Running scraping step")
            try:
                articles_added = fetch_levitin_updates_comprehensive()
                logger.info(f"Scraping completed: {articles_added} new articles found")
            except Exception as e:
                logger.error(f"Error during scraping: {e}", exc_info=True)
        
        if args.process or not (args.scrape or args.process):  # Default to running both if no args
            logger.info("Running processing step")
            try:
                if args.article_id:
                    success = process_article(app, args.article_id)
                    logger.info(f"Processing article ID={args.article_id}: {'Success' if success else 'Failed'}")
                else:
                    # Process up to 3 articles
                    processed = 0
                    for _ in range(3):
                        article = Article.query.filter_by(is_posted=False).order_by(Article.created_at).first()
                        if not article:
                            logger.info("No more unpublished articles to process")
                            break
                            
                        success = process_article(app, article.id)
                        if success:
                            processed += 1
                            
                    logger.info(f"Processing completed: {processed} articles processed")
            except Exception as e:
                logger.error(f"Error during processing: {e}", exc_info=True)
    
    logger.info(f"=== Workflow test completed at {datetime.now()} ===")

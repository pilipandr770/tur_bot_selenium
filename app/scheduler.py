# scheduler.py

from apscheduler.schedulers.background import BackgroundScheduler
import pytz
import logging
from datetime import datetime
from app.models import Article, db
from app.levitin_scraper import fetch_levitin_updates_comprehensive
from app.rewriter import rewrite_text
from app.image_editor import process_image_from_prompt
from app.publisher import send_to_telegram
import os, uuid

# Set up logger
logger = logging.getLogger('app.scheduler')

def start_scheduler(app):
    """
    Starts scheduled tasks:
    1. Scraping task - once a day at 9:00 AM
    2. Processing and publishing task - every 2 hours (one article per run)
    """
    scheduler = BackgroundScheduler(timezone=pytz.timezone('Europe/Berlin'))
    
    # Task 1: Scrape new articles once a day at 9:00 AM
    @scheduler.scheduled_job('cron', hour=9, minute=0)
    def scrape_task():
        with app.app_context():
            app.logger.info(f"[{datetime.now()}] Starting daily scraping task")
            try:
                new_articles = fetch_levitin_updates_comprehensive()
                app.logger.info(f"Scraping completed: {new_articles} new articles found")
            except Exception as e:
                app.logger.error(f"Error in scraping task: {e}", exc_info=True)
    
    # Task 2: Process and publish articles every 2 hours, one article per run
    @scheduler.scheduled_job('interval', hours=2)
    def process_and_publish():
        with app.app_context():
            app.logger.info(f"[{datetime.now()}] Starting processing and publishing task")
            
            # Get ONE unpublished article per run
            pending = Article.query.filter_by(is_posted=False).order_by(Article.created_at).limit(1).all()
            app.logger.info(f"Found {len(pending)} articles for processing")

            for art in pending:
                try:
                    app.logger.info(f"Processing article ID={art.id}: {art.title}")
                    
                    # 1) Skip this article if too short
                    if not art.original_text or len(art.original_text.strip()) < 50:
                        app.logger.warning(f"Article ID={art.id} text too short, marking as posted")
                        art.is_posted = True
                        db.session.commit()
                        continue
                    
                    # 2) Rewrite text if not already rewritten
                    if not art.rewritten_text:
                        app.logger.info(f"Rewriting text for article ID={art.id}")
                        art.rewritten_text = rewrite_text(art.original_text)
                        
                        # If rewriting failed, use original text
                        if not art.rewritten_text or art.rewritten_text.startswith("[Error"):
                            app.logger.warning(f"Rewriting failed for ID={art.id}, using original text")
                            art.rewritten_text = art.original_text
                            
                        db.session.commit()
                        app.logger.info(f"Text processed for article ID={art.id}")

                    # 3) Generate image if needed
                    if not art.image_path:
                        app.logger.info(f"Generating image for article ID={art.id}")
                        
                        # Create images directory if it doesn't exist
                        images_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "images")
                        os.makedirs(images_dir, exist_ok=True)
                        
                        # Generate unique image name
                        img_name = f"{uuid.uuid4()}.png"
                        save_path = os.path.join(images_dir, img_name)
                        
                        # Use rewritten text for better image generation
                        source_text = art.rewritten_text or art.original_text
                        img_path = process_image_from_prompt(source_text, save_path)
                        
                        if img_path:
                            art.image_path = img_path
                            db.session.commit()
                            app.logger.info(f"Image generated: {img_path}")
                        else:
                            app.logger.warning(f"Image generation failed for ID={art.id}")

                    # 4) Publish to Telegram
                    app.logger.info(f"Publishing to Telegram: ID={art.id}")
                    publish_success = send_to_telegram(
                        art.rewritten_text or art.original_text, 
                        art.image_path,
                        art.url
                    )
                    
                    if publish_success:
                        art.is_posted = True
                        db.session.commit()
                        app.logger.info(f"Published to Telegram (ID={art.id})")
                    else:
                        app.logger.error(f"Failed to publish to Telegram (ID={art.id})")

                except Exception as e:
                    app.logger.error(f"Error processing article ID={art.id}: {e}", exc_info=True)
    
    # Start the scheduler
    scheduler.start()
    app.logger.info("Scheduler started successfully")

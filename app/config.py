# app/config.py
import os
import logging

class Config:
    # Database settings
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///data.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # OpenAI settings
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_ASSISTANT_ID = os.getenv("OPENAI_ASSISTANT_ID")
    
    # DALL-E settings
    DALLE_MODEL = os.getenv("DALLE_MODEL", "dall-e-3")
    DALLE_SIZE = os.getenv("DALLE_SIZE", "1024x1024")
    DALLE_QUALITY = os.getenv("DALLE_QUALITY", "standard")

    # RSS Feed
    RSS_FEED_URL = os.getenv("RSS_FEED_URL")    # Telegram settings
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # Поддержка имени TELEGRAM_BOT_TOKEN из docker-compose
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    
    # Scheduler settings
    SCRAPE_INTERVAL_MINUTES = int(os.getenv("SCRAPE_INTERVAL_MINUTES", "60"))
    PUBLISH_INTERVAL_MINUTES = int(os.getenv("PUBLISH_INTERVAL_MINUTES", "10"))
    MAX_ARTICLES_PER_RUN = int(os.getenv("MAX_ARTICLES_PER_RUN", "3"))
    
    # Logging settings
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_LEVEL_VALUE = getattr(logging, LOG_LEVEL.upper(), logging.INFO)

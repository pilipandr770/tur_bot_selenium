# app/publisher.py
import requests
from flask import current_app
import os
import logging
import re
import time
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger('app.publisher')

def format_article_for_telegram(text: str, url: Optional[str] = None) -> str:
    """
    Formats article text for Telegram with proper HTML markup
    """
    if not text:
        return ""
    
    # Extract title from the first line
    lines = text.strip().split('\n')
    title = lines[0] if lines else "Новая статья"
    
    # Clean and format the text
    content = "\n\n".join(lines[1:]) if len(lines) > 1 else ""
    
    # Replace HTML special characters
    text_escaped = text.replace('<', '&lt;').replace('>', '&gt;')
    
    # Create paragraphs and add formatting
    paragraphs = re.split(r'\n{2,}', text_escaped)
    formatted_text = ""
    
    # Add title
    formatted_text += f"<b>{title}</b>\n\n"
    
    # Add content paragraphs
    for i, paragraph in enumerate(paragraphs[1:6] if len(paragraphs) > 1 else []):  # Limit to 5 paragraphs
        if paragraph.strip():
            formatted_text += f"{paragraph.strip()}\n\n"
    
    # Add URL if provided
    if url:
        formatted_text += f"\n<a href=\"{url}\">Читать полностью</a>"
    
    # Ensure the final text is within Telegram limits
    if len(formatted_text) > 4000:
        formatted_text = formatted_text[:3997] + "..."
        
    return formatted_text

def send_to_telegram(text: str, image_path: Optional[str] = None, url: Optional[str] = None, max_retries: int = 3) -> bool:
    """
    Send article and optional image to Telegram
    
    Args:
        text: The text to send
        image_path: Optional path to an image to include
        url: Optional URL to the original article
        max_retries: Maximum number of retry attempts
        
    Returns:
        True if successful, False otherwise
    """
    if not text:
        logger.warning("Attempted to send empty text to Telegram")
        return False
    
    try:
        token = current_app.config.get('TELEGRAM_TOKEN')
        chat_id = current_app.config.get('TELEGRAM_CHAT_ID')
        
        if not token or not chat_id:
            logger.error("Telegram token or chat ID not configured")
            return False
            
        # Format the text with proper markup
        formatted_text = format_article_for_telegram(text, url)
        logger.info(f"Sending article to Telegram (length: {len(formatted_text)} chars)")
        
        success = False
        
        # 1) Send image if provided
        if image_path and os.path.exists(image_path):
            logger.info(f"Attaching image: {image_path}")
            
            # Send with caption if text is short enough, otherwise send image first
            if len(formatted_text) <= 1024:
                # Image with caption
                for attempt in range(max_retries):
                    try:
                        with open(image_path, 'rb') as photo:
                            photo_resp = requests.post(
                                f"https://api.telegram.org/bot{token}/sendPhoto",
                                data={
                                    'chat_id': chat_id,
                                    'caption': formatted_text,
                                    'parse_mode': 'HTML'
                                },
                                files={'photo': photo},
                                timeout=30
                            )
                            
                        if photo_resp.status_code == 200:
                            logger.info("Successfully sent image with caption to Telegram")
                            return True
                        else:
                            logger.warning(f"Attempt {attempt+1}/{max_retries} - Error sending photo to Telegram: {photo_resp.text}")
                            if attempt < max_retries - 1:
                                time.sleep(2)
                    except Exception as e:
                        logger.error(f"Attempt {attempt+1}/{max_retries} - Error sending photo to Telegram: {e}")
                        if attempt < max_retries - 1:
                            time.sleep(2)
                
                # If sending with caption failed, fall through to sending image and text separately
            
            # Send image first, then text
            try:
                with open(image_path, 'rb') as photo:
                    photo_resp = requests.post(
                        f"https://api.telegram.org/bot{token}/sendPhoto",
                        data={'chat_id': chat_id},
                        files={'photo': photo},
                        timeout=30
                    )
                    
                if photo_resp.status_code == 200:
                    logger.info("Successfully sent image to Telegram")
                else:
                    logger.error(f"Error sending photo to Telegram: {photo_resp.text}")
            except Exception as e:
                logger.error(f"Exception sending photo to Telegram: {e}")
                
        # 2) Send text (either after image or standalone)
        for attempt in range(max_retries):
            try:
                msg_resp = requests.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    data={
                        'chat_id': chat_id,
                        'text': formatted_text,
                        'parse_mode': 'HTML',
                        'disable_web_page_preview': True
                    },
                    timeout=30
                )
                
                if msg_resp.status_code == 200:
                    logger.info("Successfully sent text to Telegram")
                    return True
                else:
                    logger.warning(f"Attempt {attempt+1}/{max_retries} - Error sending text to Telegram: {msg_resp.text}")
                    
                    # If HTML parsing failed, try sending without HTML
                    if "can't parse entities" in msg_resp.text.lower():
                        plain_text = re.sub(r'<.*?>', '', formatted_text)
                        msg_resp = requests.post(
                            f"https://api.telegram.org/bot{token}/sendMessage",
                            data={
                                'chat_id': chat_id,
                                'text': plain_text[:4000],
                                'disable_web_page_preview': True
                            },
                            timeout=30
                        )
                        
                        if msg_resp.status_code == 200:
                            logger.info("Successfully sent plain text to Telegram (HTML failed)")
                            return True
                    
                    if attempt < max_retries - 1:
                        time.sleep(2)
            except Exception as e:
                logger.error(f"Attempt {attempt+1}/{max_retries} - Exception sending text to Telegram: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)

        return False

    except Exception as e:
        logger.error(f"Unexpected error sending to Telegram: {e}", exc_info=True)
        return False

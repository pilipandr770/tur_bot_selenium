# app/image_editor.py
import openai
import requests
import logging
from flask import current_app
import os
import time
import re
from typing import Optional, Dict, Any, List, Tuple

# Set up logger
logger = logging.getLogger('app.image_editor')

def extract_topic_keywords(text: str, max_keywords: int = 5) -> List[str]:
    """
    Extract the most important keywords from the text for better image generation
    """
    # Simple keyword extraction by removing common words and keeping nouns
    if not text:
        return []
        
    # Take first 1000 chars for analysis
    text = text[:1000].lower()
    
    # Split into words and filter
    words = re.findall(r'\b[а-яА-Яa-zA-Z]{4,}\b', text)
    
    # Remove common stop words (English and Russian)
    stop_words = {'and', 'the', 'of', 'in', 'to', 'with', 'as', 'for', 'by', 'и', 'в', 'на', 'с', 'по', 'для', 'как', 'что', 'от'}
    filtered_words = [w for w in words if w not in stop_words]
    
    # Count frequency
    word_counts = {}
    for word in filtered_words:
        word_counts[word] = word_counts.get(word, 0) + 1
    
    # Get most common words
    sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
    top_keywords = [word for word, _ in sorted_words[:max_keywords]]
    
    return top_keywords

def create_image_prompt(article_text: str) -> str:
    """
    Creates an optimized prompt for image generation based on article text
    """
    # Extract a clean title
    title_match = re.search(r'^(.+?)(?:\n|$)', article_text.strip())
    title = title_match.group(1) if title_match else ""
    
    # Extract keywords
    keywords = extract_topic_keywords(article_text)
    keyword_text = ", ".join(keywords)
    
    # Create the prompt
    prompt = (
        f"Create a photorealistic travel image for an article titled '{title}'. "
        f"Key themes: {keyword_text}. "
        f"Style: professional photography, bright, attractive tourism destination. "
        "No text, logos, watermarks, or people. Natural travel scenery only."
    )
    
    return prompt

def process_image_from_prompt(article_text: str, save_path: str, max_retries: int = 3) -> Optional[str]:
    """
    Generates an image using DALL-E based on the article text and saves it.
    
    Args:
        article_text: The text of the article to generate an image for
        save_path: Path where the generated image should be saved
        max_retries: Maximum number of retry attempts
        
    Returns:
        Path to the saved image or None if generation failed
    """
    try:
        api_key = current_app.config.get('OPENAI_API_KEY')
        if not api_key:
            logger.error("OpenAI API key not configured")
            return None
            
        openai.api_key = api_key
        model = current_app.config.get('DALLE_MODEL', 'dall-e-3')
        size = current_app.config.get('DALLE_SIZE', '1024x1024')
        
        # Create optimized prompt
        prompt = create_image_prompt(article_text)
        logger.info(f"Generating image with prompt: {prompt}")
        
        # Implement retry logic
        for attempt in range(max_retries):
            try:
                # Using the new client-based API for OpenAI v1.0+
                response = openai.images.generate(
                    prompt=prompt,
                    n=1,
                    size=size,
                    model=model,
                    quality=current_app.config.get('DALLE_QUALITY', 'standard')
                )
                
                if not response or not hasattr(response, 'data') or not response.data:
                    logger.error("Invalid response from OpenAI Image API")
                    if attempt < max_retries - 1:
                        time.sleep(2 * (attempt + 1))  # Exponential backoff
                        continue
                    return None
                
                # New API returns data differently
                image_url = response.data[0].url
                break  # Success
                
            except Exception as e:
                logger.error(f"Attempt {attempt+1}/{max_retries} - Error generating image: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 * (attempt + 1))  # Exponential backoff
                    continue
                return None
        
        # Download the generated image
        try:
            image_response = requests.get(image_url, timeout=30)
            image_response.raise_for_status()  # Raise exception for 4XX/5XX responses
            image_data = image_response.content
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
            
            # Save the image
            with open(save_path, 'wb') as f:
                f.write(image_data)
                
            logger.info(f"Image successfully saved to: {save_path}")
            return save_path
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error downloading image: {e}")
            return None
            
    except Exception as e:
        logger.error(f"Unexpected error in image generation: {e}", exc_info=True)
        return None

# app/rewriter.py
import openai
import time
import logging
from flask import current_app

logger = logging.getLogger('app.rewriter')

def rewrite_text(original_text: str, max_retries=3, delay=2) -> str:
    """
    Rewrites text using OpenAI's assistant API
    
    Args:
        original_text: The text to rewrite
        max_retries: Maximum number of retry attempts
        delay: Delay between retries
        
    Returns:
        Rewritten text or error message
    """
    if not original_text or len(original_text.strip()) < 10:
        logger.warning("Text too short to rewrite")
        return "Text too short to rewrite properly."
        
    try:
        openai.api_key = current_app.config.get('OPENAI_API_KEY')
        assistant_id = current_app.config.get('OPENAI_ASSISTANT_ID')
        
        if not openai.api_key:
            logger.error("OpenAI API key not configured")
            return f"[OpenAI API key not configured. Original: {original_text[:100]}...]"
            
        if not assistant_id:
            logger.error("OpenAI Assistant ID not configured")
            return f"[OpenAI Assistant ID not configured. Original: {original_text[:100]}...]"
            
        logger.info(f"Rewriting text of length {len(original_text)}")
        
        # Create a new thread with retry logic
        thread = None
        run = None
        
        for attempt in range(max_retries):
            try:
                thread = openai.beta.threads.create()
                openai.beta.threads.messages.create(
                    thread_id=thread.id,
                    role="user",
                    content=original_text
                )
                run = openai.beta.threads.runs.create(
                    thread_id=thread.id,
                    assistant_id=assistant_id
                )
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(f"Retry {attempt+1}/{max_retries} after error: {e}")
                time.sleep(delay)
        
        # Wait for completion with timeout
        max_wait_time = 120  # 2 minutes
        start_time = time.time()
        poll_interval = 2  # seconds
        
        logger.info(f"Waiting for OpenAI processing to complete")
        
        while True:
            try:
                run = openai.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
                
                if run.status == "completed":
                    logger.info("Rewriting completed successfully")
                    break
                    
                if run.status in ["failed", "cancelled", "expired"]:
                    logger.error(f"Rewrite failed with status: {run.status}")
                    return f"[Rewriting failed with status: {run.status}. Original: {original_text[:100]}...]"
                    
                # Check for timeout
                if time.time() - start_time > max_wait_time:
                    logger.error(f"Rewrite timed out after {max_wait_time} seconds")
                    return f"[Rewriting timed out. Original: {original_text[:100]}...]"
                    
                time.sleep(poll_interval)
            except Exception as e:
                logger.error(f"Error while checking run status: {e}")
                return f"[Error during rewriting: {str(e)}. Original: {original_text[:100]}...]"

        # Get the assistant's response
        try:
            messages = openai.beta.threads.messages.list(thread_id=thread.id)
            reply = next((m for m in reversed(messages.data) if m.role == "assistant"), None)
            
            if reply and hasattr(reply, 'content') and reply.content:
                content_text = reply.content[0].text.value if reply.content[0].type == 'text' else None
                if content_text:
                    logger.info(f"Successfully retrieved rewritten content of length {len(content_text)}")
                    return content_text
                    
            logger.error("No valid content found in the assistant's response")
            return f"[No valid content in response. Original: {original_text[:100]}...]"
        except Exception as e:
            logger.error(f"Error retrieving message content: {e}")
            return f"[Error retrieving content: {str(e)}. Original: {original_text[:100]}...]"
        
    except Exception as e:
        logger.error(f"Unexpected error during text rewriting: {e}", exc_info=True)
        return f"[Error in rewriting process: {str(e)}. Original: {original_text[:100]}...]"

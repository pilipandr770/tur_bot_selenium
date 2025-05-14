# Tourism Website Content Automation Bot

This system automatically scrapes travel articles from levitin.de, rewrites them using OpenAI's API, generates images based on the content, and publishes everything to a Telegram channel. The bot is designed to work autonomously, scraping new content daily and publishing it on a schedule you define.

## Features

- **Automated web scraping** of tourism articles from levitin.de
- **AI-powered content rewriting** using OpenAI's GPT models
- **Image generation** based on article content using DALL-E
- **Scheduled publication** to Telegram channels
- **Health monitoring** and management utilities
- **Docker support** for easy deployment

## Docker Deployment

You can easily deploy this system using Docker:

```bash
# Build and run the containers
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the containers
docker-compose down
```

Before running with Docker, create a `.env` file with your API keys:
```
OPENAI_API_KEY=your_openai_api_key
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
```

### Security Features

The Docker deployment includes enhanced security measures:

- Specific stable Python version (3.10.13-slim-bookworm) instead of generic tags
- Non-privileged user execution inside container
- Resource limits (memory: 2GB, CPU: 1 core)
- Exposed services only on localhost (127.0.0.1)
- No new privileges security option
- Integrated health check (every 1 minute)
- Removal of package lists after installation
- Non-writable Python bytecode
- Clean separation of data with volume mounts

### Health Monitoring

The application includes a health endpoint at the root URL providing:

- Overall application status
- Database connection status and article count
- Configuration verification 
- Disk space availability
- Timestamp for monitoring purposes

### Management Utilities

A management script (`manage.py`) is provided to help with administration:

```bash
# Check system health status
python manage.py health

# Clean old images (older than 30 days by default)
python manage.py clean --images=30

# Truncate log files (keep last 1000 lines)
python manage.py clean --logs

# Show help
python manage.py --help
```

When running in Docker, access these utilities with:
```bash
docker-compose exec app python manage.py [command]
```

## System Components

### 1. Web Scraper (`levitin_scraper.py`)
- Scrapes articles from levitin.de using multiple approaches:
  - Selenium for handling dynamic Angular content
  - Direct API calls when possible
- Intelligent selection of content based on multiple selectors
- Error handling and retry mechanisms

### 2. Content Rewriter (`rewriter.py`)
- Uses OpenAI's API to rewrite the scraped content
- Implements error handling and fallbacks
- Handles rate limiting and timeouts

### 3. Image Generator (`image_editor.py`)
- Generates images using DALL-E based on article content
- Extracts key topics from text for better prompts
- Implements retry logic for API failures

### 4. Telegram Publisher (`publisher.py`)
- Posts rewritten content and images to Telegram
- Formats text with proper HTML
- Handles errors and retry logic

### 5. Scheduler (`scheduler.py`)
- Runs two separate tasks:
  - Scraping task every 60 minutes
  - Content processing and publishing every 10 minutes
- Limits processing to 3 articles per run to avoid API rate limits

### 6. Database Model (`models.py`)
- Article model with the following fields:
  - original_text: Raw scraped content
  - rewritten_text: Content after AI rewriting
  - image_path: Path to generated image
  - is_posted: Publishing status
  - title: Article title
  - summary: Brief description
  - url: Original article URL
  - source_name: Source website
  - publish_at: Timestamp

## Setup Instructions

1. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up environment variables in `.env` file:
   ```
   DATABASE_URL=sqlite:////absolute/path/to/instance/test.db
   OPENAI_API_KEY=your_openai_api_key
   OPENAI_ASSISTANT_ID=your_openai_assistant_id
   TELEGRAM_TOKEN=your_telegram_bot_token
   TELEGRAM_CHAT_ID=your_telegram_chat_id
   ```

4. Initialize the database:
   ```
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```

5. Run the application:
   ```
   python -m app.run
   ```

## Testing

You can manually test the scraper using:
```
python test_scraper.py
```

## Debugging

Debug files are stored in the `debug` directory, including:
- HTML content from scraped pages
- API responses

Logs are stored in the `logs` directory:
- `app.log` - General application logs
- `scraper.log` - Web scraper specific logs

## Recent Improvements

- Enhanced scraping logic to handle Angular applications
- Added multiple approaches (Selenium and API) to maximize content extraction
- Improved error handling and logging throughout the system
- Separated scheduling into discrete scraping and publishing tasks
- Added proper retry mechanisms for all external API calls
- Implemented deep content extraction for articles by following URLs
- Added detailed logging and debugging capabilities

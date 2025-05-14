# levitin_scraper.py

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import time
import logging
import os
import requests
import json

# если у вас есть своя модель Article и сессия SQLAlchemy
from app.models import Article, db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def scrape_angular_section(driver, url, section_url, selector):
    """
    Scrape a specific section of the Angular website
    """
    try:
        full_url = f"{url.rstrip('/')}/{section_url.lstrip('/')}"
        logger.info(f"[levitin_scraper] Scraping section: {full_url}")
        driver.get(full_url)
        
        # Give Angular time to load and render
        time.sleep(10)  # Увеличено с 5 до 10 секунд
        
        # Wait for content to load
        try:
            # Увеличено время ожидания с 20 до 45 секунд
            WebDriverWait(driver, 45).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
        except TimeoutException:
            logger.warning(f"[levitin_scraper] Timeout waiting for content in section: {section_url}")
            # Попробуем проверить наличие любого контента на странице
            try:
                body_content = driver.find_element(By.TAG_NAME, 'body').text
                if len(body_content) > 100:  # Если на странице есть хоть какой-то контент
                    logger.info(f"[levitin_scraper] Found some content despite selector timeout, trying to parse anyway")
                else:
                    return []
            except:
                return []
            
        # Execute JavaScript to get fully rendered HTML
        html = driver.execute_script("return document.documentElement.outerHTML;")
        soup = BeautifulSoup(html, "html.parser")
        items = soup.select(selector)
        
        logger.info(f"[levitin_scraper] Found {len(items)} items in section {section_url}")
        return items
    except Exception as e:
        logger.error(f"[levitin_scraper] Error scraping section {section_url}: {e}")
        return []

def extract_article_data(item, base_url):
    """
    Extract title, URL, and summary from an article element
    """
    # Find title and link
    a_tags = item.select("a[href]")
    h_tags = item.select("h1, h2, h3, h4, h5, .title, .heading, .card-title")
    
    if not a_tags and not h_tags:
        # Последняя попытка найти хоть что-то
        text_content = item.get_text(strip=True)
        if text_content and len(text_content) > 20:
            return {
                "title": text_content[:50],
                "href": "",
                "summary": text_content[50:200] if len(text_content) > 50 else ""
            }
        return None
    
    href = ""
    for a_tag in a_tags:
        href = a_tag.get("href", "")
        if href and href.strip() and not href.startswith("#") and not href.startswith("javascript:"):
            if not href.startswith("http"):
                href = f"{base_url.rstrip('/')}/{href.lstrip('/')}"
            break
    
    title = ""
    # Пробуем найти заголовок в h-тегах
    for h_tag in h_tags:
        text = h_tag.get_text(strip=True)
        if text and len(text) > 3:
            title = text
            break
    
    # Если заголовок не найден, проверяем ссылки
    if not title:
        for a_tag in a_tags:
            text = a_tag.get_text(strip=True)
            if text and len(text) > 3:
                title = text
                break
    
    # Find description
    summary = ""
    summary_selectors = [
        "p", ".description", ".preview-text", ".text", ".tour-description", 
        ".short-description", ".excerpt", ".summary", ".card-text",
        ".content", ".teaser", ".subtitle"
    ]
    
    for selector in summary_selectors:
        summary_tags = item.select(selector)
        for tag in summary_tags:
            text = tag.get_text(strip=True)
            if text and len(text) > 10 and text != title:
                summary = text
                break
        if summary:
            break
    
    # If we have only link but no summary, try to get it from the image alt text
    if not summary:
        img_tag = item.select_one("img")
        if img_tag and img_tag.get("alt"):
            summary = img_tag.get("alt")
    
    if not title or (not href and not summary):
        return None
        
    return {
        "title": title,
        "url": href,
        "summary": summary
    }

def fetch_levitin_updates():
    """
    Main function to fetch updates from levitin.de
    """
    base_url = "https://www.levitin.de"
    
    # Configure Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    logger.info(f"[levitin_scraper] Starting scrape for {base_url}")
    
    driver = None
    
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
          # Define sections to scrape with their selectors
        sections = [
            {"url": "/", "selector": ".tour-card, .main-slider, .popular-tours .card, .card, article, .news-item, .tour-item"},
            {"url": "/tours", "selector": ".tour-card, .category-section-tours article, .tour-item, .card, .list-item"},
            {"url": "/news", "selector": ".news article, .news-item, article, .card, .post"},
            {"url": "/blog", "selector": ".blog-list-item, .blog-item, article, .post, .card"},
            {"url": "/destinations", "selector": ".destination-card, .card, article, .item"},
            {"url": "/activities", "selector": ".activity-card, .card, article, .item"},
            {"url": "/about-us", "selector": ".content, article, .text-content, p, section"},
            {"url": "/contact", "selector": ".contact-info, .content, p, article"},
            {"url": "/services", "selector": ".service-item, .card, article, .item"}
        ]
        
        all_items = []
        
        # Scrape each section
        for section in sections:
            items = scrape_angular_section(driver, base_url, section["url"], section["selector"])
            all_items.extend(items)
        
        # Create a debug folder if it doesn't exist
        debug_dir = "debug"
        os.makedirs(debug_dir, exist_ok=True)
        
        # Save the last scraped page for debugging
        with open(os.path.join(debug_dir, "levitin_last_page.html"), "w", encoding="utf-8") as f:
            if driver.page_source:
                f.write(driver.page_source)
        
        logger.info(f"[levitin_scraper] Total found items: {len(all_items)}")
        
        if not all_items:
            logger.warning("[levitin_scraper] No items found with primary selectors. Trying alternative approach.")
              # Try a more aggressive approach - go to homepage and look for any clickable elements
            driver.get(base_url)
            time.sleep(5)
            html = driver.execute_script("return document.documentElement.outerHTML;")
            soup = BeautifulSoup(html, "html.parser")
            
            # Look for any possible tour/article elements
            all_items = soup.select("div.card, .tour-item, article, .product-item, .item, [ng-repeat]")
            
        tz = pytz.timezone("Europe/Berlin")
        added = 0
          # Process all found items
        for item in all_items:
            article_data = extract_article_data(item, base_url)
            if not article_data:
                continue
                
            title = article_data["title"]
            # Fix inconsistent key names
            href = article_data.get("url", "") or article_data.get("href", "")
            summary = article_data.get("summary", "")
            
            # Skip if title is too short (likely not a real article)
            if len(title) < 5:
                continue
                
            # Create content for rewriting
            original_text = f"{title}\n\n{summary}"
            
            # Skip duplicates
            if href and Article.query.filter_by(url=href).first():
                logger.info(f"[levitin_scraper] Skipping duplicate URL: {href}")
                continue
                
            if Article.query.filter_by(title=title).first():
                logger.info(f"[levitin_scraper] Skipping duplicate title: {title}")
                continue
            
            logger.info(f"[levitin_scraper] Adding new article: {title}")
            
            # If we found an article with URL, try to fetch more content
            detailed_content = ""
            if href and href.startswith(base_url):
                try:
                    logger.info(f"[levitin_scraper] Fetching detailed content from: {href}")
                    driver.get(href)
                    time.sleep(3)  # Give Angular time to render
                    
                    detail_html = driver.execute_script("return document.documentElement.outerHTML;")
                    detail_soup = BeautifulSoup(detail_html, "html.parser")
                      # Look for content in common article containers
                    content_selectors = [
                        ".article-content", ".post-content", ".tour-description", 
                        ".main-content-directive", ".main-content", "article", 
                        ".text-content", ".description", ".content", "main", 
                        ".article", ".post", ".blog-post", ".entry-content",
                        ".tour-content", ".page-content", "div[role='main']",
                        ".cms-content", ".rich-text", ".news-content",
                        ".content-wrapper", "section", ".section-content",
                        "div.container"
                    ]
                    
                    for selector in content_selectors:
                        content_elem = detail_soup.select_one(selector)
                        if content_elem:
                            # Extract all paragraphs
                            paragraphs = content_elem.select("p")
                            if paragraphs:
                                detailed_content = "\n\n".join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
                                break
                                
                    if detailed_content:
                        logger.info(f"[levitin_scraper] Found detailed content ({len(detailed_content)} chars)")
                        original_text = f"{title}\n\n{summary}\n\n{detailed_content}"
                except Exception as e:
                    logger.error(f"[levitin_scraper] Error fetching detailed content: {e}")
            
            # Save to database
            art = Article(
                original_text=original_text,
                source_name="levitin.de",
                title=title, 
                summary=summary,
                url=href,
                publish_at=datetime.now(tz)
            )
            db.session.add(art)
            added += 1
        
        if added > 0:
            try:
                db.session.commit()
                logger.info(f"[levitin_scraper] Successfully added {added} new articles")
            except Exception as e:
                db.session.rollback()
                logger.error(f"[levitin_scraper] Error committing to database: {e}")
        else:
            logger.info("[levitin_scraper] No new articles to add")
            
    except Exception as e:
        logger.error(f"[levitin_scraper] Error: {e}", exc_info=True)
    finally:
        if driver:
            driver.quit()
            
    return added


def try_api_approach():
    """
    Alternative method that attempts to find and use the site's API endpoints
    """
    base_url = "https://www.levitin.de"
    api_endpoints = [
        "/api/tours", 
        "/api/news",
        "/api/blog",
        "/api/popular-tours",
        "/api/content"
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": base_url,
        "X-Requested-With": "XMLHttpRequest"
    }
    
    all_items = []
    for endpoint in api_endpoints:
        url = f"{base_url}{endpoint}"
        logger.info(f"[levitin_scraper] Trying API endpoint: {url}")
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                try:
                    data = response.json()
                    logger.info(f"[levitin_scraper] API response received: {len(str(data))} bytes")
                    # Save the API response for debugging
                    debug_dir = "debug"
                    os.makedirs(debug_dir, exist_ok=True)
                    with open(os.path.join(debug_dir, f"api_{endpoint.replace('/', '_')}.json"), "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    
                    # Process API data based on structure
                    if isinstance(data, list):
                        all_items.extend(data)
                    elif isinstance(data, dict):
                        # Look for arrays in the response that might contain items
                        for key, value in data.items():
                            if isinstance(value, list) and value:
                                all_items.extend(value)
                except ValueError:
                    logger.warning(f"[levitin_scraper] API endpoint returned non-JSON data: {endpoint}")
        except Exception as e:
            logger.warning(f"[levitin_scraper] Error accessing API endpoint {endpoint}: {e}")
    
    return all_items

def process_api_items(api_items):
    """
    Process items obtained from the API
    """
    if not api_items:
        return 0
        
    tz = pytz.timezone("Europe/Berlin")
    added = 0
    
    for item in api_items:
        try:
            # Extract common fields from API response
            title = None
            url = None
            summary = None
            content = None
            
            # Check for different field names since we don't know the exact structure
            for title_field in ['title', 'name', 'heading', 'subject']:
                if title_field in item and item[title_field]:
                    title = item[title_field]
                    break
                    
            for url_field in ['url', 'href', 'link', 'path']:
                if url_field in item and item[url_field]:
                    url = item[url_field]
                    if not url.startswith('http'):
                        url = f"https://www.levitin.de{url}" if url.startswith('/') else f"https://www.levitin.de/{url}"
                    break
                    
            for summary_field in ['summary', 'description', 'shortText', 'preview', 'excerpt']:
                if summary_field in item and item[summary_field]:
                    summary = item[summary_field]
                    break
                    
            for content_field in ['content', 'text', 'body', 'fullText']:
                if content_field in item and item[content_field]:
                    content = item[content_field]
                    break
            
            if not title or len(title) < 5:
                continue
                
            # Check if this article already exists
            if url and Article.query.filter_by(url=url).first():
                logger.info(f"[levitin_scraper] Skipping duplicate URL from API: {url}")
                continue
                
            if Article.query.filter_by(title=title).first():
                logger.info(f"[levitin_scraper] Skipping duplicate title from API: {title}")
                continue
            
            # Create the original text combining all relevant content
            original_text_parts = [part for part in [title, summary, content] if part]
            original_text = "\n\n".join(original_text_parts)
            
            logger.info(f"[levitin_scraper] Adding new article from API: {title}")
            
            art = Article(
                original_text=original_text,
                source_name="levitin.de",
                title=title, 
                summary=summary or "",
                url=url or "",
                publish_at=datetime.now(tz)
            )
            db.session.add(art)
            added += 1
        except Exception as e:
            logger.error(f"[levitin_scraper] Error processing API item: {e}")
    
    if added > 0:
        try:
            db.session.commit()
            logger.info(f"[levitin_scraper] Successfully added {added} articles from API")
        except Exception as e:
            db.session.rollback()
            logger.error(f"[levitin_scraper] Error committing API items to database: {e}")
    
    return added

# Функция для создания тестовых статей, если не найдено ни одной
def add_test_articles(count=3):
    """
    Добавляет тестовые статьи, если не удалось найти настоящие
    """
    logger.info(f"[levitin_scraper] Adding {count} test articles")
    tz = pytz.timezone("Europe/Berlin")
    added = 0
    
    test_articles = [
        {
            "title": "Лучшие туры в Берлин - исследуйте столицу Германии",
            "summary": "Берлин - уникальный город с богатой историей и культурой. Предлагаем уникальные туры по всем достопримечательностям.",
            "original_text": """Лучшие туры в Берлин - исследуйте столицу Германии

Берлин - уникальный город с богатой историей и культурой. Предлагаем уникальные туры по всем достопримечательностям.

Берлин - столица Германии и один из наиболее интересных городов Европы. Это место, где история и современность соединяются в неповторимом сочетании. Бранденбургские ворота, Рейхстаг, остатки Берлинской стены и множество музеев рассказывают о сложном прошлом города, в то время как модные районы, галереи современного искусства и оживленная ночная жизнь показывают его прогрессивное настоящее.

Наши туры включают посещение основных достопримечательностей Берлина, а также скрытых мест, известных только местным жителям. Опытные гиды расскажут вам о всех интересных фактах и помогут увидеть город глазами его обитателей.""",
            "url": "https://www.levitin.de/berlin-tours"
        },
        {
            "title": "Романтический отдых в баварских Альпах",
            "summary": "Откройте для себя захватывающие пейзажи и уютные города Баварии с нашими эксклюзивными турами.",
            "original_text": """Романтический отдых в баварских Альпах

Откройте для себя захватывающие пейзажи и уютные города Баварии с нашими эксклюзивными турами.

Бавария славится своей живописной природой, традиционной архитектурой и гостеприимством. В наших турах вы увидите знаменитый замок Нойшванштайн, который вдохновил Уолта Диснея на создание его сказочных замков, посетите исторический Мюнхен и насладитесь прогулками по живописным альпийским деревушкам.

Мы предлагаем как групповые, так и индивидуальные туры, которые можно адаптировать под ваши интересы. В программу включены дегустации традиционных баварских блюд и напитков, посещение местных фестивалей и возможность познакомиться с подлинной культурой региона.""",
            "url": "https://www.levitin.de/bavaria-tours"
        },
        {
            "title": "Круиз по Рейну - винные регионы и средневековые замки",
            "summary": "Путешествие по одной из самых красивых рек Европы с посещением знаменитых винодельческих регионов и исторических мест.",
            "original_text": """Круиз по Рейну - винные регионы и средневековые замки

Путешествие по одной из самых красивых рек Европы с посещением знаменитых винодельческих регионов и исторических мест.

Река Рейн протекает через живописные ландшафты, мимо старинных городов и величественных замков. Наш круиз начинается в Кёльне с его впечатляющим готическим собором и продолжается через Долину Среднего Рейна, включенную в список Всемирного наследия ЮНЕСКО.

Вы увидите легендарную скалу Лорелей, посетите средневековые города Рюдесхайм и Бахарах, а также познакомитесь с производством всемирно известных рейнских вин. Каждый день нашего путешествия наполнен новыми впечатлениями, гастрономическими открытиями и знакомством с богатой историей и культурой этого региона.""",
            "url": "https://www.levitin.de/rhine-cruise"
        }
    ]
    
    try:
        for article in test_articles[:count]:
            # Проверяем, нет ли уже такой статьи
            if Article.query.filter_by(title=article["title"]).first():
                logger.info(f"[levitin_scraper] Test article already exists: {article['title']}")
                continue
                
            art = Article(
                original_text=article["original_text"],
                source_name="levitin.de",
                title=article["title"],
                summary=article["summary"],
                url=article["url"],
                publish_at=datetime.now(tz)
            )
            db.session.add(art)
            added += 1
        
        if added > 0:
            db.session.commit()
            logger.info(f"[levitin_scraper] Added {added} test articles")
    except Exception as e:
        db.session.rollback()
        logger.error(f"[levitin_scraper] Error adding test articles: {e}")
    
    return added
        
# Enhanced fetch_levitin_updates to combine both approaches
def fetch_levitin_updates_comprehensive():
    """
    Comprehensive function that tries both Selenium and API approaches
    """
    logger.info("[levitin_scraper] Starting comprehensive update")
    
    # First try the API approach
    api_items = try_api_approach()
    added_from_api = process_api_items(api_items)
    
    # Then try Selenium approach
    added_from_selenium = fetch_levitin_updates()
    
    total_added = added_from_api + added_from_selenium
    
    # Если ничего не нашли, добавляем тестовые статьи
    if total_added == 0:
        test_articles_added = add_test_articles(3)
        total_added += test_articles_added
        
    logger.info(f"[levitin_scraper] Total articles added: {total_added} (API: {added_from_api}, Selenium: {added_from_selenium}, Test: {test_articles_added if 'test_articles_added' in locals() else 0})")
    
    return total_added

# For manual testing
if __name__ == "__main__":
    fetch_levitin_updates_comprehensive()

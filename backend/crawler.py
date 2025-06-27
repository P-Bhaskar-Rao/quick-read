import asyncio
import random
import logging
import hashlib
import time
from urllib.parse import urljoin, urlparse, urldefrag
from bs4 import BeautifulSoup, Comment
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from langchain.text_splitter import RecursiveCharacterTextSplitter
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import cloudscraper
from fake_useragent import UserAgent

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("Crawler")

def chunk_text(text):
    splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=20)
    return splitter.split_text(text)

class WebCrawler:
    def __init__(self):
        self.ua = UserAgent()
        self.session = None
        self.cloudscraper_session = None
        
    def get_random_headers(self):
        """Generate random headers to avoid detection"""
        return {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        }

    def create_requests_session(self):
        """Create a robust requests session with retries"""
        if not self.session:
            self.session = requests.Session()
            
            # Retry strategy
            retry_strategy = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
            )
            
            adapter = HTTPAdapter(max_retries=retry_strategy)
            self.session.mount("http://", adapter)
            self.session.mount("https://", adapter)
            
            # Set timeout
            self.session.timeout = 30
            
        return self.session

    def create_cloudscraper_session(self):
        """Create CloudScraper session for CloudFlare protected sites"""
        if not self.cloudscraper_session:
            self.cloudscraper_session = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'windows',
                    'mobile': False
                }
            )
        return self.cloudscraper_session

    async def fetch_with_playwright(self, url):
        """Method 1: Use Playwright with advanced stealth"""
        try:
            async with async_playwright() as p:
                # Try different browsers
                for browser_type in [p.chromium, p.firefox]:
                    try:
                        browser = await browser_type.launch(
                            headless=True,
                            args=[
                                '--no-sandbox',
                                '--disable-setuid-sandbox',
                                '--disable-dev-shm-usage',
                                '--disable-accelerated-2d-canvas',
                                '--no-first-run',
                                '--no-zygote',
                                '--disable-gpu',
                                '--disable-web-security',
                                '--disable-features=VizDisplayCompositor'
                            ]
                        )
                        
                        context = await browser.new_context(
                            user_agent=self.ua.random,
                            locale="en-US",
                            timezone_id="America/New_York",
                            viewport={"width": 1920, "height": 1080},
                            extra_http_headers=self.get_random_headers(),
                        )

                        page = await context.new_page()
                        
                       
                        await page.add_init_script("""
                            // Remove webdriver property
                            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                            
                            // Mock chrome object
                            window.chrome = { runtime: {} };
                            
                            // Mock languages
                            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                            
                            // Mock plugins
                            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                            
                            // Mock permissions
                            const originalQuery = window.navigator.permissions.query;
                            window.navigator.permissions.query = (parameters) => (
                                parameters.name === 'notifications' ?
                                Promise.resolve({ state: Notification.permission }) :
                                originalQuery(parameters)
                            );
                            
                            // Remove automation indicators
                            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
                        """)

                        logger.info(f"Fetching with Playwright: {url}")
                        
                        # Random delay before navigation
                        await asyncio.sleep(random.uniform(1, 3))
                        
                        response = await page.goto(
                            url, 
                            timeout=60000, 
                            wait_until='domcontentloaded'
                        )
                        
                        # Random delay after loading
                        await asyncio.sleep(random.uniform(2, 5))
                        
                        # Try to scroll to simulate human behavior
                        try:
                            await page.evaluate("window.scrollTo(0, document.body.scrollHeight/2)")
                            await asyncio.sleep(random.uniform(1, 2))
                        except:
                            pass

                        if response and response.ok:
                            html = await page.content()
                            await browser.close()
                            return html
                            
                        await browser.close()
                        
                    except Exception as e:
                        logger.warning(f"Playwright {browser_type.name} failed: {e}")
                        if 'browser' in locals():
                            await browser.close()
                        continue
                        
        except Exception as e:
            logger.error(f"Playwright completely failed: {e}")
            
        return None

    def fetch_with_requests(self, url):
        """Method 2: Use requests with session and retries"""
        try:
            session = self.create_requests_session()
            headers = self.get_random_headers()
            
            logger.info(f"Fetching with Requests: {url}")
            
            # Random delay
            time.sleep(random.uniform(1, 3))
            
            response = session.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                return response.text
            else:
                logger.warning(f"Requests failed with status: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Requests failed: {e}")
            
        return None

    def fetch_with_cloudscraper(self, url):
        """Method 3: Use CloudScraper for CloudFlare protected sites"""
        try:
            scraper = self.create_cloudscraper_session()
            
            logger.info(f"Fetching with CloudScraper: {url}")
            
            # Random delay
            time.sleep(random.uniform(1, 3))
            
            response = scraper.get(url, timeout=30)
            
            if response.status_code == 200:
                return response.text
            else:
                logger.warning(f"CloudScraper failed with status: {response.status_code}")
                
        except Exception as e:
            logger.error(f"CloudScraper failed: {e}")
            
        return None

    async def fetch_page_with_fallbacks(self, url):
        """Try multiple methods to fetch a page"""
        methods = [
            ("Playwright", self.fetch_with_playwright),
            ("CloudScraper", self.fetch_with_cloudscraper),
            ("Requests", self.fetch_with_requests),
        ]
        
        for method_name, method in methods:
            try:
                logger.info(f"Trying {method_name} for: {url}")
                
                if method_name == "Playwright":
                    html = await method(url)
                else:
                    html = method(url)
                    
                if html and len(html) > 1000:  # Basic content validation
                    logger.info(f"{method_name} succeeded for: {url}")
                    return html
                else:
                    logger.warning(f"{method_name} returned insufficient content")
                    
            except Exception as e:
                logger.error(f"{method_name} failed: {e}")
                continue
                
            # Random delay between methods
            await asyncio.sleep(random.uniform(2, 4))
            
        logger.error(f"🚫 All methods failed for: {url}")
        return None

    def clean_text_from_html(self, html):
        """Extract clean text from HTML"""
        if not html:
            return "", None
            
        soup = BeautifulSoup(html, "html.parser")

        # Remove unwanted tags
        for tag in soup(["script", "style", "noscript", "footer", "header", "nav", "aside", "iframe"]):
            tag.decompose()

        # Remove comments
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        text = soup.get_text(separator="\n", strip=True)
        
        # Clean up text
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        clean_text = '\n'.join(lines)
        
        return clean_text, soup

    def normalize_url(self, url):
        """Normalize URL by removing fragments and query params"""
        return urldefrag(url)[0].split("?")[0]

    async def crawl_single_page(self, url):
        """Crawl a single page with all fallback methods"""
        logger.info(f"🔍 Starting crawl for: {url}")
        
        html = await self.fetch_page_with_fallbacks(url)
        if not html:
            return None
            
        text, soup = self.clean_text_from_html(html)
        
        if not text or len(text) < 100:
            logger.warning(f"⚠️ Insufficient content extracted from: {url}")
            return None
            
        # Extract metadata
        metadata = {
            "title": "Untitled Page",
            "description": "No description",
            "date": "Unknown Date"
        }
        
        if soup:
            if soup.title:
                metadata["title"] = soup.title.string.strip()
                
            desc_tag = soup.find("meta", attrs={"name": "description"}) or \
                      soup.find("meta", attrs={"property": "og:description"})
            if desc_tag and desc_tag.get('content'):
                metadata["description"] = desc_tag['content'].strip()
                
            date_tag = soup.find("meta", attrs={"property": "article:published_time"}) or \
                      soup.find("meta", attrs={"name": "date"})
            if date_tag and date_tag.get('content'):
                metadata["date"] = date_tag['content']
        
        result = {
            "text": text,
            "title": metadata["title"],
            "description": metadata["description"],
            "date": metadata["date"],
            "url": url,
            "content_length": len(text)
        }
        
        logger.info(f"✅ Successfully crawled: {url} ({len(text)} characters)")
        return result

# Global crawler instance
crawler = WebCrawler()

def crawl_site(url):
    """Main function to crawl a site - called by Flask app"""
    try:
        logger.info(f"🚀 Starting crawl for: {url}")
        
        # Run the async crawl
        result = asyncio.run(crawler.crawl_single_page(url))
        
        if not result:
            # Return a basic error structure that matches expected format
            return {
                "text": f"Unable to crawl the website: {url}. The site may be blocking automated access.",
                "title": "Access Error",
                "description": "Could not access the requested URL",
                "date": "Unknown"
            }, ["Unable to crawl the website. The site may be blocking automated access."]
        
        # Chunk the text
        chunks = chunk_text(result["text"])
        
        logger.info(f"🎉 Crawl completed successfully. Extracted {len(chunks)} chunks.")
        
        return result, chunks
        
    except Exception as e:
        logger.error(f"🚫 Crawl failed with error: {e}")
        
        # Return error structure
        return {
            "text": f"Error crawling {url}: {str(e)}",
            "title": "Crawl Error", 
            "description": "An error occurred while crawling",
            "date": "Unknown"
        }, [f"Error crawling website: {str(e)}"]

async def crawl(url):
    """Legacy async function - kept for compatibility"""
    result = await crawler.crawl_single_page(url)
    if result:
        return result
    else:
        return {
            "text": f"Unable to crawl: {url}",
            "title": "Access Error",
            "description": "Could not access URL", 
            "date": "Unknown"
        }
import asyncio
import logging
import re
from typing import Set, List, Dict, Any
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import httpx

logger = logging.getLogger(__name__)

# Standard mobile/desktop user agents to avoid bot detection
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0"
]

def clean_url(url: str) -> str:
    """Normalizes a URL string, adding https:// if missing."""
    url = url.strip()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url

def get_base_domain(url: str) -> str:
    """Extracts the base domain name (e.g., example.com) from a URL."""
    try:
        parsed = urlparse(clean_url(url))
        domain = parsed.netloc
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return ""

def clean_html_to_text(html_content: str) -> str:
    """Extracts human-readable text from HTML, stripping boilerplate tags."""
    if not html_content:
        return ""
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Remove structural and dynamic noise
        for tag in soup(["script", "style", "nav", "footer", "header", "iframe", "noscript", "svg"]):
            tag.decompose()
            
        # Get raw text with spacing
        text = soup.get_text(separator="\n")
        
        # Remove consecutive empty lines and trim whitespace
        lines = [line.strip() for line in text.splitlines()]
        clean_lines = [line for line in lines if line]
        
        return "\n".join(clean_lines)
    except Exception as e:
        logger.error(f"Error cleaning HTML: {e}")
        return ""

async def scrape_with_httpx(url: str, headers: Dict[str, str]) -> str:
    """Fallback scraping using HTTPX and BeautifulSoup."""
    logger.info(f"Using HTTPX fallback for: {url}")
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=12.0) as client:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                return response.text
            else:
                logger.warning(f"HTTPX failed for {url} with status code {response.status_code}")
    except Exception as e:
        logger.warning(f"HTTPX request failed for {url}: {e}")
    return ""

async def crawl_website_page(url: str, use_playwright: bool = True, timeout_ms: int = 15000) -> str:
    """Scrapes a single page, trying Playwright first, and falling back to HTTPX."""
    url = clean_url(url)
    headers = {"User-Agent": USER_AGENTS[0]}
    
    html_content = ""
    
    if use_playwright:
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                # Create a context with custom user agent and viewport
                context = await browser.new_context(
                    user_agent=USER_AGENTS[0],
                    viewport={"width": 1280, "height": 800}
                )
                page = await context.new_page()
                try:
                    # Navigate and wait for DOM load
                    await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                    # Let Javascript execute briefly
                    await asyncio.sleep(1)
                    html_content = await page.content()
                except Exception as page_err:
                    logger.warning(f"Playwright navigation failed for {url}: {page_err}")
                finally:
                    await browser.close()
        except Exception as pw_err:
            logger.warning(f"Playwright failed to initialize: {pw_err}. Falling back to HTTPX.")
            
    # Fallback to HTTPX if Playwright failed or was skipped
    if not html_content:
        html_content = await scrape_with_httpx(url, headers)
        
    return clean_html_to_text(html_content)

async def extract_links(url: str, html_content: str, base_domain: str) -> Set[str]:
    """Finds all internal links inside the HTML content."""
    links = set()
    if not html_content:
        return links
        
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"].strip()
            if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue
                
            # Resolve relative links
            full_url = urljoin(url, href)
            # Remove query parameters/fragments to normalize
            parsed_full = urlparse(full_url)
            normalized_url = f"{parsed_full.scheme}://{parsed_full.netloc}{parsed_full.path}"
            
            # Ensure the link belongs to the same domain
            if get_base_domain(normalized_url) == base_domain:
                links.add(normalized_url)
    except Exception as e:
        logger.error(f"Error extracting links from {url}: {e}")
        
    return links

def prioritize_links(links: Set[str]) -> List[str]:
    """Sorts and prioritizes links that look like about/product/career pages."""
    priority_patterns = [
        re.compile(r"about|profile|history|company|management|team|founder|leader", re.IGNORECASE),
        re.compile(r"product|service|solution|portfolio|manufactur|facility|plant|technology|r-d|research", re.IGNORECASE),
        re.compile(r"certif|quality|approve|standards|award", re.IGNORECASE),
        re.compile(r"career|job|hiring|recruit|join", re.IGNORECASE),
        re.compile(r"news|press|announce|media", re.IGNORECASE),
        re.compile(r"contact|location|office|reach", re.IGNORECASE)
    ]
    
    def score_link(link: str) -> int:
        # Lower score is higher priority
        path = urlparse(link).path
        for idx, pattern in enumerate(priority_patterns):
            if pattern.search(path):
                return idx
        return len(priority_patterns)  # Lowest priority
        
    sorted_links = sorted(list(links), key=score_link)
    return sorted_links

async def scrape_entire_website(url: str, max_pages: int = 5, timeout_ms: int = 15000) -> str:
    """
    Crawls a website starting at url.
    Visits up to max_pages, prioritizing high-value subpages.
    Combines text contents and returns it.
    """
    start_url = clean_url(url)
    if not start_url:
        return ""
        
    base_domain = get_base_domain(start_url)
    if not base_domain:
        return ""
        
    logger.info(f"Crawling website: {start_url} (domain: {base_domain})")
    
    visited_urls: Set[str] = set()
    to_visit: List[str] = [start_url]
    combined_texts: List[str] = []
    
    # Check if playwright is available
    use_playwright = True
    try:
        import playwright
    except ImportError:
        use_playwright = False
        
    # Standard request headers for crawler fallback
    headers = {"User-Agent": USER_AGENTS[0]}
    
    while to_visit and len(visited_urls) < max_pages:
        current_url = to_visit.pop(0)
        if current_url in visited_urls:
            continue
            
        logger.info(f"Scraping page {len(visited_urls) + 1}/{max_pages}: {current_url}")
        visited_urls.add(current_url)
        
        # Scrape html or raw text
        html_content = ""
        page_text = ""
        
        if use_playwright:
            try:
                from playwright.async_api import async_playwright
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True)
                    context = await browser.new_context(user_agent=USER_AGENTS[0])
                    page = await context.new_page()
                    try:
                        await page.goto(current_url, wait_until="domcontentloaded", timeout=timeout_ms)
                        await asyncio.sleep(0.5)
                        html_content = await page.content()
                        page_text = clean_html_to_text(html_content)
                    except Exception as e:
                        logger.warning(f"Playwright failed to scrape {current_url}: {e}")
                    finally:
                        await browser.close()
            except Exception as e:
                logger.warning(f"Playwright failed for {current_url}: {e}. Falling back to HTTPX.")
                use_playwright = False # Disable for subsequent pages if runtime issue
                
        if not page_text:
            html_content = await scrape_with_httpx(current_url, headers)
            page_text = clean_html_to_text(html_content)
            
        if page_text:
            # Label the page to help the LLM contextualize the text
            parsed_url = urlparse(current_url)
            page_label = parsed_url.path if parsed_url.path and parsed_url.path != "/" else "home"
            combined_texts.append(f"--- PAGE: {page_label} ({current_url}) ---\n{page_text}\n")
            
            # If we need more pages, extract links from this page
            if len(visited_urls) < max_pages and html_content:
                discovered_links = await extract_links(current_url, html_content, base_domain)
                new_links = discovered_links - visited_urls - set(to_visit)
                
                # Prioritize and add links to visit
                prioritized_new = prioritize_links(new_links)
                to_visit.extend(prioritized_new)
                # Re-sort to_visit to maintain global priority
                to_visit = prioritize_links(set(to_visit))
                
        # Politeness delay between pages
        await asyncio.sleep(1.0)
        
    return "\n".join(combined_texts)

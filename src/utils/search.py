import logging
from typing import List, Dict, Any
import httpx
from bs4 import BeautifulSoup
import urllib.parse

logger = logging.getLogger(__name__)

def search_ddg(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Search the web for the given query.
    Returns a list of dicts: [{'title': '...', 'url': '...', 'snippet': '...'}]
    
    Fallback chain: ddgs → DuckDuckGo HTML scrape → Yahoo Search
    """
    logger.info(f"Searching web for: '{query}'")
    results = []

    # Method 1: Use ddgs package (successor to duckduckgo_search)
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            ddg_results = ddgs.text(query, max_results=max_results)
            for r in ddg_results:
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", "")
                })
        if results:
            logger.info(f"ddgs returned {len(results)} results.")
            return results
    except ImportError:
        logger.warning("ddgs package not found. Attempting HTML scraping fallback...")
    except Exception as e:
        logger.warning(f"ddgs search failed: {e}. Trying HTML scraping...")

    # Method 2: DuckDuckGo HTML scraping
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5"
        }
        url = "https://html.duckduckgo.com/html/"
        params = {"q": query}

        with httpx.Client(follow_redirects=True, timeout=12.0) as client:
            response = client.get(url, params=params, headers=headers)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            result_elements = soup.find_all("div", class_="result")

            for elem in result_elements[:max_results]:
                title_elem = elem.find("a", class_="result__a")
                snippet_elem = elem.find("a", class_="result__snippet")

                if title_elem:
                    title = title_elem.get_text(strip=True)
                    raw_url = title_elem.get("href", "")

                    # Decode DDG redirect URLs
                    parsed_url = urllib.parse.urlparse(raw_url)
                    if parsed_url.path == "/l/":
                        query_params = urllib.parse.parse_qs(parsed_url.query)
                        actual_url = query_params.get("uddg", [raw_url])[0]
                    else:
                        actual_url = raw_url

                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                    results.append({"title": title, "url": actual_url, "snippet": snippet})

        if results:
            logger.info(f"DuckDuckGo HTML fallback returned {len(results)} results.")
            return results
    except Exception as fallback_err:
        logger.error(f"DuckDuckGo HTML fallback failed: {fallback_err}")

    # Method 3: Yahoo Search fallback
    try:
        logger.info("Attempting Yahoo Search fallback...")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5"
        }
        url = "https://search.yahoo.com/search"
        params = {"p": query}

        with httpx.Client(follow_redirects=True, timeout=12.0) as client:
            response = client.get(url, params=params, headers=headers)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            elements = soup.find_all("div", class_="algo")

            for elem in elements[:max_results]:
                a = elem.find("a")
                if a:
                    raw_url = a.get("href", "")
                    actual_url = raw_url
                    if "/RU=" in raw_url:
                        try:
                            parts = raw_url.split("/RU=")
                            if len(parts) > 1:
                                actual_url = urllib.parse.unquote(parts[1].split("/RK=")[0])
                        except Exception:
                            pass

                    title_elem = elem.find("h3")
                    title = title_elem.get_text(strip=True) if title_elem else "Unknown Title"
                    comp_desc = elem.find("div", class_="compText")
                    snippet = comp_desc.get_text(strip=True) if comp_desc else ""

                    results.append({"title": title, "url": actual_url, "snippet": snippet})

            if results:
                logger.info(f"Yahoo Search fallback successful: {len(results)} results.")
    except Exception as yahoo_err:
        logger.error(f"Yahoo Search fallback failed: {yahoo_err}")

    return results

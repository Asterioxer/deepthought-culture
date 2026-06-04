import logging
import re
from typing import List, Dict, Any, Set
from urllib.parse import urlparse
from src.agents.base import BaseAgent
from src.utils.search import search_ddg
from src.utils.scraper import get_base_domain

logger = logging.getLogger(__name__)

# Directory and social domains to filter out when seeking direct company websites
EXCLUDED_DOMAINS = {
    "zaubacorp.com", "tofler.in", "linkedin.com", "indiamart.com", "justdial.com",
    "facebook.com", "twitter.com", "youtube.com", "wikipedia.org", "glassdoor.co.in",
    "glassdoor.com", "ambitionbox.com", "tracxn.com", "tradeindia.com", "yellowpages.com",
    "instagram.com", "google.com", "mapsofindia.com", "sulekha.com", "easyleadz.com",
    "apollo.io", "zoominfo.com", "signalsbi.com", "crisil.com", "startupindia.gov.in"
}

class DiscoveryAgent(BaseAgent):
    """
    Agent responsible for finding target companies matching the input criteria (city, industry).
    Uses web searches to gather candidates, filtering directories and resolving websites.
    """
    
    def discover(self, city: str, industry: str, max_companies: int) -> List[Dict[str, Any]]:
        """
        Executes search queries to find matching companies.
        Returns a list of dicts: [{'name': '...', 'website': '...'}]
        """
        logger.info(f"Starting discovery for '{industry}' in '{city}', limit: {max_companies}")
        
        # 1. Generate search queries using LLM
        queries = self._generate_search_queries(city, industry)
        logger.info(f"Generated search queries: {queries}")
        
        # 2. Gather raw search results
        raw_results = []
        for q in queries:
            search_hits = search_ddg(q, max_results=10)
            raw_results.extend(search_hits)
            
        # 3. Extract candidate companies using LLM & Heuristics
        candidates = self._extract_candidates(raw_results, city, industry)
        logger.info(f"Initial candidates extracted: {len(candidates)}")
        
        # 4. Resolve missing websites using secondary searches
        resolved_companies = []
        seen_names: Set[str] = set()
        seen_websites: Set[str] = set()
        
        for c in candidates:
            name = c.get("name", "").strip()
            website = c.get("website", "").strip()
            
            # Clean name for deduplication (lowercase, strip spaces, etc.)
            clean_name = re.sub(r"\s+(pvt|private|ltd|limited)\s*$", "", name, flags=re.IGNORECASE).strip().lower()
            if not clean_name or clean_name in seen_names:
                continue
                
            if not website:
                # Run search to find website
                website = self._find_company_website(name, city)
                
            if website:
                parsed_web = urlparse(website.lower() if website.startswith("http") else "https://" + website.lower())
                domain = parsed_web.netloc
                if domain.startswith("www."):
                    domain = domain[4:]
                if domain in seen_websites or domain in EXCLUDED_DOMAINS:
                    continue
                seen_websites.add(domain)
                
            seen_names.add(clean_name)
            
            resolved_companies.append({
                "name": name,
                "website": website or "No website found",
                "city": city,
                "segment": industry
            })
            
            if len(resolved_companies) >= max_companies:
                break
                
        logger.info(f"Discovery completed. Found {len(resolved_companies)} unique candidates.")
        return resolved_companies
        
    def _generate_search_queries(self, city: str, industry: str) -> List[str]:
        """Uses LLM to formulate highly relevant search queries."""
        system_prompt = (
            "You are an expert market research assistant specializing in discovering Indian B2B companies. "
            "Your task is to generate 5-6 high-yield web search queries to discover real company names and websites "
            "matching a given city and industry segment in India."
        )
        user_prompt = (
            f"Generate 6 targeted search queries to find companies in the '{industry}' sector located in or around '{city}', India.\n"
            "Strategy:\n"
            "  - 3 broad natural-language queries (e.g. 'top precision engineering companies in Pune India')\n"
            "  - 1 trade expo or industry association query (e.g. 'Pune auto components ACMA members list')\n"
            "  - 1 registry query using site:zaubacorp.com or site:tofler.in (for company name extraction only)\n"
            "  - 1 LinkedIn or news query (e.g. 'auto component manufacturer Pune founded CEO')\n"
            "Do NOT use complex boolean operators. Return ONLY a JSON array of strings.\n"
            f"Example: [\"precision auto component manufacturers Pune India\", \"ACMA members Pune auto parts companies\"]"
        )
        
        try:
            res_json = self.call_llm_json(system_prompt, user_prompt)
            if isinstance(res_json, list) and len(res_json) >= 2:
                return res_json[:6]  # Cap at 6 queries
            elif isinstance(res_json, dict) and "queries" in res_json:
                return res_json["queries"][:6]
        except Exception as e:
            logger.error(f"Failed to generate search queries using LLM: {e}. Using fallback queries.")

        # Fallback queries: broad natural language first, registry supplementary
        return [
            f"{industry} companies {city} India",
            f"top {industry} manufacturers {city}",
            f"{industry} company {city} India website",
            f"site:zaubacorp.com \"{city}\" {industry}",
            f"site:indiamart.com {industry} {city} manufacturer",
        ]

    def _extract_candidates(self, search_results: List[Dict[str, Any]], city: str, industry: str) -> List[Dict[str, Any]]:
        """Parses web search results using LLM to extract list of companies and websites."""
        # Clean up search results for LLM prompt limit
        context_lines = []
        for idx, r in enumerate(search_results):
            context_lines.append(f"Result [{idx+1}]:\nTitle: {r['title']}\nLink: {r['url']}\nSnippet: {r['snippet']}\n")
        context_text = "\n".join(context_lines)[:12000] # Cap to prevent token overflow
        
        system_prompt = (
            "You are a business research intelligence agent. Your job is to extract corporate names and websites from raw search engine results. "
            "Focus only on companies located in India that match the industry. Reject generic platforms, job boards, or news sites."
        )
        user_prompt = (
            f"Based on the following search results for companies in '{industry}' in '{city}', extract a list of candidate companies.\n"
            "For each candidate, extract the Company Name and their direct corporate website URL (if mentioned or evident in the URL/snippet).\n"
            "If the URL points to a registry like ZaubaCorp or Tofler, leave 'website' empty unless the official website is explicitly mentioned in the snippet.\n"
            "Ensure company names are clean corporate names (e.g. 'Ananth Technologies' instead of 'Ananth Technologies Hyderabad').\n\n"
            "Return ONLY a JSON list of objects: [{\"name\": \"Company Name\", \"website\": \"company_website_url_or_empty\"}].\n\n"
            f"Search Results:\n{context_text}"
        )
        
        try:
            candidates = self.call_llm_json(system_prompt, user_prompt)
            if isinstance(candidates, list):
                return candidates
            elif isinstance(candidates, dict) and "companies" in candidates:
                return candidates["companies"]
        except Exception as e:
            logger.error(f"Failed to extract candidates using LLM: {e}")
            
        # Heuristic fallback parsing if LLM fails
        heuristic_candidates = []
        for r in search_results:
            url = r["url"]
            domain = get_base_domain(url)
            if domain and domain not in EXCLUDED_DOMAINS:
                # Try to clean the name from the title
                title = r["title"]
                cleaned_name = title.split("-")[0].split("|")[0].split(":")[0].strip()
                # Simple cleaning
                cleaned_name = re.sub(r"^(Welcome to|Home|About Us)\s+", "", cleaned_name, flags=re.IGNORECASE).strip()
                if len(cleaned_name) > 3 and len(cleaned_name) < 50:
                    heuristic_candidates.append({"name": cleaned_name, "website": f"https://{domain}"})
                    
        return heuristic_candidates

    def _find_company_website(self, name: str, city: str) -> str:
        """Runs a targeted search query to find the official website of a discovered company."""
        query = f"\"{name}\" official website {city}"
        logger.info(f"Attempting website discovery query: {query}")
        hits = search_ddg(query, max_results=4)
        
        # Filter search hits to find the most likely corporate URL
        for hit in hits:
            url = hit["url"]
            domain = get_base_domain(url)
            if domain and domain not in EXCLUDED_DOMAINS:
                # Return the root domain as the official website
                return f"https://{domain}"
                
        return ""

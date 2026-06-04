import asyncio
import logging
from typing import Dict, Any, List
from src.agents.base import BaseAgent
from src.utils.scraper import scrape_entire_website
from src.utils.search import search_ddg

logger = logging.getLogger(__name__)

class ResearchAgent(BaseAgent):
    """
    ResearchAgent crawls a target company's website and performs supplementary
    web searches to compile comprehensive information about its products, leadership,
    financials, facilities, and growth signals.
    """
    
    async def research_company(self, company: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gathers facts for a single company via crawling and search.
        Updates and returns the company dictionary.
        """
        name = company.get("name", "")
        website = company.get("website", "")
        city = company.get("city", "")
        
        logger.info(f"Researching company: {name} (Website: {website})")
        
        # 1. Crawl website
        scraped_text = ""
        if website and website != "No website found":
            try:
                # Crawl up to 4 pages on the website
                scraped_text = await scrape_entire_website(website, max_pages=4)
            except Exception as e:
                logger.error(f"Error scraping website for {name}: {e}")
                
        # 2. Run supplementary searches (for details like founder background, revenue band, news)
        search_snippets = []
        try:
            queries = [
                f"\"{name}\" founder OR MD OR owner OR CEO background {city}",
                f"\"{name}\" revenue OR turnover OR financial band Tofler OR Zauba",
                f"\"{name}\" plant OR factory OR facility OR expansion {city}",
                f"\"{name}\" certification OR approval OR ISO OR FDA"
            ]
            
            # Fetch search snippets in parallel (with politeness delays inside DDG search if needed)
            for q in queries:
                results = search_ddg(q, max_results=3)
                for r in results:
                    search_snippets.append(f"Search Context (Query: {q}):\nTitle: {r['title']}\nSnippet: {r['snippet']}\nUrl: {r['url']}\n")
                await asyncio.sleep(0.5) # simple delay to prevent hammering DDG
        except Exception as e:
            logger.warning(f"Supplementary searches failed for {name}: {e}")
            
        # 3. Combine crawled text and search snippets
        combined_text = ""
        if scraped_text:
            combined_text += f"=== WEBSITE TEXT ===\n{scraped_text}\n"
        if search_snippets:
            combined_text += f"\n=== SUPPLEMENTARY WEB SEARCHES ===\n" + "\n".join(search_snippets)
            
        if not combined_text.strip():
            logger.warning(f"No research text could be gathered for {name}")
            combined_text = "No text could be extracted from website or web searches."
            
        company["scraped_content"] = combined_text
        
        # 4. Extract structured profile using LLM
        extracted_facts = self._extract_facts_with_llm(name, city, combined_text)
        
        # Merge facts into the company dictionary
        company.update(extracted_facts)
        
        return company

    def _extract_facts_with_llm(self, name: str, city: str, context: str) -> Dict[str, Any]:
        """Uses LLM to extract structured facts from scraped text and search snippets."""
        system_prompt = (
            "You are a meticulous business intelligence analyst. Your job is to extract factual corporate records from provided text. "
            "Never assume or extrapolate facts; if a detail is not explicitly mentioned or clearly evidenced, write 'Unknown' or 'No visible evidence'.\n"
            "Format the output strictly as a JSON object with the specified keys."
        )
        
        user_prompt = f"""Analyze the provided context for the company '{name}' located in '{city}', India. 
Extract the following attributes:
1. **Products**: List specific products they manufacture or specialized services they deliver in-house. Do not write generic industry segments.
2. **Revenue Band**: Estimate the annual revenue of the company. Choose EXACTLY one of: "<Rs.30Cr", "Rs.30-100Cr", "Rs.100-300Cr", "Rs.300-500Cr", ">Rs.500Cr", or "Unknown". Look for ROC, ZaubaCorp, Tofler, or news indicators.
3. **Decision Maker**: Find the name of the founder, MD, or primary operator.
4. **DM Title**: What is their formal title (e.g. Managing Director, Founder, Chairman, CEO)?
5. **DM Background**: Summarize their education or professional history. Look for technical qualifications (e.g., B.Tech, PhD, M.Tech, IIT/NIT/BITS, scientific pedigree) or operator systems background.
6. **Facilities**: Details of manufacturing plants, factories, R&D centers, or testing labs.
7. **Certifications**: List specific regulatory approvals, quality certifications (e.g. ISO 9001:2015, AS9100, USFDA, WHO-GMP, PIC/S, CE marking).
8. **Expansion Announcements**: Note any new capacity expansions, plant build announcements, or investment in equipment in the last 18 months.
9. **Hiring Activity**: Note any job vacancies, recruiting activity on LinkedIn/Naukri, or teams mentioned in the text.
10. **Evidence Sources**: A list of URLs or sources that confirm these facts.

Context:
{context[:20000]} # Trim to fit LLM window

Your response must be a JSON object matching this schema:
{{
  "Products": "string (specific list)",
  "Revenue Band": "string (one of the specified options)",
  "Decision Maker": "string (name)",
  "DM Title": "string (title)",
  "DM Background": "string (academic / work history)",
  "facilities": "string (details of facilities)",
  "certifications": "string (certifications list)",
  "expansions": "string (expansion details)",
  "hiring": "string (hiring details)",
  "evidence_sources": "string (semicolon-separated list of URLs or sources)"
}}
"""
        try:
            facts = self.call_llm_json(system_prompt, user_prompt)
            # Normalize keys to match Pydantic model expectations (mapping is handled in state.py)
            return facts
        except Exception as e:
            logger.error(f"LLM fact extraction failed for {name}: {e}")
            return {
                "Products": "Failed to extract products",
                "Revenue Band": "Unknown",
                "Decision Maker": "Unknown",
                "DM Title": "Unknown",
                "DM Background": "Unknown",
                "facilities": "Unknown",
                "certifications": "Unknown",
                "expansions": "Unknown",
                "hiring": "Unknown",
                "evidence_sources": "Unknown"
            }

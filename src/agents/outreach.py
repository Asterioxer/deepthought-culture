import logging
from typing import Dict, Any
from src.agents.base import BaseAgent

logger = logging.getLogger(__name__)

class OutreachAgent(BaseAgent):
    """
    OutreachAgent generates a personalized outreach hook based on specific,
    highly relevant details extracted about the company (e.g. founder's background,
    specialized equipment, or recent plant expansions).
    """
    
    def generate_hook(self, company: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generates one personalized outreach hook for the company.
        Returns the updated company dictionary.
        """
        name = company.get("name", "")
        logger.info(f"Generating outreach hook for {name}")
        
        # Don't generate hooks for disqualified companies
        if company.get("Verdict") == "Disqualified":
            company["Outreach Hook"] = ""
            return company
            
        products = company.get("Products", "")
        decision_maker = company.get("Decision Maker", "Unknown")
        dm_title = company.get("DM Title", "Unknown")
        dm_background = company.get("DM Background", "Unknown")
        facilities = company.get("facilities", "Unknown")
        certifications = company.get("certifications", "Unknown")
        expansions = company.get("expansions", "Unknown")
        hiring = company.get("hiring", "Unknown")
        scraped_text = company.get("scraped_content", "")
        segment = company.get("segment", "")
        city = company.get("city", "")
        
        system_prompt = (
            "You are an elite B2B sales development representative. Your job is to write a single-sentence "
            "email hook that is highly specific, completely personalized, and demonstrates that we "
            "deeply understand what the company does. Avoid generic compliments (e.g. 'I was impressed by your website'). "
            "Reference a specific technical detail, founder milestone, certification, or recent expansion.\n"
            "Format the output strictly as a JSON object."
        )
        
        user_prompt = f"""Write a personalized outreach email hook for the following company:
Company Name: {name}
City: {city}
Industry Segment: {segment}
Products: {products}
Decision Maker: {decision_maker} ({dm_title})
Decision Maker Background: {dm_background}
Facilities: {facilities}
Certifications: {certifications}
Expansions: {expansions}
Hiring: {hiring}

Context from Scraped Data:
{scraped_text[:12000]}

--- HOOK REQUIREMENTS ---
1. Must be exactly one sentence.
2. Must mention a specific, true, recent detail about the company (e.g., their transition to a specific German Barmag machinery, their AS9100 certification, their founder's ex-ISRO scientist background, or their new Hyderabad facility).
3. Do NOT make up facts. Use ONLY details found in the dossier or context.
4. Keep it professional, conversational, and direct.

Return a JSON object matching this schema:
{{
  "Outreach Hook": "One sentence personalized hook."
}}
"""
        try:
            hook_results = self.call_llm_json(system_prompt, user_prompt)
            company["Outreach Hook"] = hook_results.get("Outreach Hook", "Failed to generate hook.")
        except Exception as e:
            logger.error(f"Outreach hook generation failed for {name}: {e}")
            company["Outreach Hook"] = "Failed to generate hook due to execution error."
            
        return company

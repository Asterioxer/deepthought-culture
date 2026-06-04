import logging
from typing import Dict, Any
from src.agents.base import BaseAgent

logger = logging.getLogger(__name__)

class FedererScoringAgent(BaseAgent):
    """
    FedererScoringAgent evaluates the company on criteria C3 to C8:
    - C3: Differentiated (Moat/IP/Specialized capability) - Weight 20
    - C4: Decision Maker Quality (Pedigree/Systems-thinking) - Weight 15
    - C5: Growing Sector (Industry tailwinds) - Weight 15
    - C6: Growth Signals (Active hiring, facility, certs, financials, site) - Weight 15
    - C7: Systems Maturity (ERP/SAP, costing, dashboards) - Weight 20
    - C8: Leadership Succession (Gen-2, outside execs, governance) - Weight 15
    
    Total score = Sum(C3-C8) out of 100.
    """
    
    def score_company(self, company: Dict[str, Any]) -> Dict[str, Any]:
        """
        Scores the company on C3-C8 and adds evidence for each score.
        Returns the updated company dictionary.
        """
        name = company.get("name", "")
        logger.info(f"Scoring company: {name}")
        
        products = company.get("Products", "")
        revenue_band = company.get("Revenue Band", "Unknown")
        decision_maker = company.get("Decision Maker", "Unknown")
        dm_background = company.get("DM Background", "Unknown")
        facilities = company.get("facilities", "Unknown")
        certifications = company.get("certifications", "Unknown")
        expansions = company.get("expansions", "Unknown")
        hiring = company.get("hiring", "Unknown")
        scraped_text = company.get("scraped_content", "")
        city = company.get("city", "")
        segment = company.get("segment", "")
        
        system_prompt = (
            "You are a rigorous financial analyst and management consultant. Your job is to score a company against "
            "the Federer scoring system using ONLY the provided facts and scraped text. Do not invent or assume "
            "details. C7 (Systems Maturity) is extremely critical; if there is no mention of ERP/SAP, costing systems, "
            "or digital processes, it must be scored as Weak (0).\n"
            "Format the output strictly as a JSON object."
        )
        
        user_prompt = f"""Score the company '{name}' based on these scoring rules:

--- SCORING RULES & CRITERIA ---
1. **C3 (Differentiated - 20 max)**:
   - **Strong (20.0)**: Patents, DSIR-recognized R&D, international approvals (USFDA/EU-GMP/PICs), proprietary technical products OR specialized production machinery (e.g., German/Japanese Barmag/CNC) + custom capability + market-shaping innovation (like pioneer MOQ).
   - **Moderate (10.0)**: Some technical depth or customization, but no patents, approvals, or highly specialized machinery.
   - **Weak (0.0)**: Standard commodity product, job-work, or low-barrier service. No capability or IP moat.

2. **C4 (Decision Maker Quality - 15 max)**:
   - **Strong (15.0)**: Founder/MD has a PhD, B.Tech/M.Tech from top pedigree (IIT/NIT/BITS/IISc), is a scientist, OR is an operator-founder who actively built ERP, costing models, or formal planning systems.
   - **Moderate (7.5)**: Gen-2 with formal higher education, or some evidence of systems thinking (CA background, standard operational planning).
   - **Weak (0.0)**: Business promoter with no technical or systems background, or outsource mindset.

3. **C5 (Growing Sector - 15 max)**:
   - **Strong (15.0)**: Niche segment with tailwinds: PLI eligible, China+1 beneficiary, Make-in-India focus, major export growth, space/defence opening.
   - **Moderate (7.5)**: Stable market/sector (standard industrial inputs, stable food processing) but no major macro tailwinds.
   - **Weak (0.0)**: Declining or stagnant industry.

4. **C6 (Growth Signals - 15 max)**:
   - **Strong (15.0)**: Meets 2 or more of the following 5 thresholds:
     * Hiring: 5+ open roles on LinkedIn/Naukri in last 6 months.
     * Facility: New plant or capacity expansion in last 18 months.
     * Certifications: New regulatory approval/certification in last 2 years.
     * Website: Copyright date is current/last year, active news/press updates.
     * Financial: Strong revenue growth visible, or entering new export markets.
   - **Moderate (7.5)**: Meets exactly 1 signal.
   - **Weak (0.0)**: Meets 0 signals (stagnant/dormant).

5. **C7 (Systems Maturity - 20 max)**:
   - **Strong (20.0)**: ERP/SAP (e.g. SAP S/4HANA) confirmed in use, custom costing models, daily MIS dashboards, or active IT division driving operational processes.
   - **Moderate (10.0)**: Some software in use (Tally, standard CRM) or IT job positions/IT manager on LinkedIn, but depth is unclear.
   - **Weak (0.0)**: No mention of ERP/SAP, paper/WhatsApp-driven, or running entirely on founder intuition.

6. **C8 (Leadership Succession - 15 max)**:
   - **Strong (15.0)**: Gen-2 formally appointed to the board (active operational role), AND/OR external professional managers in senior roles (CTO/CFO/COO from outside), AND/OR multiple distinct V4 executive portfolios (division heads).
   - **Moderate (7.5)**: Gen-2 exists but operational authority is unclear, OR exactly one outside professional hire on the board.
   - **Weak (0.0)**: Solo founder, no gen-2, no professional managers, all authority resides in one person.

--- COMPANY DOSSIER ---
Company Name: {name}
City: {city}
Industry: {segment}
Products: {products}
Revenue Band: {revenue_band}
Decision Maker: {decision_maker}
DM Background: {dm_background}
Facilities: {facilities}
Certifications: {certifications}
Expansions: {expansions}
Hiring: {hiring}

Context from Scraped Data:
{scraped_text[:15000]}

--- OUTPUT SCHEMA ---
Your response must be a JSON object with this format (use float scores):
{{
  "C3 Score": 0.0 or 10.0 or 20.0,
  "C3 Evidence": "One sentence citing the exact fact/quote justifying this score.",
  "C4 Score": 0.0 or 7.5 or 15.0,
  "C4 Evidence": "One sentence citing the exact fact/quote justifying this score.",
  "C5 Score": 0.0 or 7.5 or 15.0,
  "C5 Evidence": "One sentence citing the exact fact/quote justifying this score.",
  "C6 Score": 0.0 or 7.5 or 15.0,
  "C6 Evidence": "Specify which signals were met (0, 1, or 2+) and cite the facts.",
  "C7 Score": 0.0 or 10.0 or 20.0,
  "C7 Evidence": "One sentence citing the exact fact/quote justifying this score.",
  "C8 Score": 0.0 or 7.5 or 15.0,
  "C8 Evidence": "One sentence citing the exact fact/quote justifying this score."
}}
"""
        try:
            scores = self.call_llm_json(system_prompt, user_prompt)
            
            # Map scores into company
            company["C3 Score"] = float(scores.get("C3 Score", 0.0))
            company["C3 Evidence"] = scores.get("C3 Evidence", "No evidence.")
            company["C4 Score"] = float(scores.get("C4 Score", 0.0))
            company["C4 Evidence"] = scores.get("C4 Evidence", "No evidence.")
            company["C5 Score"] = float(scores.get("C5 Score", 0.0))
            company["C5 Evidence"] = scores.get("C5 Evidence", "No evidence.")
            company["C6 Score"] = float(scores.get("C6 Score", 0.0))
            company["C6 Evidence"] = scores.get("C6 Evidence", "No evidence.")
            company["C7 Score"] = float(scores.get("C7 Score", 0.0))
            company["C7 Evidence"] = scores.get("C7 Evidence", "No evidence.")
            company["C8 Score"] = float(scores.get("C8 Score", 0.0))
            company["C8 Evidence"] = scores.get("C8 Evidence", "No evidence.")
            
        except Exception as e:
            logger.error(f"Federer scoring failed for {name}: {e}")
            for c_idx in ["C3", "C4", "C5", "C6", "C7", "C8"]:
                company[f"{c_idx} Score"] = 0.0
                company[f"{c_idx} Evidence"] = f"Scoring error: {str(e)}"
                
        return company

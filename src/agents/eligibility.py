import logging
from typing import Dict, Any
from src.agents.base import BaseAgent

logger = logging.getLogger(__name__)

class EligibilityAgent(BaseAgent):
    """
    EligibilityAgent verifies the two mandatory gates:
    - E1: Producer (Not a trader, reseller, distributor, CRO, or pure broker)
    - E2: Accessible (India-based operational presence)
    Also applies auto-disqualification criteria.
    """
    
    def evaluate_eligibility(self, company: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluates E1 and E2 eligibility gates and auto-disqualification criteria.
        Returns the updated company dictionary.
        """
        name = company.get("name", "")
        logger.info(f"Evaluating eligibility for {name}")
        
        # Pull the gathered facts
        products = company.get("Products", "")
        revenue_band = company.get("Revenue Band", "Unknown")
        decision_maker = company.get("Decision Maker", "Unknown")
        facilities = company.get("facilities", "Unknown")
        certifications = company.get("certifications", "Unknown")
        scraped_text = company.get("scraped_content", "")
        city = company.get("city", "")
        segment = company.get("segment", "")
        
        system_prompt = (
            "You are a strict compliance auditor for corporate targeting. Your task is to verify if a company passes DeepThought's two eligibility gates:\n"
            "1. E1: Producer — Must manufacture a physical product or deliver a highly specialized proprietary service (has own plant, facility, or infrastructure). Reject traders, distributors, resellers, agents, CROs, testing labs, clinical trial services, and generic service companies.\n"
            "2. E2: Accessible — Must have an operational presence (HQ, R&D, or manufacturing facility) in India.\n\n"
            "You must also identify auto-disqualifications:\n"
            "- Revenue > Rs.500Cr (Revenue Band is '>Rs.500Cr')\n"
            "- Generic pharma (bulk generic APIs, standard generic drugs, bulk vaccines)\n"
            "- Subsidiary of a large group (e.g., Tata, Reliance, Birla divisions)\n"
            "- PE/VC-controlled (majority institutional ownership, not promoter/founder driven)\n"
            "- No website / inactive for the last 2 years\n\n"
            "Format the output strictly as a JSON object."
        )
        
        user_prompt = f"""Evaluate the eligibility gates for this company:
Company Name: {name}
City: {city}
Industry Segment: {segment}
Products: {products}
Revenue Band: {revenue_band}
Decision Maker: {decision_maker}
Facilities: {facilities}
Certifications: {certifications}

Context from Scraped Data:
{scraped_text[:12000]} # Trim to fit

Return a JSON object matching this schema:
{{
  "E1 Status": "PASS or FAIL",
  "E1 Evidence": "One sentence citing evidence from the context showing if the company operates its own manufacturing facility/infrastructure (PASS) or is a trader/service CRO/distributor (FAIL).",
  "E2 Status": "PASS or FAIL",
  "E2 Evidence": "One sentence citing evidence showing the company's operational footprint in India.",
  "Is Disqualified": true or false,
  "Disqualification Reason": "Write a clear rejection reason if disqualified (e.g. 'Revenue exceeds Rs.500Cr limit', 'Company is a CRO/Testing lab, not a producer', 'PE-owned', 'No active operations'), or empty if passed."
}}
"""
        try:
            gate_results = self.call_llm_json(system_prompt, user_prompt)
            
            # Map LLM results into company keys
            company["E1 Status"] = gate_results.get("E1 Status", "FAIL").upper()
            company["E1 Evidence"] = gate_results.get("E1 Evidence", "No evidence retrieved.")
            company["E2 Status"] = gate_results.get("E2 Status", "FAIL").upper()
            company["E2 Evidence"] = gate_results.get("E2 Evidence", "No evidence retrieved.")
            
            # Auto-disqualify if E1/E2 fails or LLM flagged disqualification
            is_disqualified = gate_results.get("Is Disqualified", False)
            disq_reason = gate_results.get("Disqualification Reason", "")
            
            if company["E1 Status"] == "FAIL" or company["E2 Status"] == "FAIL":
                is_disqualified = True
                if not disq_reason:
                    disq_reason = "Failed E1 (Producer) or E2 (Accessible) eligibility gates."
                    
            if is_disqualified:
                company["Verdict"] = "Disqualified"
                company["Band"] = "D"
                company["Evidence"] = disq_reason
                logger.info(f"Company {name} DISQUALIFIED: {disq_reason}")
            else:
                company["Verdict"] = "Pending Scored"
                
        except Exception as e:
            logger.error(f"Eligibility evaluation failed for {name}: {e}")
            company["E1 Status"] = "FAIL"
            company["E1 Evidence"] = "Failed to run eligibility evaluation."
            company["E2 Status"] = "FAIL"
            company["E2 Evidence"] = "Failed to run eligibility evaluation."
            company["Verdict"] = "Disqualified"
            company["Band"] = "D"
            company["Evidence"] = f"Eligibility verification error: {str(e)}"
            
        return company

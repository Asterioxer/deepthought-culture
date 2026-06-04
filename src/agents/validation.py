import logging
from typing import Dict, Any
from src.agents.base import BaseAgent

logger = logging.getLogger(__name__)

class ValidationAgent(BaseAgent):
    """
    ValidationAgent fact-checks the eligibility status, scores, and cited evidence
    against the raw scraped content. It assigns a confidence score and can
    programmatically override inflated scores to prevent hallucinations.
    """
    
    def validate_profile(self, company: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates company scores and evidence.
        Applies overrides if LLM over-scored or hallucinated.
        Returns the updated company dictionary.
        """
        name = company.get("name", "")
        logger.info(f"Validating profile for: {name}")
        
        # Collect criteria details
        criteria_summary = ""
        for score_key in ["C3", "C4", "C5", "C6", "C7", "C8"]:
            score = company.get(f"{score_key} Score", 0.0)
            evidence = company.get(f"{score_key} Evidence", "")
            criteria_summary += f"[{score_key}] Score: {score} | Cited Evidence: {evidence}\n"
            
        scraped_text = company.get("scraped_content", "")
        
        system_prompt = (
            "You are a critical quality control inspector. Your task is to review a company's evaluation profile "
            "against the raw text logs and verify that every score is backed by real, non-hallucinated facts. "
            "If you detect weak evidence (e.g. C7 scored as Strong but the evidence is generic) or direct "
            "contradiction, suggest an override. Be highly conservative.\n"
            "Format the output strictly as a JSON object."
        )
        
        user_prompt = f"""Review the following profile for the company '{name}' against the scraped context:

--- EVALUATED METRICS ---
{criteria_summary}

--- SCRAPED SOURCE TEXT CONTEXT ---
{scraped_text[:15000]}

--- INSTRUCTIONS ---
1. Check if any cited evidence does NOT appear or is NOT supported by the source text.
2. Verify if the evidence is 'Weak' relative to the score. For example, if C7 (Systems) is 20.0 (Strong) but the evidence is just 'company has a contact page', that is a fail. Set C7 override to 0.0 or 10.0.
3. If C4 (Decision Maker) is 15.0 but there's no mention of a technical background or ERP operations, suggest an override.
4. Calculate a 'Confidence Score' between 0.0 (unreliable) and 1.0 (perfectly verified).
5. Provide detailed 'Validation Notes' explaining your checks.

Return a JSON object matching this schema:
{{
  "Confidence Score": 0.0 to 1.0 (float),
  "Validation Notes": "Summary of what you verified and any issues found.",
  "Suggested Overrides": {{
    "C3 Score": 0.0 or 10.0 or 20.0, (only include if overriding)
    "C4 Score": 0.0 or 7.5 or 15.0, (only include if overriding)
    "C5 Score": 0.0 or 7.5 or 15.0, (only include if overriding)
    "C6 Score": 0.0 or 7.5 or 15.0, (only include if overriding)
    "C7 Score": 0.0 or 10.0 or 20.0, (only include if overriding)
    "C8 Score": 0.0 or 7.5 or 15.0  (only include if overriding)
  }}
}}
"""
        try:
            val_results = self.call_llm_json(system_prompt, user_prompt)
            
            # Map validation metrics
            company["Confidence Score"] = float(val_results.get("Confidence Score", 1.0))
            company["Validation Notes"] = val_results.get("Validation Notes", "Validated successfully.")
            
            # Apply overrides if suggested
            overrides = val_results.get("Suggested Overrides", {})
            if overrides:
                for criterion, new_score in overrides.items():
                    old_score = company.get(criterion)
                    if old_score is not None and old_score != float(new_score):
                        logger.info(f"VALIDATION OVERRIDE for {name} on {criterion}: {old_score} -> {new_score}")
                        company[criterion] = float(new_score)
                        company[f"{criterion.split(' ')[0]} Evidence"] += f" [Validation Note: Score adjusted from {old_score} during validation check because: {company['Validation Notes']}]"
                        
        except Exception as e:
            logger.error(f"Validation step failed for {name}: {e}")
            company["Confidence Score"] = 0.5
            company["Validation Notes"] = f"Validation agent error: {str(e)}"
            
        return company

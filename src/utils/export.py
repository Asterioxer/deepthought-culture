import json
import os
import pandas as pd
from typing import List, Dict, Any
from src.state import CompanyData

def export_to_csv(companies: List[Dict[str, Any]], filepath: str = None) -> str:
    """
    Exports processed companies to CSV format with exact fields requested.
    If filepath is provided, writes to it. Returns the CSV string.
    """
    # Map the dictionaries back into CompanyData objects to format properly
    company_objects = []
    for c in companies:
        if isinstance(c, dict):
            # Parse using Pydantic, supporting aliases
            obj = CompanyData.model_validate(c)
        else:
            obj = c
        company_objects.append(obj)
        
    # Get clean dictionary representation matching user fields
    clean_dicts = [obj.to_dict(clean_for_csv=True) for obj in company_objects]
    df = pd.DataFrame(clean_dicts)
    
    # Ensure correct columns are present even if list is empty
    csv_columns = [
        "Company Name", "Website", "City", "Segment", "Products", "Revenue Band", "Decision Maker",
        "E1 Status", "E2 Status", "C3 Score", "C4 Score", "C5 Score", "C6 Score", "C7 Score", "C8 Score",
        "Federer Score", "Band", "Verdict", "Evidence", "Outreach Hook"
    ]
    
    if df.empty:
        df = pd.DataFrame(columns=csv_columns)
    else:
        # Reorder to match exact specification
        df = df.reindex(columns=csv_columns)
        
    if filepath:
        # Ensure parent directories exist
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        df.to_csv(filepath, index=False)
        
    return df.to_csv(index=False)

def export_to_json(companies: List[Dict[str, Any]], filepath: str = None) -> str:
    """Exports processed companies to a full metadata JSON dump."""
    # Standardize to list of dicts
    dict_list = []
    for c in companies:
        if isinstance(c, CompanyData):
            dict_list.append(c.to_dict(clean_for_csv=False))
        else:
            dict_list.append(c)
            
    json_str = json.dumps(dict_list, indent=2)
    
    if filepath:
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(json_str)
            
    return json_str

def generate_markdown_report(
    city: str,
    industry: str,
    qualified_companies: List[Dict[str, Any]],
    failed_companies: List[Dict[str, Any]],
    filepath: str = None
) -> str:
    """
    Generates a beautifully structured markdown report summarizing the execution
    metrics, distribution, and detailed profiles of discovered companies.
    """
    total_discovered = len(qualified_companies) + len(failed_companies)
    
    # Count bands
    bands = {"A": 0, "B": 0, "C": 0, "D": 0}
    verdicts = {"Strong Fit": 0, "Fit": 0, "Borderline": 0, "Disqualified": 0}
    
    for c in qualified_companies:
        bands[c.get("Band", "B")] = bands.get(c.get("Band", "B"), 0) + 1
        verdicts[c.get("Verdict", "Fit")] = verdicts.get(c.get("Verdict", "Fit"), 0) + 1
    for c in failed_companies:
        bands[c.get("Band", "D")] = bands.get(c.get("Band", "D"), 0) + 1
        verdicts[c.get("Verdict", "Disqualified")] = verdicts.get(c.get("Verdict", "Disqualified"), 0) + 1
        
    yield_pct = (len(qualified_companies) / total_discovered * 100) if total_discovered > 0 else 0.0
    
    # Compute average score of evaluated companies
    scores = [c.get("Federer Score", 0) for c in qualified_companies]
    avg_score = sum(scores) / len(scores) if scores else 0.0
    
    report = f"""# Federer Company Discovery Engine - Summary Report
## Executive Summary
* **Target City**: {city}
* **Industry Segment**: {industry}
* **Total Discovered**: {total_discovered}
* **Qualified Companies (Bands A & B)**: {len(qualified_companies)}
* **Failed / Disqualified Companies**: {len(failed_companies)}
* **Conversion Yield**: {yield_pct:.1f}%
* **Average Federer Score (Qualified)**: {avg_score:.1f} / 100

### Company Distribution by Band
| Band | Description | Count |
|---|---|---|
| **Band A** (80-100) | Strong Federer (High Priority) | {bands['A']} |
| **Band B** (60-79) | Probable Federer | {bands['B']} |
| **Band C** (40-59) | Borderline (Research Further) | {bands['C']} |
| **Band D** (< 40) | Not ICP (Disqualified) | {bands['D']} |

---

## Qualified Companies (Bands A & B)
Here is the list of target companies that matched DeepThought's Federer Ideal Customer Profile.

| Company Name | Website | Federer Score | Band | Verdict | Revenue Band | Key Products |
|---|---|---|---|---|---|---|
"""
    
    for c in qualified_companies:
        report += f"| **{c.get('Company Name')}** | [{c.get('Website')}]({c.get('Website') if c.get('Website').startswith('http') else 'https://' + c.get('Website')}) | {c.get('Federer Score')} | {c.get('Band')} | {c.get('Verdict')} | {c.get('Revenue Band')} | {c.get('Products')} |\n"
        
    report += """
---

## Failed / Disqualified Companies
The following companies were checked but failed to meet either the E1/E2 eligibility gates, or did not score high enough on the Federer criteria.

| Company Name | Website | Eligibility Status | Reason for Failure |
|---|---|---|---|
"""
    
    for c in failed_companies:
        reason = c.get("Evidence") or c.get("validation_notes") or "Failed scoring threshold"
        e_status = f"E1: {c.get('E1 Status', 'FAIL')} / E2: {c.get('E2 Status', 'FAIL')}"
        report += f"| {c.get('Company Name')} | {c.get('Website')} | {e_status} | {reason} |\n"
        
    report += "\n---\n\n## Detailed Profiling Cards (Qualified)\n"
    
    for idx, c in enumerate(qualified_companies):
        report += f"""### {idx+1}. {c.get('Company Name')}
* **Website**: [{c.get('Website')}]({c.get('Website') if c.get('Website').startswith('http') else 'https://' + c.get('Website')})
* **Segment**: {c.get('Segment')}
* **Revenue Band**: {c.get('Revenue Band')}
* **Decision Maker**: {c.get('Decision Maker')} ({c.get('DM Title')}) - {c.get('DM Background')}
* **Federer Score**: **{c.get('Federer Score')} / 100** (Band {c.get('Band')})
* **Verdict**: *{c.get('Verdict')}*

#### Eligibility Gates:
* **E1 (Producer)**: **{c.get('E1 Status')}**
  > {c.get('E1 Evidence')}
* **E2 (Accessible)**: **{c.get('E2 Status')}**
  > {c.get('E2 Evidence')}

#### Score Breakdown:
1. **C3 (Differentiated - 20 max)**: Score: {c.get('C3 Score')}
   > {c.get('C3 Evidence')}
2. **C4 (Decision Maker - 15 max)**: Score: {c.get('C4 Score')}
   > {c.get('C4 Evidence')}
3. **C5 (Growing Sector - 15 max)**: Score: {c.get('C5 Score')}
   > {c.get('C5 Evidence')}
4. **C6 (Growth Signals - 15 max)**: Score: {c.get('C6 Score')}
   > {c.get('C6 Evidence')}
5. **C7 (Systems Maturity - 20 max)**: Score: {c.get('C7 Score')}
   > {c.get('C7 Evidence')}
6. **C8 (Leadership Succession - 15 max)**: Score: {c.get('C8 Score')}
   > {c.get('C8 Evidence')}

#### Personalization Hook:
> **"{c.get('Outreach Hook')}"**

#### Validation Checks:
* **Confidence Level**: {c.get('Confidence Score', 1.0) * 100:.0f}%
* **Notes**: {c.get('Validation Notes') or 'Verified successfully.'}
* **Sources**: {c.get('Evidence Sources')}

---
"""
        
    if filepath:
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report)
            
    return report

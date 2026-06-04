from typing import List, Dict, Any, Optional
from typing_extensions import TypedDict
from pydantic import BaseModel, Field

class CompanyData(BaseModel):
    """Pydantic model representing a researched, scored, and validated company."""
    
    # Core Metadata
    name: str = Field(..., alias="Company Name")
    website: str = Field(..., alias="Website")
    city: str = Field(..., alias="City")
    segment: str = Field(..., alias="Segment")
    products: str = Field(default="", alias="Products")
    revenue_band: str = Field(default="Unknown", alias="Revenue Band")
    decision_maker: str = Field(default="", alias="Decision Maker")
    dm_title: str = Field(default="", alias="DM Title")
    dm_background: str = Field(default="", alias="DM Background")
    
    # Eligibility Gates
    e1_status: str = Field(default="FAIL", alias="E1 Status")  # PASS / FAIL
    e1_evidence: str = Field(default="", alias="E1 Evidence")
    e2_status: str = Field(default="FAIL", alias="E2 Status")  # PASS / FAIL
    e2_evidence: str = Field(default="", alias="E2 Evidence")
    
    # Scoring Criteria
    c3_score: float = Field(default=0.0, alias="C3 Score")  # 0, 10, or 20
    c3_evidence: str = Field(default="", alias="C3 Evidence")
    c4_score: float = Field(default=0.0, alias="C4 Score")  # 0, 7.5, or 15
    c4_evidence: str = Field(default="", alias="C4 Evidence")
    c5_score: float = Field(default=0.0, alias="C5 Score")  # 0, 7.5, or 15
    c5_evidence: str = Field(default="", alias="C5 Evidence")
    c6_score: float = Field(default=0.0, alias="C6 Score")  # 0, 7.5, or 15
    c6_evidence: str = Field(default="", alias="C6 Evidence")
    c7_score: float = Field(default=0.0, alias="C7 Score")  # 0, 10, or 20
    c7_evidence: str = Field(default="", alias="C7 Evidence")
    c8_score: float = Field(default=0.0, alias="C8 Score")  # 0, 7.5, or 15
    c8_evidence: str = Field(default="", alias="C8 Evidence")
    
    # Summary Calculations
    federer_score: float = Field(default=0.0, alias="Federer Score")  # Sum of C3-C8
    band: str = Field(default="D", alias="Band")  # A (80-100), B (60-79), C (40-59), D (<40)
    verdict: str = Field(default="Disqualified", alias="Verdict")  # Strong Fit / Fit / Borderline / Disqualified
    evidence: str = Field(default="", alias="Evidence")  # Verdict reasoning
    outreach_hook: str = Field(default="", alias="Outreach Hook")
    
    # System & Validation Metadata (Internal use & UI details)
    confidence_score: float = Field(default=0.0, alias="Confidence Score")
    validation_notes: str = Field(default="", alias="Validation Notes")
    evidence_sources: str = Field(default="", alias="Evidence Sources")
    scraped_content: str = Field(default="", exclude=True)  # Scraped website text

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True

    def calculate_metrics(self):
        """Calculates federer_score, band, and verdict based on criteria."""
        # Calculate sum
        self.federer_score = (
            self.c3_score + self.c4_score + self.c5_score + 
            self.c6_score + self.c7_score + self.c8_score
        )
        
        # Determine Band
        if self.e1_status == "FAIL" or self.e2_status == "FAIL":
            self.band = "D"
            self.verdict = "Disqualified"
        else:
            if self.federer_score >= 80:
                self.band = "A"
                self.verdict = "Strong Fit"
            elif self.federer_score >= 60:
                self.band = "B"
                self.verdict = "Fit"
            elif self.federer_score >= 40:
                self.band = "C"
                self.verdict = "Borderline"
            else:
                self.band = "D"
                self.verdict = "Disqualified"
                
        # If C7 systems maturity is 0 (Weak), DT usually disqualifies or flags as Borderline
        # Example 4 in assignment says "C7=0 is a structural disqualifier for DT's model"
        if self.c7_score == 0.0 and self.verdict in ["Strong Fit", "Fit"]:
            self.verdict = "Borderline"
            
        return self

    def to_dict(self, clean_for_csv: bool = False) -> Dict[str, Any]:
        """Converts model to dictionary, optionally formatted with CSV-friendly headers."""
        data = self.model_dump(by_alias=True)
        if clean_for_csv:
            # Only keep the fields specified by the user for CSV export
            csv_fields = [
                "Company Name", "Website", "City", "Segment", "Products", "Revenue Band", "Decision Maker",
                "E1 Status", "E2 Status", "C3 Score", "C4 Score", "C5 Score", "C6 Score", "C7 Score", "C8 Score",
                "Federer Score", "Band", "Verdict", "Evidence", "Outreach Hook"
            ]
            return {k: data.get(k, "") for k in csv_fields}
        return data


class GraphState(TypedDict):
    """LangGraph State representation for the multi-agent execution flow."""
    city: str
    industry: str
    max_companies: int
    
    # Active LLM Provider configuration (with fallback supports)
    llm_provider: str
    google_api_key: Optional[str]
    groq_api_key: Optional[str]
    ollama_base_url: Optional[str]
    ollama_model: Optional[str]
    
    # Legacy / Custom LLM configurations (retained for backward compatibility)
    api_key: Optional[str]
    base_url: Optional[str]
    model: Optional[str]
    
    # Search Expansion Parameters
    auto_broaden: bool
    broaden_count: int
    
    # Company Lists
    discovered_companies: List[Dict[str, Any]]  # Raw candidates: [{"name": "...", "website": "..."}]
    processed_companies: List[Dict[str, Any]]   # Fully scored companies
    failed_companies: List[Dict[str, Any]]      # Disqualified companies (either E1/E2 fail or low score)
    
    # Dashboard & Progress Metrics
    logs: List[str]
    progress: float
    status: str  # e.g., 'discovering', 'researching', 'scoring', 'completed'

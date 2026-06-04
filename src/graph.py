import asyncio
import logging
from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from src.state import GraphState, CompanyData
from src.agents.discovery import DiscoveryAgent
from src.agents.research import ResearchAgent
from src.agents.eligibility import EligibilityAgent
from src.agents.scoring import FedererScoringAgent
from src.agents.validation import ValidationAgent
from src.agents.outreach import OutreachAgent
from src.config import Config

logger = logging.getLogger(__name__)

# Semaphores to limit concurrency and protect API rate limits / network limits
MAX_SCRAPING_CONCURRENCY = Config.get_max_concurrent_scrapes()
sem = asyncio.Semaphore(MAX_SCRAPING_CONCURRENCY)

async def discovery_node(state: GraphState) -> Dict[str, Any]:
    """Node that searches and discovers matching company names and websites."""
    state["status"] = "discovering"
    state["progress"] = 10.0
    msg = f"Starting discovery for '{state['industry']}' in '{state['city']}..."
    state["logs"].append(msg)
    logger.info(msg)
    
    agent = DiscoveryAgent(
        provider=state.get("llm_provider"),
        google_api_key=state.get("google_api_key"),
        groq_api_key=state.get("groq_api_key"),
        ollama_base_url=state.get("ollama_base_url"),
        ollama_model=state.get("ollama_model"),
        api_key=state.get("api_key"),
        base_url=state.get("base_url"),
        model=state.get("model")
    )
    
    # Run discovery (queries Google/DDG and extracts companies)
    try:
        discovered = agent.discover(state["city"], state["industry"], state["max_companies"])
        
        state["discovered_companies"] = discovered
        msg = f"Discovered {len(discovered)} potential company profiles."
        state["logs"].append(msg)
        logger.info(msg)
    except Exception as e:
        msg = f"Discovery error: {str(e)}"
        state["logs"].append(msg)
        logger.error(msg)
        state["discovered_companies"] = []
        
    state["progress"] = 25.0
    return state

async def research_node(state: GraphState) -> Dict[str, Any]:
    """Node that crawls website and searches metadata for all discovered companies in parallel."""
    state["status"] = "researching"
    state["progress"] = 30.0
    candidates = state.get("discovered_companies", [])
    
    if not candidates:
        state["logs"].append("No discovered companies to research. Skipping research.")
        return state
        
    msg = f"Beginning detailed web crawling & fact research for {len(candidates)} companies..."
    state["logs"].append(msg)
    logger.info(msg)
    
    agent = ResearchAgent(
        provider=state.get("llm_provider"),
        google_api_key=state.get("google_api_key"),
        groq_api_key=state.get("groq_api_key"),
        ollama_base_url=state.get("ollama_base_url"),
        ollama_model=state.get("ollama_model"),
        api_key=state.get("api_key"),
        base_url=state.get("base_url"),
        model=state.get("model")
    )
    
    # Async worker helper using Semaphore
    async def worker(company):
        async with sem:
            name = company.get("name", "Unknown")
            state["logs"].append(f"Researching: {name} (website crawl & search)...")
            try:
                # Scrapes website + supplemental searches + LLM facts
                return await agent.research_company(company)
            except Exception as e:
                logger.error(f"Research node failed for {name}: {e}")
                company["scraped_content"] = f"Research failed: {str(e)}"
                return company

    # Run research concurrently with bounded workers
    tasks = [worker(c) for c in candidates]
    researched_companies = await asyncio.gather(*tasks)
    
    state["discovered_companies"] = researched_companies
    state["logs"].append("Research phase completed.")
    state["progress"] = 55.0
    return state

async def processing_pipeline_node(state: GraphState) -> Dict[str, Any]:
    """
    Node that runs Eligibility -> Scoring -> Validation -> Outreach
    sequentially for each researched company. Run concurrently across companies.
    """
    state["status"] = "processing"
    state["progress"] = 60.0
    researched = state.get("discovered_companies", [])
    
    if not researched:
        state["logs"].append("No companies found to process.")
        return state
        
    msg = f"Initiating eligibility audit, scoring, validation, and hook generation for {len(researched)} companies..."
    state["logs"].append(msg)
    logger.info(msg)
    
    # Instantiate agents with multi-provider details
    elig_kwargs = {
        "provider": state.get("llm_provider"),
        "google_api_key": state.get("google_api_key"),
        "groq_api_key": state.get("groq_api_key"),
        "ollama_base_url": state.get("ollama_base_url"),
        "ollama_model": state.get("ollama_model"),
        "api_key": state.get("api_key"),
        "base_url": state.get("base_url"),
        "model": state.get("model")
    }
    
    eligibility_agent = EligibilityAgent(**elig_kwargs)
    scoring_agent = FedererScoringAgent(**elig_kwargs)
    validation_agent = ValidationAgent(**elig_kwargs)
    outreach_agent = OutreachAgent(**elig_kwargs)
    
    qualified_list = []
    failed_list = []
    
    # Process a single company end-to-end
    def process_single_company(company_dict):
        name = company_dict.get("name", "Unknown")
        
        # 1. Eligibility Gate
        state["logs"].append(f"Eligibility Audit: Checking {name}...")
        co = eligibility_agent.evaluate_eligibility(company_dict)
        
        if co.get("Verdict") == "Disqualified":
            state["logs"].append(f"Disqualified {name}: {co.get('Evidence')}")
            # Convert to CompanyData to calculate and validate
            comp_obj = CompanyData.model_validate(co)
            comp_obj.calculate_metrics()
            failed_list.append(comp_obj.to_dict())
            return
            
        # 2. Federer Scoring
        state["logs"].append(f"Scoring Federer Criteria: {name}...")
        co = scoring_agent.score_company(co)
        
        # 3. Validation Fact-Check
        state["logs"].append(f"Validating & Fact-Checking: {name}...")
        co = validation_agent.validate_profile(co)
        
        # 4. Outreach Hook Generation
        state["logs"].append(f"Writing outreach hooks: {name}...")
        co = outreach_agent.generate_hook(co)
        
        # 5. Compile final metrics
        comp_obj = CompanyData.model_validate(co)
        comp_obj.calculate_metrics()
        
        final_dict = comp_obj.to_dict()
        if comp_obj.verdict == "Disqualified":
            state["logs"].append(f"Disqualified {name} due to low Federer score ({comp_obj.federer_score}) or missing systems.")
            failed_list.append(final_dict)
        else:
            state["logs"].append(f"QUALIFIED: {name} (Score: {comp_obj.federer_score}, Band: {comp_obj.band})")
            qualified_list.append(final_dict)

    # We run the pipeline concurrently using executors
    loop = asyncio.get_event_loop()
    
    async def run_in_thread(co):
        await loop.run_in_executor(None, process_single_company, co)
        
    await asyncio.gather(*[run_in_thread(c) for c in researched])
    
    state["processed_companies"] = qualified_list
    state["failed_companies"] = failed_list
    state["logs"].append("Processing pipeline finished.")
    state["progress"] = 90.0
    return state

async def compile_node(state: GraphState) -> Dict[str, Any]:
    """Final node that sorts records and reports statistics. Triggers broadening if needed."""
    # Sort qualified companies by score descending
    state["processed_companies"] = sorted(
        state.get("processed_companies", []),
        key=lambda x: x.get("Federer Score", 0.0),
        reverse=True
    )
    
    qualified_count = len(state["processed_companies"])
    failed_count = len(state["failed_companies"])
    
    msg = f"Pipeline execution completed. Qualified: {qualified_count} | Failed: {failed_count}."
    state["logs"].append(msg)
    logger.info(msg)
    
    # Check if we need to auto-broaden search target city
    auto_broaden = state.get("auto_broaden", False)
    broaden_count = state.get("broaden_count", 0)
    

    if auto_broaden and qualified_count == 0 and broaden_count < 3:
        cities = ["Hyderabad", "Pune", "Ahmedabad", "Chennai", "Coimbatore", "Vadodara", "Bengaluru", "Indore", "Surat", "Ludhiana", "Kolhapur"]
        current_city = state.get("city", "Hyderabad")
        try:
            idx = cities.index(current_city)
            next_city = cities[(idx + 1) % len(cities)]
        except ValueError:
            next_city = cities[0]
            
        state["city"] = next_city
        state["broaden_count"] = broaden_count + 1
        
        # Reset temporary arrays & reset progress to start a loop
        state["discovered_companies"] = []
        state["progress"] = 5.0
        state["status"] = "broadening"
        
        loop_msg = f"⚠️ [AUTO-BROADEN] No qualified targets found in {current_city}. pivoting target parameters to: City='{next_city}' (Attempt {state['broaden_count']}/3)..."
        state["logs"].append(loop_msg)
        logger.info(loop_msg)
    else:
        state["status"] = "completed"
        state["progress"] = 100.0
        
    return state

def check_results_and_broaden(state: GraphState) -> str:
    """Conditional edge checking if we need to loop back to discovery."""
    if state.get("status") == "broadening":
        return "discover"
    return "end"

# Constructing the LangGraph Workflow
def build_discovery_graph() -> StateGraph:
    workflow = StateGraph(GraphState)
    
    # Add Nodes
    workflow.add_node("discover", discovery_node)
    workflow.add_node("research", research_node)
    workflow.add_node("process", processing_pipeline_node)
    workflow.add_node("compile", compile_node)
    
    # Add Edges
    workflow.set_entry_point("discover")
    workflow.add_edge("discover", "research")
    workflow.add_edge("research", "process")
    workflow.add_edge("process", "compile")
    
    # Add Conditional loop from compile
    workflow.add_conditional_edges(
        "compile",
        check_results_and_broaden,
        {
            "discover": "discover",
            "end": END
        }
    )
    
    return workflow.compile()

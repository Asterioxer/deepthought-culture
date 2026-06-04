import streamlit as st
import pandas as pd
import asyncio
import os
import json
import logging
from src.graph import build_discovery_graph
from src.state import CompanyData
from src.utils.export import export_to_csv, export_to_json, generate_markdown_report

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Premium CSS Styling
st.set_page_config(
    page_title="Federer Company Discovery Engine",
    page_icon="🎾",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .reportview-container {
        background: #0F172A;
    }
    .metric-card {
        background: rgba(30, 41, 59, 0.5);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        text-align: center;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #10B981;
    }
    .metric-label {
        font-size: 0.875rem;
        color: #94A3B8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .custom-log {
        background-color: #020617;
        color: #38BDF8;
        font-family: 'Courier New', Courier, monospace;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #1E293B;
        max-height: 300px;
        overflow-y: scroll;
        white-space: pre-wrap;
    }
</style>
""", unsafe_allow_html=True)

# App Header
st.title("🎾 Federer Company Discovery Engine")
st.markdown(
    "Identify and score Indian companies that match DeepThought's **Federer Ideal Customer Profile (ICP)**. "
    "Refactored to support free and local LLM providers (Gemini, Groq, Ollama) with automated sequential fallbacks."
)

# Setup Sidebar Configurations
st.sidebar.image("https://img.icons8.com/nolan/96/tennis-racket-and-ball.png", width=80)
st.sidebar.header("⚙️ Configuration")

# Resolve default configurations from environment
default_provider = os.environ.get("LLM_PROVIDER", "gemini").lower().strip()
env_google_key = os.environ.get("GOOGLE_API_KEY", "")
env_groq_key = os.environ.get("GROQ_API_KEY", "")
env_ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
env_ollama_model = os.environ.get("OLLAMA_MODEL", "qwen3:8b")

st.sidebar.subheader("🤖 LLM Provider Settings")
provider_options = ["Gemini", "Groq", "Ollama"]
default_idx = 0
if default_provider == "groq":
    default_idx = 1
elif default_provider == "ollama":
    default_idx = 2

selected_provider = st.sidebar.selectbox("Active LLM Provider", options=provider_options, index=default_idx)

# Dynamic fields depending on active provider
google_key = ""
groq_key = ""
ollama_url = "http://localhost:11434"
ollama_model = "qwen2.5:7b"

if selected_provider == "Gemini":
    google_key = st.sidebar.text_input("Google API Key", value=env_google_key, type="password", help="Enter your Google AI Studio API Key.")
    st.sidebar.success("Active: **Gemini (Primary)**")
elif selected_provider == "Groq":
    groq_key = st.sidebar.text_input("Groq API Key", value=env_groq_key, type="password", help="Enter your Groq Console API Key.")
    st.sidebar.success("Active: **Groq (Secondary)**")
elif selected_provider == "Ollama":
    ollama_url = st.sidebar.text_input("Ollama Base URL", value=env_ollama_url, help="Local Ollama service URL (default: http://localhost:11434).")
    ollama_model = st.sidebar.text_input("Ollama Model Name", value=env_ollama_model, help="Name of the local pulled model (default: qwen3:8b).")
    st.sidebar.success("Active: **Ollama (Local Fallback)**")

st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 Scoring Guidelines")
st.sidebar.info(
    "**Eligibility Gates:**\n"
    "* **E1:** Producer (in-house facility)\n"
    "* **E2:** Accessible (India HQ/Ops)\n\n"
    "**Scoring Weights:**\n"
    "* **C3:** Differentiated (20)\n"
    "* **C4:** Decision Maker Quality (15)\n"
    "* **C5:** Growing Sector (15)\n"
    "* **C6:** Growth Signals (15)\n"
    "* **C7:** Systems Maturity (20)\n"
    "* **C8:** Leadership Succession (15)"
)

# Main Inputs Form
st.subheader("🔍 Target Parameters")
col1, col2, col3 = st.columns(3)

with col1:
    city_options = ["Hyderabad", "Pune", "Ahmedabad", "Chennai", "Coimbatore", "Vadodara", "Bengaluru", "Indore", "Surat", "Ludhiana", "Kolhapur"]
    city_input = st.selectbox("Select Target City", options=city_options, index=0)
    
with col2:
    segment_options = [
        "Specialty biotech (probiotics, enzymes, fermentation services)",
        "Specialty diagnostics & life-science tools",
        "Custom synthesis & specialty chemicals",
        "Performance chemicals (polymer additives, coatings & resins)",
        "Complex APIs & regulated pharma",
        "Medical devices",
        "Hybrid seeds & specialty agri-inputs",
        "Specialty food & nutraceutical ingredients",
        "Industrial sensors & instrumentation",
        "Animal health & veterinary biologics",
        "Technical textiles & specialty yarns",
        "Precision auto components & engineering",
        "Specialty food processing",
        "Designer / artisanal manufacturing"
    ]
    segment_input = st.selectbox("Select Industry Segment", options=segment_options, index=0)

with col3:
    max_companies_input = st.slider("Maximum Companies to Discover", min_value=1, max_value=20, value=3, step=1, help="Limit discovery search for demonstration. Scalable up to 1000+.")

# Auto-Broaden search parameter
auto_broaden_input = st.checkbox(
    "🔄 Auto-Broaden Search",
    value=False,
    help="If enabled, the engine will automatically cycle through nearby/adjacent target cities if the search in your selected city returns 0 qualified targets."
)

# State initialization
if "pipeline_results" not in st.session_state:
    st.session_state.pipeline_results = None
if "logs" not in st.session_state:
    st.session_state.logs = []
if "running" not in st.session_state:
    st.session_state.running = False

# Async streaming executor
async def run_pipeline(state_input):
    graph = build_discovery_graph()
    logs_container = st.empty()
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    current_state = {
        "city": state_input["city"],
        "industry": state_input["industry"],
        "max_companies": state_input["max_companies"],
        "llm_provider": state_input["llm_provider"],
        "google_api_key": state_input["google_api_key"],
        "groq_api_key": state_input["groq_api_key"],
        "ollama_base_url": state_input["ollama_base_url"],
        "ollama_model": state_input["ollama_model"],
        "auto_broaden": state_input["auto_broaden"],
        "broaden_count": 0,
        "discovered_companies": [],
        "processed_companies": [],
        "failed_companies": [],
        "logs": [],
        "progress": 0.0,
        "status": "idle"
    }
    
    # Stream the graph step execution
    async for event in graph.astream(current_state):
        for node_name, node_state in event.items():
            # Update key variables in execution context
            if "city" in node_state:
                current_state["city"] = node_state["city"]
            if "broaden_count" in node_state:
                current_state["broaden_count"] = node_state["broaden_count"]
                
            if "logs" in node_state:
                current_state["logs"].extend([l for l in node_state["logs"] if l not in current_state["logs"]])
                # Show logs dynamically
                log_content = "\n".join(current_state["logs"])
                logs_container.markdown(f'<div class="custom-log">{log_content}</div>', unsafe_allow_html=True)
            if "progress" in node_state:
                current_state["progress"] = node_state["progress"]
                progress_bar.progress(node_state["progress"] / 100.0)
            if "status" in node_state:
                current_state["status"] = node_state["status"]
                status_text.write(f"Engine Phase: **{node_state['status'].upper()}** | Active Target City: **{current_state['city']}**")
            
            # Keep track of records
            if "discovered_companies" in node_state:
                current_state["discovered_companies"] = node_state["discovered_companies"]
            if "processed_companies" in node_state:
                current_state["processed_companies"] = node_state["processed_companies"]
            if "failed_companies" in node_state:
                current_state["failed_companies"] = node_state["failed_companies"]
                
    return current_state

# Button to trigger
if st.button("🚀 Start Discovery Engine", disabled=st.session_state.running):
    # Perform input validation
    valid = True
    if selected_provider == "Gemini" and not google_key:
        st.error("Error: Please provide a valid Google API Key in the sidebar config.")
        valid = False
    elif selected_provider == "Groq" and not groq_key:
        st.error("Error: Please provide a valid Groq API Key in the sidebar config.")
        valid = False
        
    if valid:
        st.session_state.running = True
        st.session_state.logs = []
        
        # Prepare inputs
        inputs = {
            "city": city_input,
            "industry": segment_input,
            "max_companies": max_companies_input,
            "llm_provider": selected_provider.lower(),
            "google_api_key": google_key,
            "groq_api_key": groq_key,
            "ollama_base_url": ollama_url,
            "ollama_model": ollama_model,
            "auto_broaden": auto_broaden_input
        }
        
        # Run async loop
        with st.spinner("Executing Federer Multi-Agent Pipeline..."):
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                final_state = loop.run_until_complete(run_pipeline(inputs))
                st.session_state.pipeline_results = final_state
                st.success("Discovery and evaluation completed successfully!")
            except Exception as e:
                st.error(f"Pipeline execution encountered an error: {e}")
                logger.exception(e)
            finally:
                st.session_state.running = False

# Render results if available
if st.session_state.pipeline_results:
    results = st.session_state.pipeline_results
    qualified = results.get("processed_companies", [])
    failed = results.get("failed_companies", [])
    
    st.markdown("---")
    st.subheader("📊 Analytics Overview")
    
    # KPI Grid
    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
    total_scanned = len(qualified) + len(failed)
    yield_rate = (len(qualified) / total_scanned * 100) if total_scanned > 0 else 0.0
    
    with kpi_col1:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{total_scanned}</div><div class="metric-label">Total Discovered</div></div>', unsafe_allow_html=True)
    with kpi_col2:
        st.markdown(f'<div class="metric-card"><div class="metric-value" style="color: #10B981;">{len(qualified)}</div><div class="metric-label">Qualified (Bands A/B)</div></div>', unsafe_allow_html=True)
    with kpi_col3:
        st.markdown(f'<div class="metric-card"><div class="metric-value" style="color: #EF4444;">{len(failed)}</div><div class="metric-label">Failed / Disqualified</div></div>', unsafe_allow_html=True)
    with kpi_col4:
        st.markdown(f'<div class="metric-card"><div class="metric-value" style="color: #F59E0B;">{yield_rate:.1f}%</div><div class="metric-label">Conversion Yield</div></div>', unsafe_allow_html=True)
        
    # Main results display tabs
    tab_qual, tab_fail, tab_inspect, tab_export = st.tabs([
        "✅ Qualified Companies", 
        "❌ Failed Companies", 
        "🔎 Detailed Company Inspector", 
        "💾 Export & Reports"
    ])
    
    with tab_qual:
        st.markdown("### Target Outreach Prospect List")
        if not qualified:
            st.info("No companies qualified under the Federer criteria.")
        else:
            qual_df = pd.DataFrame([CompanyData.model_validate(c).to_dict(clean_for_csv=True) for c in qualified])
            st.dataframe(qual_df, use_container_width=True)
            
    with tab_fail:
        st.markdown("### Disqualified / Failed Candidates")
        if not failed:
            st.info("No companies failed eligibility gates or scoring bands.")
        else:
            fail_rows = []
            for c in failed:
                fail_rows.append({
                    "Company Name": c.get("Company Name"),
                    "Website": c.get("Website"),
                    "E1 Status": c.get("E1 Status"),
                    "E2 Status": c.get("E2 Status"),
                    "Federer Score": c.get("Federer Score", 0),
                    "Rejection Reason": c.get("Evidence") or c.get("Validation Notes") or "Below target scoring threshold."
                })
            st.dataframe(pd.DataFrame(fail_rows), use_container_width=True)
            
    with tab_inspect:
        st.markdown("### Profile Card Explorer")
        if not qualified:
            st.info("No qualified companies to inspect.")
        else:
            company_names = [c.get("Company Name") for c in qualified]
            selected_name = st.selectbox("Select a company to inspect:", options=company_names)
            
            # Find selected company object
            comp = next(c for c in qualified if c.get("Company Name") == selected_name)
            
            st.markdown(f"## {comp.get('Company Name')}")
            st.markdown(f"🌐 **Website**: {comp.get('Website')} | 📍 **City**: {comp.get('City')} | 🏭 **Segment**: {comp.get('Segment')}")
            
            col_left, col_right = st.columns(2)
            with col_left:
                st.markdown("### 📋 Executive Details")
                st.write(f"**Decision Maker**: {comp.get('Decision Maker')} ({comp.get('DM Title')})")
                st.write(f"**DM Academic/Professional Background**:\n{comp.get('DM Background')}")
                st.write(f"**Manufacturing Products**:\n{comp.get('Products')}")
                st.write(f"**Estimated Revenue Band**: {comp.get('Revenue Band')}")
                
                st.markdown("---")
                st.markdown("### 🏆 Federer Score Card")
                st.markdown(f"### Score: **{comp.get('Federer Score')} / 100** (Band {comp.get('Band')})")
                st.markdown(f"**Status**: *{comp.get('Verdict')}*")
                
            with col_right:
                st.markdown("### 🛠️ Criteria Evaluation & Citations")
                
                with st.expander(f"C3: Differentiated (Score: {comp.get('C3 Score')}/20)"):
                    st.write(comp.get("C3 Evidence"))
                with st.expander(f"C4: Decision Maker Quality (Score: {comp.get('C4 Score')}/15)"):
                    st.write(comp.get("C4 Evidence"))
                with st.expander(f"C5: Growing Sector (Score: {comp.get('C5 Score')}/15)"):
                    st.write(comp.get("C5 Evidence"))
                with st.expander(f"C6: Growth Signals (Score: {comp.get('C6 Score')}/15)"):
                    st.write(comp.get("C6 Evidence"))
                with st.expander(f"C7: Systems Maturity (Score: {comp.get('C7 Score')}/20)"):
                    st.write(comp.get("C7 Evidence"))
                with st.expander(f"C8: Leadership Succession (Score: {comp.get('C8 Score')}/15)"):
                    st.write(comp.get("C8 Evidence"))
                    
            st.markdown("---")
            st.markdown("### 📝 Personalized Outreach Hook")
            st.warning(f'"{comp.get("Outreach Hook")}"')
            
            st.markdown("### 🔍 Validation and Fact-Check")
            st.info(f"**Confidence Score**: {comp.get('Confidence Score', 1.0)*100:.0f}% | **Validation Audit**: {comp.get('Validation Notes')}")
            
    with tab_export:
        st.markdown("### Download Data Deliverables")
        
        csv_data = export_to_csv(qualified, filepath=None)
        json_data = export_to_json(qualified + failed, filepath=None)
        md_report = generate_markdown_report(results["city"], results["industry"], qualified, failed, filepath=None)
        
        col_down1, col_down2, col_down3 = st.columns(3)
        with col_down1:
            st.download_button(
                label="📥 Download Qualified List (CSV)",
                data=csv_data,
                file_name=f"federer_qualified_{results['city'].lower()}_{results['industry'].lower().replace(' ', '_')}.csv",
                mime="text/csv"
            )
        with col_down2:
            st.download_button(
                label="📥 Download Full metadata (JSON)",
                data=json_data,
                file_name=f"federer_metadata_{results['city'].lower()}_{results['industry'].lower().replace(' ', '_')}.json",
                mime="application/json"
            )
        with col_down3:
            st.download_button(
                label="📥 Download Summary Report (MD)",
                data=md_report,
                file_name=f"federer_report_{results['city'].lower()}_{results['industry'].lower().replace(' ', '_')}.md",
                mime="text/markdown"
            )
            
        st.markdown("---")
        st.markdown("### 📋 Preview Summary Report")
        st.markdown(md_report)

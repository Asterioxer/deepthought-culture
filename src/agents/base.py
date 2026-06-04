import json
import logging
import re
import time
from typing import Dict, Any, Optional
from langchain_core.messages import SystemMessage, HumanMessage
from src.config import Config
from src.providers.factory import ProviderFactory

logger = logging.getLogger(__name__)


class BaseAgent:
    """Base class for all Multi-Agent nodes in the Discovery Engine."""

    def __init__(self,
                 provider: str = None,
                 google_api_key: str = None,
                 groq_api_key: str = None,
                 ollama_base_url: str = None,
                 ollama_model: str = None,
                 openrouter_api_key: str = None,
                 openrouter_model: str = None,
                 api_key: str = None,       # Legacy/OpenAI key
                 base_url: str = None,      # Legacy/OpenAI base URL
                 model: str = None):        # Legacy/OpenAI model name

        self.provider_name = provider or Config.get_provider()
        self.google_api_key = google_api_key or Config.get_google_api_key()
        self.groq_api_key = groq_api_key or Config.get_groq_api_key()
        self.ollama_base_url = ollama_base_url or Config.get_ollama_base_url()
        self.ollama_model = ollama_model or Config.get_ollama_model()
        self.openrouter_api_key = openrouter_api_key or Config.get_openrouter_api_key()
        self.openrouter_model = openrouter_model or Config.get_openrouter_model()
        self.legacy_api_key = api_key
        self.legacy_base_url = base_url
        self.legacy_model = model

    def call_llm(self, system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
        """
        Invokes the LLM with system and user prompts.
        Fallback chain: OpenRouter -> Gemini -> Groq -> Ollama.
        Per-minute rate limits: waits briefly and retries on the same provider (up to 3x).
        Daily/project quota exhaustion: cascades immediately to the next provider.
        """
        active = self.provider_name.lower().strip()

        if active == "openrouter":
            chain = ["openrouter", "gemini", "groq", "ollama"]
        elif active == "gemini":
            chain = ["gemini", "groq", "ollama"]
        elif active == "groq":
            chain = ["groq", "ollama"]
        elif active == "ollama":
            chain = ["ollama"]
        else:
            chain = [active, "openrouter", "gemini", "groq", "ollama"]

        last_error = None

        for prov in chain:
            # Skip providers with missing credentials
            if prov == "openrouter" and not self.openrouter_api_key:
                logger.warning("Skipping OpenRouter: OPENROUTER_API_KEY not configured.")
                continue
            if prov == "gemini" and not self.google_api_key:
                logger.warning("Skipping Gemini: GOOGLE_API_KEY not configured.")
                continue
            if prov == "groq" and not self.groq_api_key:
                logger.warning("Skipping Groq: GROQ_API_KEY not configured.")
                continue

            # Resolve provider-specific params
            prov_api_key = None
            prov_base_url = None
            prov_model = None

            if prov == "openrouter":
                prov_api_key = self.openrouter_api_key
                prov_model = self.openrouter_model or "google/gemini-2.5-flash:free"
            elif prov == "gemini":
                prov_api_key = self.google_api_key
                prov_model = "gemini-2.0-flash"
            elif prov == "groq":
                prov_api_key = self.groq_api_key
                prov_model = "llama-3.1-8b-instant"
            elif prov == "ollama":
                prov_base_url = self.ollama_base_url
                prov_model = self.ollama_model
            else:
                prov_api_key = self.legacy_api_key or self.google_api_key
                prov_base_url = self.legacy_base_url
                prov_model = self.legacy_model

            # Inner retry loop for per-minute rate limits
            for attempt in range(3):
                try:
                    logger.info(f"Invoking LLM Provider: {prov} (JSON Mode: {json_mode}, attempt {attempt + 1})")
                    llm = ProviderFactory.get_llm(
                        provider_name=prov,
                        api_key=prov_api_key,
                        base_url=prov_base_url,
                        model=prov_model,
                        temperature=0.15,
                        json_mode=json_mode
                    )
                    messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
                    response = llm.invoke(messages)
                    return response.content

                except Exception as e:
                    err_str = str(e)
                    is_rate_limit = (
                        "429" in err_str
                        or "rate_limit" in err_str.lower()
                        or "RESOURCE_EXHAUSTED" in err_str
                    )

                    if is_rate_limit:
                        # Daily / project quota → cascade to next provider immediately
                        is_daily_exhausted = (
                            "tokens per day" in err_str.lower()
                            or "GenerateRequestsPerDay" in err_str
                            or "limit: 0" in err_str.lower()
                            or bool(re.search(r"try again in \d+h", err_str))
                        )
                        if is_daily_exhausted:
                            logger.warning(f"Provider '{prov}' daily quota exhausted. Cascading to next provider.")
                            last_error = e
                            break  # exit inner retry loop → try next provider

                        # Per-minute limit → extract wait time and retry
                        m = re.search(r"try again in (\d+(?:\.\d+)?)s", err_str)
                        wait_secs = min(float(m.group(1)) + 1.0 if m else 15.0, 30.0)
                        if attempt < 2:
                            logger.warning(f"Provider '{prov}' per-minute limit hit. Retrying in {wait_secs:.1f}s...")
                            time.sleep(wait_secs)
                            continue
                        # Exhausted retries
                        logger.warning(f"Provider '{prov}' still rate-limited after {attempt + 1} retries. Cascading.")
                        last_error = e
                        break
                    else:
                        logger.warning(f"Provider '{prov}' failed: {e}. Cascading to next provider.")
                        last_error = e
                        break  # non-rate-limit error → cascade immediately

        err_msg = f"All LLM providers in the fallback chain failed. Last exception: {last_error}"
        logger.error(err_msg)
        raise RuntimeError(err_msg) from last_error

    def call_llm_json(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Calls the LLM and guarantees a parsed JSON response, with a 3-attempt retry policy."""
        json_sys_prompt = (
            f"{system_prompt}\n\n"
            "CRITICAL: Your response must be a single, valid JSON object or array. "
            "Do NOT include any conversational intro/outro text. "
            "Do NOT wrap it in markdown code blocks (no ```json ... ```)."
        )

        last_error = None
        for attempt in range(3):
            try:
                raw_response = self.call_llm(json_sys_prompt, user_prompt, json_mode=True)
                return self.parse_json_response(raw_response)
            except Exception as e:
                logger.warning(f"LLM JSON extraction attempt {attempt + 1} failed: {e}")
                last_error = e

        raise ValueError(f"Failed to get a valid JSON response from LLM after 3 attempts. Last error: {last_error}")

    def parse_json_response(self, text: str) -> Dict[str, Any]:
        """Cleans and parses a JSON string. Handles markdown code fences and extracts embedded JSON."""
        cleaned = text.strip()

        # Strip markdown code fences
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Try extracting a JSON object
            match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError as e:
                    logger.error(f"Regex extracted block failed parsing: {match.group(1)[:200]}")
                    raise e
            # Try extracting a JSON array
            match = re.search(r"(\[.*\])", cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    pass
            raise ValueError(f"Response is not valid JSON:\n{text[:500]}")

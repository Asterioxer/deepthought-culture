import os
from dotenv import load_dotenv

# Load any local .env file
load_dotenv()

class Config:
    """Manages system configurations and environment variables."""
    
    @staticmethod
    def get_provider(override: str = None) -> str:
        """Returns the active LLM provider (gemini, groq, or ollama). Default: gemini."""
        return (override or os.environ.get("LLM_PROVIDER") or "gemini").strip().lower()

    @staticmethod
    def get_google_api_key(override: str = None) -> str:
        """Returns the Google API key for Gemini models."""
        return (override or os.environ.get("GOOGLE_API_KEY") or "").strip()

    @staticmethod
    def get_groq_api_key(override: str = None) -> str:
        """Returns the Groq API key."""
        return (override or os.environ.get("GROQ_API_KEY") or "").strip()

    @staticmethod
    def get_ollama_base_url(override: str = None) -> str:
        """Returns the Ollama base URL (default: http://localhost:11434)."""
        return (override or os.environ.get("OLLAMA_BASE_URL") or "http://localhost:11434").strip()

    @staticmethod
    def get_ollama_model(override: str = None) -> str:
        """Returns the Ollama model name (default: qwen3:8b)."""
        return (override or os.environ.get("OLLAMA_MODEL") or "qwen3:8b").strip()

    @staticmethod
    def get_max_concurrent_scrapes() -> int:
        """Returns the maximum number of concurrent scraping workers."""
        try:
            return int(os.environ.get("MAX_CONCURRENT_SCRAPES", "5"))
        except ValueError:
            return 5

    @staticmethod
    def get_playwright_timeout() -> int:
        """Returns the Playwright page load timeout in milliseconds."""
        try:
            return int(os.environ.get("PLAYWRIGHT_TIMEOUT_MS", "15000"))
        except ValueError:
            return 15000

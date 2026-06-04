import logging
from src.providers.gemini_provider import GeminiProvider
from src.providers.groq_provider import GroqProvider
from src.providers.ollama_provider import OllamaProvider
from src.providers.openrouter_provider import OpenRouterProvider
from src.config import Config

logger = logging.getLogger(__name__)

class ProviderFactory:
    """Factory pattern to resolve and retrieve LLM provider wrappers."""
    
    @staticmethod
    def get_provider(provider_name: str = None):
        """Resolves the provider name, defaulting to config settings or gemini."""
        name = (provider_name or Config.get_provider() or "gemini").lower().strip()
        
        if name == "gemini":
            return GeminiProvider()
        elif name == "groq":
            return GroqProvider()
        elif name == "ollama":
            return OllamaProvider()
        elif name == "openrouter":
            return OpenRouterProvider()
        else:
            logger.error(f"Unsupported provider requested: {name}. Defaulting to Gemini.")
            return GeminiProvider()

    @staticmethod
    def get_llm(provider_name: str = None, 
                api_key: str = None, 
                base_url: str = None, 
                model: str = None, 
                temperature: float = 0.15, 
                json_mode: bool = False):
        """Instantiates the correct LangChain model with specified settings."""
        provider = ProviderFactory.get_provider(provider_name)
        return provider.get_llm(
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=temperature,
            json_mode=json_mode
        )

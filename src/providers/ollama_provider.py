import logging
from langchain_ollama import ChatOllama
from src.providers.base import BaseProvider
from src.config import Config

logger = logging.getLogger(__name__)

class OllamaProvider(BaseProvider):
    """Integrates local offline models running under Ollama."""
    
    def get_llm(self, 
                api_key: str = None, 
                base_url: str = None, 
                model: str = None, 
                temperature: float = 0.15, 
                json_mode: bool = False) -> ChatOllama:
        
        # Resolve configurations
        url = base_url or Config.get_ollama_base_url() or "http://localhost:11434"
        model_name = model or Config.get_ollama_model() or "qwen3:8b"
        
        kwargs = {
            "model": model_name,
            "base_url": url,
            "temperature": temperature
        }
        
        if json_mode:
            # Enforce JSON formatting for Ollama models
            kwargs["format"] = "json"
            
        logger.info(f"Instantiating Ollama model: {model_name} on {url} (JSON Mode: {json_mode})")
        return ChatOllama(**kwargs)

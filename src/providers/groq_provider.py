import logging
from langchain_groq import ChatGroq
from src.providers.base import BaseProvider
from src.config import Config

logger = logging.getLogger(__name__)

class GroqProvider(BaseProvider):
    """Integrates Groq models using langchain-groq."""
    
    def get_llm(self, 
                api_key: str = None, 
                base_url: str = None, 
                model: str = None, 
                temperature: float = 0.15, 
                json_mode: bool = False) -> ChatGroq:
        
        # Resolve configurations
        key = api_key or Config.get_groq_api_key()
        model_name = model or "llama-3.1-8b-instant"
        
        if not key:
            raise ValueError("GROQ_API_KEY is not configured or is empty.")
            
        kwargs = {
            "model_name": model_name,
            "groq_api_key": key,
            "temperature": temperature,
            "max_retries": 3
        }
        
        if json_mode:
            # Enforce JSON mode for Groq via model_kwargs (avoids LangChain warning)
            kwargs["model_kwargs"] = {"response_format": {"type": "json_object"}}
            
        logger.info(f"Instantiating Groq model: {model_name} (JSON Mode: {json_mode})")
        return ChatGroq(**kwargs)

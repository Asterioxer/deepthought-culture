import logging
from langchain_openai import ChatOpenAI
from src.providers.base import BaseProvider
from src.config import Config

logger = logging.getLogger(__name__)

class OpenRouterProvider(BaseProvider):
    """Integrates OpenRouter models using langchain-openai."""
    
    def get_llm(self, 
                api_key: str = None, 
                base_url: str = None, 
                model: str = None, 
                temperature: float = 0.15, 
                json_mode: bool = False) -> ChatOpenAI:
        
        # Resolve configurations
        key = api_key or Config.get_openrouter_api_key()
        model_name = model or Config.get_openrouter_model() or "google/gemini-2.5-flash:free"
        endpoint = base_url or "https://openrouter.ai/api/v1"
        
        if not key:
            raise ValueError("OPENROUTER_API_KEY is not configured or is empty.")
            
        kwargs = {
            "model_name": model_name,
            "openai_api_key": key,
            "openai_api_base": endpoint,
            "temperature": temperature,
            "max_retries": 3,
            "default_headers": {
                "HTTP-Referer": "https://github.com/Asterioxer/deepthought-culture",
                "X-Title": "Federer Company Discovery Engine"
            }
        }
        
        if json_mode:
            # Enforce JSON mode via model_kwargs
            kwargs["model_kwargs"] = {"response_format": {"type": "json_object"}}
            
        logger.info(f"Instantiating OpenRouter model: {model_name} (JSON Mode: {json_mode})")
        return ChatOpenAI(**kwargs)

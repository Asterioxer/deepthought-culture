import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from src.providers.base import BaseProvider
from src.config import Config

logger = logging.getLogger(__name__)

class GeminiProvider(BaseProvider):
    """Integrates Gemini models using langchain-google-genai."""
    
    def get_llm(self, 
                api_key: str = None, 
                base_url: str = None, 
                model: str = None, 
                temperature: float = 0.15, 
                json_mode: bool = False) -> ChatGoogleGenerativeAI:
        
        # Resolve configurations
        key = api_key or Config.get_google_api_key()
        model_name = model or "gemini-2.0-flash"
        
        if not key:
            raise ValueError("GOOGLE_API_KEY is not configured or is empty.")
            
        kwargs = {
            "model": model_name,
            "google_api_key": key,
            "temperature": temperature,
            "max_retries": 3
        }
        
        if json_mode:
            # Pass response_mime_type directly to avoid LangChain UserWarning
            kwargs["response_mime_type"] = "application/json"
            
        logger.info(f"Instantiating Gemini model: {model_name} (JSON Mode: {json_mode})")
        return ChatGoogleGenerativeAI(**kwargs)

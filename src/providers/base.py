from abc import ABC, abstractmethod
from langchain_core.language_models.chat_models import BaseChatModel

class BaseProvider(ABC):
    """Abstract base class for all LLM providers."""
    
    @abstractmethod
    def get_llm(self, 
                api_key: str = None, 
                base_url: str = None, 
                model: str = None, 
                temperature: float = 0.15, 
                json_mode: bool = False) -> BaseChatModel:
        """Instantiates and returns the configured LangChain chat model."""
        pass

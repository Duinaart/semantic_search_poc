"""
LLM Configuration Module

Provides a unified interface for different LLM providers using LangChain.
Supports easy switching between OpenAI, Anthropic, Google, and other providers.
"""

import os
from typing import Optional, Dict, Any
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

class LLMConfig:
    """Configuration class for LLM providers."""
    
    # Default models for each provider
    DEFAULT_MODELS = {
        "openai": "gpt-4o-mini",
        "anthropic": "claude-3-haiku-20240307",
        "google": "gemini-2.5-flash-lite",
    }
    
    # Environment variable mappings
    API_KEY_MAPPING = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY", 
        "google": "GOOGLE_API_KEY",
    }
    
    @classmethod
    def get_llm(
        cls, 
        provider: str = None, 
        model: str = None, 
        temperature: float = 0,
        **kwargs
    ) -> BaseChatModel:
        """
        Get a configured LLM instance.
        
        Args:
            provider: LLM provider ('openai', 'anthropic', 'google')
            model: Specific model name (uses default if not specified)
            temperature: Model temperature (0-1)
            **kwargs: Additional provider-specific arguments
            
        Returns:
            Configured LangChain chat model instance
        """
        # Default to OpenAI if not specified
        if provider is None:
            provider = os.getenv("LLM_PROVIDER", "openai").lower()
            
        # Use default model if not specified
        if model is None:
            model = os.getenv(f"{provider.upper()}_MODEL", cls.DEFAULT_MODELS.get(provider))
            
        # Get API key
        api_key = os.getenv(cls.API_KEY_MAPPING.get(provider))
        if not api_key:
            raise ValueError(f"API key not found for provider '{provider}'. Set {cls.API_KEY_MAPPING.get(provider)} environment variable.")
        
        # Create the appropriate LLM instance
        if provider == "openai":
            return ChatOpenAI(
                model=model,
                temperature=temperature,
                api_key=api_key,
                **kwargs
            )
        elif provider == "anthropic":
            return ChatAnthropic(
                model=model,
                temperature=temperature,
                api_key=api_key,
                **kwargs
            )
        elif provider == "google":
            return ChatGoogleGenerativeAI(
                model=model,
                temperature=temperature,
                google_api_key=api_key,
                **kwargs
            )
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    @classmethod
    def get_available_providers(cls) -> Dict[str, str]:
        """Get list of available providers and their status."""
        providers = {}
        for provider, env_var in cls.API_KEY_MAPPING.items():
            api_key = os.getenv(env_var)
            providers[provider] = "available" if api_key else "missing_api_key"
        return providers
    
    @classmethod
    def get_provider_models(cls, provider: str) -> Dict[str, Any]:
        """Get available models for a provider."""
        models = {
            "openai": {
                "gpt-4o": "Most capable model",
                "gpt-4o-mini": "Fast and efficient",
                "gpt-4-turbo": "Latest GPT-4 Turbo",
                "gpt-3.5-turbo": "Fast and cost-effective"
            },
            "anthropic": {
                "claude-3-opus-20240229": "Most capable Claude model",
                "claude-3-sonnet-20240229": "Balanced performance and speed",
                "claude-3-haiku-20240307": "Fast and efficient"
            },
            "google": {
                "gemini-2.5-flash-lite": "Ultra-fast, efficient model with excellent performance",
                "gemini-2.5-flash": "High-performance flash model with multimodal capabilities", 
                "gemini-2.5-pro": "Most capable Gemini model with advanced reasoning",
                "gemini-2.0-flash": "Fast multimodal model with tool calling support",
                "gemini-pro": "Legacy Google model (consider upgrading)",
                "gemini-pro-vision": "Legacy multimodal model (consider upgrading)"
            }
        }
        return models.get(provider, {})


def create_llm(provider: str = None, model: str = None, **kwargs) -> BaseChatModel:
    """
    Convenience function to create an LLM instance.
    
    Args:
        provider: LLM provider name
        model: Model name
        **kwargs: Additional arguments
        
    Returns:
        Configured LangChain chat model
    """
    return LLMConfig.get_llm(provider=provider, model=model, **kwargs)


# Example usage and testing
if __name__ == "__main__":
    # Show available providers
    print("Available providers:")
    providers = LLMConfig.get_available_providers()
    for provider, status in providers.items():
        print(f"  {provider}: {status}")
    
    print("\nTesting LLM creation...")
    try:
        # Try to create default LLM
        llm = create_llm()
        print(f"✅ Successfully created LLM: {llm.__class__.__name__}")
        
        # Test a simple completion
        from langchain_core.messages import HumanMessage
        response = llm.invoke([HumanMessage(content="Hello! Please respond with just 'Hi there!'")])
        print(f"✅ Test response: {response.content}")
        
    except Exception as e:
        print(f"❌ Error creating LLM: {e}")
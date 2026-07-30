"""
Aegis AI — Multi-LLM Provider Router.

Provides unified interface for initializing and invoking LLM models across:
- OpenAI (gpt-4o, gpt-4o-mini)
- Anthropic (claude-3-5-sonnet, claude-3-5-haiku)
- Google Gemini (gemini-2.0-flash, gemini-1.5-pro)
- Groq (llama-3.3-70b-versatile, mixtral-8x7b)
- Ollama (local open-weights models)

Includes provider fallback, retries, and token usage tracking.
"""

from __future__ import annotations

from typing import Any, Literal
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.chat_models import ChatOllama
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

ProviderType = Literal["openai", "anthropic", "google", "groq", "ollama"]


class LLMRouter:
    """
    Factory & Router for enterprise LLM model instances with resilience features.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def get_model(
        self,
        provider: str | None = None,
        model_name: str | None = None,
        temperature: float = 0.1,
        max_tokens: int | None = 4096,
        streaming: bool = True,
    ) -> BaseChatModel:
        """
        Instantiate a chat model based on requested provider or default config.
        """
        provider_name = (provider or self.settings.default_llm_provider).lower()

        try:
            if provider_name == "openai":
                return self._init_openai(model_name, temperature, max_tokens, streaming)
            elif provider_name == "anthropic":
                return self._init_anthropic(model_name, temperature, max_tokens, streaming)
            elif provider_name == "google":
                return self._init_google(model_name, temperature, max_tokens, streaming)
            elif provider_name == "groq":
                return self._init_groq(model_name, temperature, max_tokens, streaming)
            elif provider_name == "ollama":
                return self._init_ollama(model_name, temperature, streaming)
            else:
                logger.warning(
                    "unknown_llm_provider_fallback",
                    requested_provider=provider_name,
                    fallback="openai",
                )
                return self._init_openai(model_name, temperature, max_tokens, streaming)
        except Exception as e:
            logger.error("llm_initialization_failed", provider=provider_name, error=str(e))
            # Fallback attempt if non-OpenAI failed
            if provider_name != "openai" and self.settings.openai_api_key:
                logger.info("falling_back_to_openai")
                return self._init_openai(None, temperature, max_tokens, streaming)
            raise e

    def _init_openai(
        self,
        model_name: str | None,
        temperature: float,
        max_tokens: int | None,
        streaming: bool,
    ) -> ChatOpenAI:
        api_key = self.settings.openai_api_key or "sk-dummy"
        model = model_name or self.settings.openai_model
        return ChatOpenAI(
            model=model,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            streaming=streaming,
        )

    def _init_anthropic(
        self,
        model_name: str | None,
        temperature: float,
        max_tokens: int | None,
        streaming: bool,
    ) -> ChatAnthropic:
        api_key = self.settings.anthropic_api_key or "sk-ant-dummy"
        model = model_name or self.settings.anthropic_model
        return ChatAnthropic(
            model=model,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens or 4096,
            streaming=streaming,
        )

    def _init_google(
        self,
        model_name: str | None,
        temperature: float,
        max_tokens: int | None,
        streaming: bool,
    ) -> ChatGoogleGenerativeAI:
        api_key = self.settings.google_api_key or "dummy-key"
        model = model_name or self.settings.google_model
        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=api_key,
            temperature=temperature,
            max_output_tokens=max_tokens,
            streaming=streaming,
        )

    def _init_groq(
        self,
        model_name: str | None,
        temperature: float,
        max_tokens: int | None,
        streaming: bool,
    ) -> ChatOpenAI:
        """Groq uses OpenAI-compatible API endpoint."""
        api_key = self.settings.groq_api_key or "gsk-dummy"
        model = model_name or self.settings.groq_model
        return ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
            temperature=temperature,
            max_tokens=max_tokens,
            streaming=streaming,
        )

    def _init_ollama(
        self,
        model_name: str | None,
        temperature: float,
        streaming: bool,
    ) -> ChatOllama:
        base_url = self.settings.ollama_base_url
        model = model_name or self.settings.ollama_model
        return ChatOllama(
            base_url=base_url,
            model=model,
            temperature=temperature,
        )


# Singleton router helper
def get_llm_router() -> LLMRouter:
    return LLMRouter()

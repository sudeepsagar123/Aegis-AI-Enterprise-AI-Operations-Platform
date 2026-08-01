"""
Unit tests for the Multi-LLM Provider Router.
"""

from __future__ import annotations

import pytest
from app.core.llm import LLMRouter, get_llm_router
from app.core.config import get_settings


def test_llm_router_singleton():
    router = get_llm_router()
    assert isinstance(router, LLMRouter)


def test_get_openai_model():
    router = LLMRouter()
    model = router.get_model(provider="openai", model_name="gpt-4o-mini", temperature=0.2)
    assert model is not None
    assert getattr(model, "model_name", getattr(model, "model", "")) == "gpt-4o-mini"


def test_get_groq_model():
    router = LLMRouter()
    model = router.get_model(provider="groq", model_name="llama-3.3-70b-versatile")
    assert model is not None


def test_unknown_provider_fallback():
    router = LLMRouter()
    model = router.get_model(provider="unknown_llm_provider")
    assert model is not None

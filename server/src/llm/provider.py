"""
LLM Provider Manager
--------------------
Central abstraction supporting multiple LLM inference providers:
  - Mistral AI (ministral-8b-latest, mistral-small-latest, open-mistral-7b)
  - Free.ai (https://free.ai/api/) (qwen7b, qwen3-8b, mistral, deepseek-r1)

Handles dynamic switching from client UI, model selection,
and uniform streaming generators.
"""

from __future__ import annotations

import os
from typing import Generator
from dotenv import load_dotenv

from . import mistral_model
from . import freeai_model

load_dotenv()

# Available provider definitions
AVAILABLE_PROVIDERS = [
    {
        "id": "mistral",
        "name": "Mistral AI",
        "description": "Official Mistral AI API with conversational reasoning.",
        "default_model": "ministral-8b-latest",
        "models": [
            {"id": "ministral-8b-latest", "name": "Ministral 8B (Default)"},
            {"id": "mistral-small-latest", "name": "Mistral Small"},
            {"id": "open-mistral-7b", "name": "Open Mistral 7B"},
        ],
    },
    {
        "id": "freeai",
        "name": "Free.ai",
        "description": "Unified OpenAI-compatible API (https://free.ai/api/).",
        "default_model": "qwen7b",
        "models": [
            {"id": "qwen7b", "name": "Qwen 2.5 7B (Fast / Free)"},
            {"id": "qwen3-8b", "name": "Qwen 3 8B"},
            {"id": "mistral", "name": "Mistral 7B"},
            {"id": "deepseek-r1", "name": "DeepSeek R1 Distill"},
        ],
    },
]

# Initial provider detection
_default_provider = "mistral"
if (os.getenv("FREEAI_APIKEY") or os.getenv("FREEAI_API_KEY")) and not os.getenv("MISTRAL_API_KEY"):
    _default_provider = "freeai"

_active_provider: str = os.getenv("DEFAULT_LLM_PROVIDER", _default_provider)
_active_model: str = (
    "qwen7b" if _active_provider == "freeai" else "ministral-8b-latest"
)


def get_provider_info() -> dict:
    """Returns active provider status and all available providers for client synchronization."""
    return {
        "active_provider": _active_provider,
        "active_model": _active_model,
        "providers": AVAILABLE_PROVIDERS,
    }


def set_active_provider(provider_id: str, model_id: str | None = None) -> dict:
    """Updates the active LLM provider and model."""
    global _active_provider, _active_model

    matched = next((p for p in AVAILABLE_PROVIDERS if p["id"] == provider_id), None)
    if not matched:
        print(f"[LLM Provider] Unknown provider '{provider_id}', keeping '{_active_provider}'.")
        return get_provider_info()

    _active_provider = provider_id

    if model_id and any(m["id"] == model_id for m in matched["models"]):
        _active_model = model_id
    else:
        _active_model = matched["default_model"]

    print(
        f"[LLM Provider] Switched active provider to {_active_provider} (model: {_active_model})"
    )
    return get_provider_info()


def stream_chat(prompt: str, history: list) -> Generator[str, None, None]:
    """Routes stream_chat to the currently selected LLM provider and model."""
    if _active_provider == "freeai":
        yield from freeai_model.stream_chat(prompt, history, model=_active_model)
    else:
        yield from mistral_model.stream_chat(prompt, history, model_name=_active_model)


def classify_emotion(text: str) -> str:
    """Routes classify_emotion to the currently selected LLM provider."""
    if _active_provider == "freeai":
        return freeai_model.classify_emotion(text, model=_active_model)
    return mistral_model.classify_emotion(text)

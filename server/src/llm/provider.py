"""
LLM Provider Manager
--------------------
Central abstraction supporting multiple LLM inference providers:
  - Mistral AI (ministral-8b-latest, mistral-small-latest, open-mistral-7b)
  - Free.ai (https://free.ai/api/) (qwen7b, qwen3-8b, mistral, deepseek-r1)
  - OpenRouter (https://openrouter.ai/) (openrouter/free, ling-3.0-flash, liquid-lfm, space-bunny, etc.)

Handles dynamic switching from client UI, model selection,
and uniform streaming generators.
"""

from __future__ import annotations

import os
from typing import Generator
from dotenv import load_dotenv

from . import mistral_model
from . import freeai_model
from . import openrouter_model
from .vision import analyze_image

load_dotenv()

# Available provider definitions with explicit tool-calling and vision capability flags
AVAILABLE_PROVIDERS = [
    {
        "id": "mistral",
        "name": "Mistral AI",
        "description": "Official Mistral AI API with conversational reasoning and multimodal vision.",
        "default_model": "ministral-8b-latest",
        "tool_calling_supported": True,
        "vision_supported": True,
        "models": [
            {
                "id": "ministral-8b-latest",
                "name": "Ministral 8B (Default)",
                "tool_calling_supported": True,
                "vision_supported": False,
            },
            {
                "id": "pixtral-12b-2409",
                "name": "Pixtral 12B (Vision Native)",
                "tool_calling_supported": False,
                "vision_supported": True,
            },
            {
                "id": "mistral-small-latest",
                "name": "Mistral Small",
                "tool_calling_supported": True,
                "vision_supported": False,
            },
            {
                "id": "open-mistral-7b",
                "name": "Open Mistral 7B",
                "tool_calling_supported": True,
                "vision_supported": False,
            },
        ],
    },
    {
        "id": "freeai",
        "name": "Free.ai",
        "description": "Unified OpenAI-compatible API (https://free.ai/api/).",
        "default_model": "qwen7b",
        "tool_calling_supported": True,
        "vision_supported": False,
        "models": [
            {
                "id": "qwen7b",
                "name": "Qwen 2.5 7B (Fast / Free)",
                "tool_calling_supported": True,
                "vision_supported": False,
            },
            {
                "id": "qwen3-8b",
                "name": "Qwen 3 8B",
                "tool_calling_supported": True,
                "vision_supported": False,
            },
        ],
    },
    {
        "id": "openrouter",
        "name": "OpenRouter (Free)",
        "description": "OpenRouter free models with verified tool calling and vision support.",
        "default_model": "openrouter/free",
        "tool_calling_supported": True,
        "vision_supported": True,
        "models": [
            {
                "id": "openrouter/free",
                "name": "Free Models Router (Auto / Modality-Aware)",
                "tool_calling_supported": True,
                "vision_supported": True,
            },
            {
                "id": "inclusionai/ling-3.0-flash-sante:free",
                "name": "Ling 3.0 Flash Sante",
                "tool_calling_supported": True,
                "vision_supported": False,
            },
            {
                "id": "liquid/lfm-2.5-2.6b:free",
                "name": "Liquid LFM 2.5 2.6B",
                "tool_calling_supported": True,
                "vision_supported": False,
            },
            {
                "id": "stealth/space-bunny-alpha",
                "name": "Space Bunny Alpha (1M Context)",
                "tool_calling_supported": True,
                "vision_supported": False,
            },
            {
                "id": "poolside/laguna-s-2.1:free",
                "name": "Laguna S 2.1",
                "tool_calling_supported": True,
                "vision_supported": False,
            },
            {
                "id": "qwen/qwen3.8-27b:free",
                "name": "Qwen 3.8 27B",
                "tool_calling_supported": True,
                "vision_supported": False,
            },
        ],
    },
]

# Initial provider detection
_default_provider = "mistral"
if (os.getenv("FREEAI_APIKEY") or os.getenv("FREEAI_API_KEY")) and not os.getenv("MISTRAL_API_KEY"):
    _default_provider = "freeai"
if (os.getenv("OPENROUTER_APIKEY") or os.getenv("OPENROUTER_API_KEY")) and not os.getenv("MISTRAL_API_KEY"):
    _default_provider = "openrouter"

_active_provider: str = os.getenv("DEFAULT_LLM_PROVIDER", _default_provider)

def _get_default_model_for_provider(provider: str) -> str:
    """Returns the default model for a given provider ID."""
    matched = next((p for p in AVAILABLE_PROVIDERS if p["id"] == provider), None)
    return matched["default_model"] if matched else "ministral-8b-latest"

_active_model: str = _get_default_model_for_provider(_active_provider)


def is_tool_calling_supported(
    provider_id: str | None = None, model_id: str | None = None
) -> bool:
    """Evaluates whether the specified (or currently active) provider & model supports tool calling."""
    target_provider = provider_id or _active_provider
    target_model = model_id or _active_model

    p_info = next((p for p in AVAILABLE_PROVIDERS if p["id"] == target_provider), None)
    if not p_info:
        return False

    m_info = next((m for m in p_info["models"] if m["id"] == target_model), None)
    if not m_info:
        return target_provider in ("mistral", "openrouter")

    return bool(m_info.get("tool_calling_supported", False))


def is_vision_supported(
    provider_id: str | None = None, model_id: str | None = None
) -> bool:
    """Evaluates whether the specified (or currently active) provider & model natively supports image vision."""
    target_provider = provider_id or _active_provider
    target_model = model_id or _active_model

    p_info = next((p for p in AVAILABLE_PROVIDERS if p["id"] == target_provider), None)
    if not p_info:
        return False

    m_info = next((m for m in p_info["models"] if m["id"] == target_model), None)
    if not m_info:
        return target_model == "openrouter/free" or "pixtral" in (target_model or "").lower()

    return bool(m_info.get("vision_supported", False))


def get_provider_info() -> dict:
    """Returns active provider status and all available providers for client synchronization."""
    return {
        "active_provider": _active_provider,
        "active_model": _active_model,
        "active_tool_calling_supported": is_tool_calling_supported(
            _active_provider, _active_model
        ),
        "active_vision_supported": is_vision_supported(
            _active_provider, _active_model
        ),
        "providers": AVAILABLE_PROVIDERS,
    }


def set_active_provider(provider_id: str, model_id: str | None = None) -> dict:
    """Updates the active LLM provider and model."""
    global _active_provider, _active_model

    if provider_id in ("freeai", "mistral", "openrouter"):
        _active_provider = provider_id
    else:
        print(f"[LLM Provider] Unknown provider '{provider_id}', keeping '{_active_provider}'.")

    matched = next((p for p in AVAILABLE_PROVIDERS if p["id"] == _active_provider), None)

    # Strictly preserve the user's explicit model_id without silently falling back!
    if model_id and model_id.strip():
        _active_model = model_id.strip()
    elif matched:
        _active_model = matched["default_model"]
    else:
        _active_model = "ministral-8b-latest"

    print(
        f"[LLM Provider] Active provider: {_active_provider} | Active model: '{_active_model}'"
    )
    return get_provider_info()


import threading
from typing import Callable


def stream_chat(
    prompt: str,
    history: list,
    image: str | None = None,
    tools_enabled: bool = False,
    max_tool_rounds: int = 5,
    on_tool_activity: Callable[[str, str], None] | None = None,
    cancel_event: threading.Event | None = None,
) -> Generator[str, None, None]:
    """Routes stream_chat to the currently selected LLM provider and model with optional tool calling and vision."""
    effective_tools_enabled = tools_enabled and is_tool_calling_supported(
        _active_provider, _active_model
    )
    native_vision = is_vision_supported(_active_provider, _active_model)

    effective_prompt = prompt
    pass_image = image

    if image:
        if not native_vision:
            print(
                f"[LLM Provider] Active model '{_active_model}' is text-only. "
                f"Extracting visual features via background vision analyzer..."
            )
            visual_analysis = analyze_image(image)
            if prompt and prompt.strip():
                effective_prompt = f"[Image description:\n{visual_analysis}]\n\n{prompt}"
            else:
                effective_prompt = f"[Image description:\n{visual_analysis}]"
            pass_image = None
        else:
            print(
                f"[LLM Provider] Model '{_active_model}' natively supports vision. Passing image directly."
            )

    print(
        f"[LLM Provider] Routing stream_chat to provider='{_active_provider}', model='{_active_model}' "
        f"(requested_tools={tools_enabled}, effective_tools={effective_tools_enabled}, has_image={bool(image)}, native_vision={native_vision})"
    )

    if _active_provider == "freeai":
        yield from freeai_model.stream_chat(
            effective_prompt,
            history,
            model=_active_model,
            tools_enabled=effective_tools_enabled,
            max_tool_rounds=max_tool_rounds,
            on_tool_activity=on_tool_activity,
            cancel_event=cancel_event,
        )
    elif _active_provider == "openrouter":
        yield from openrouter_model.stream_chat(
            effective_prompt,
            history,
            model=_active_model,
            image=pass_image,
            tools_enabled=effective_tools_enabled,
            max_tool_rounds=max_tool_rounds,
            on_tool_activity=on_tool_activity,
            cancel_event=cancel_event,
        )
    else:
        yield from mistral_model.stream_chat(
            effective_prompt,
            history,
            model_name=_active_model,
            image=pass_image,
            tools_enabled=effective_tools_enabled,
            on_tool_activity=on_tool_activity,
            cancel_event=cancel_event,
        )


def classify_emotion(text: str) -> str:
    """Routes classify_emotion to the currently selected LLM provider."""
    if _active_provider == "freeai":
        return freeai_model.classify_emotion(text, model=_active_model)
    elif _active_provider == "openrouter":
        return openrouter_model.classify_emotion(text, model=_active_model)
    return mistral_model.classify_emotion(text)

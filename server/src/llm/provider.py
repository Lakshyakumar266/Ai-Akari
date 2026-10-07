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
from . import openai_model
from . import freeai_model
from . import openrouter_model
from . import bedrock_model
from .vision import analyze_image

load_dotenv()

# Available provider definitions with explicit tool-calling and vision capability flags
AVAILABLE_PROVIDERS = [
    {
        "id": "openai",
        "name": "OpenAI",
        "description": "Direct OpenAI API with GPT-4o, GPT-4o Mini, full tool calling and multimodal vision.",
        "default_model": "gpt-4o-mini",
        "tool_calling_supported": True,
        "vision_supported": True,
        "models": [
            {
                "id": "gpt-4o-mini",
                "name": "GPT-4o Mini (Recommended)",
                "tool_calling_supported": True,
                "vision_supported": True,
            },
            {
                "id": "gpt-4o",
                "name": "GPT-4o (Flagship)",
                "tool_calling_supported": True,
                "vision_supported": True,
            },
            {
                "id": "gpt-4-turbo",
                "name": "GPT-4 Turbo",
                "tool_calling_supported": True,
                "vision_supported": True,
            },
            {
                "id": "gpt-3.5-turbo",
                "name": "GPT-3.5 Turbo",
                "tool_calling_supported": True,
                "vision_supported": True,
            },
        ],
    },
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
            {
                "id": "google/gemma-4-31b-it:free",
                "name": "Google Gemma 4 31B (Free)",
                "tool_calling_supported": True,
                "vision_supported": True,
            },
            {
                "id": "google/gemma-4-26b-a4b-it:free",
                "name": "Google Gemma 4 26B A4B (Free)",
                "tool_calling_supported": True,
                "vision_supported": True,
            },
        ],
    },
    {
        "id": "bedrock",
        "name": "AWS Bedrock",
        "description": "Amazon Bedrock foundation models powered by AWS Bearer Token (Ministral, Gemma, Qwen, DeepSeek, Claude).",
        "default_model": "mistral.ministral-3-8b-instruct",
        "tool_calling_supported": True,
        "vision_supported": True,
        "models": [
            {
                "id": "mistral.ministral-3-8b-instruct",
                "name": "Ministral 3 8B (Recommended)",
                "tool_calling_supported": True,
                "vision_supported": True,
            },
            {
                "id": "mistral.ministral-3-14b-instruct",
                "name": "Ministral 3 14B",
                "tool_calling_supported": True,
                "vision_supported": True,
            },
            {
                "id": "mistral.mistral-large-3-675b-instruct",
                "name": "Mistral Large 3 675B",
                "tool_calling_supported": True,
                "vision_supported": True,
            },
            {
                "id": "qwen.qwen3-vl-235b-a22b-instruct",
                "name": "Qwen 3 VL 235B (Vision Flagship)",
                "tool_calling_supported": True,
                "vision_supported": True,
            },
            {
                "id": "qwen.qwen3-32b",
                "name": "Qwen 3 32B (High Reasoning)",
                "tool_calling_supported": True,
                "vision_supported": False,
            },
            {
                "id": "openai.gpt-oss-120b",
                "name": "OpenAI GPT-OSS 120B (Reasoning Flagship)",
                "tool_calling_supported": True,
                "vision_supported": False,
            },
            {
                "id": "openai.gpt-oss-20b",
                "name": "OpenAI GPT-OSS 20B (Fast Reasoning)",
                "tool_calling_supported": True,
                "vision_supported": False,
            },
            {
                "id": "google.gemma-3-4b-it",
                "name": "Google Gemma 3 4B (Fast)",
                "tool_calling_supported": False,
                "vision_supported": False,
            },
            {
                "id": "google.gemma-3-12b-it",
                "name": "Google Gemma 3 12B (Smart)",
                "tool_calling_supported": False,
                "vision_supported": False,
            },
            {
                "id": "google.gemma-3-27b-it",
                "name": "Google Gemma 3 27B",
                "tool_calling_supported": False,
                "vision_supported": False,
            },
            {
                "id": "deepseek.v3.1",
                "name": "DeepSeek V3.1",
                "tool_calling_supported": True,
                "vision_supported": False,
            },
            {
                "id": "deepseek.v3.2",
                "name": "DeepSeek V3.2",
                "tool_calling_supported": True,
                "vision_supported": False,
            },
            {
                "id": "zai.glm-5",
                "name": "Zhipu GLM 5 (Frontier)",
                "tool_calling_supported": True,
                "vision_supported": False,
            },
            {
                "id": "moonshotai.kimi-k2.5",
                "name": "Moonshot Kimi K2.5",
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
if (os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_APIKEY")) and not os.getenv("MISTRAL_API_KEY"):
    _default_provider = "openai"
if (os.getenv("AWS_BEARER_TOKEN_BEDROCK") or os.getenv("BEDROCK_API_KEY")) and not os.getenv("MISTRAL_API_KEY"):
    _default_provider = "bedrock"

_active_provider: str = os.getenv("DEFAULT_LLM_PROVIDER", _default_provider)

def _get_default_model_for_provider(provider: str) -> str:
    """Returns the default model for a given provider ID."""
    matched = next((p for p in AVAILABLE_PROVIDERS if p["id"] == provider), None)
    return matched["default_model"] if matched else "ministral-8b-latest"

_active_model: str = _get_default_model_for_provider(_active_provider)


def set_provider_api_key(provider_id: str, api_key: str):
    """Updates the runtime API key for a given provider."""
    cleaned = api_key.strip() if api_key else ""
    if provider_id == "openai":
        openai_model.set_api_key(cleaned)
    elif provider_id == "mistral":
        os.environ["MISTRAL_API_KEY"] = cleaned
    elif provider_id == "openrouter":
        os.environ["OPENROUTER_APIKEY"] = cleaned
    elif provider_id == "freeai":
        os.environ["FREEAI_APIKEY"] = cleaned
    elif provider_id == "bedrock":
        bedrock_model.set_api_key(cleaned)
    print(f"[LLM Provider] Updated runtime API key for '{provider_id}' (configured={bool(cleaned)})")


def has_provider_api_key(provider_id: str) -> bool:
    """Returns True if the provider has an API key configured (in environment or runtime)."""
    if provider_id == "openai":
        return openai_model.has_api_key()
    if provider_id == "mistral":
        return bool(os.getenv("MISTRAL_API_KEY"))
    if provider_id == "openrouter":
        return bool(os.getenv("OPENROUTER_APIKEY") or os.getenv("OPENROUTER_API_KEY"))
    if provider_id == "freeai":
        return bool(os.getenv("FREEAI_APIKEY") or os.getenv("FREEAI_API_KEY"))
    if provider_id == "bedrock":
        return bedrock_model.has_api_key()
    return False


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
        lower = (target_model or "").lower()
        if "gemma-4" in lower:
            return True
        if "gemma-3" in lower or "gemma-2" in lower:
            return False
        return target_provider in ("mistral", "openrouter", "openai", "bedrock")

    return bool(m_info.get("tool_calling_supported", False))


def is_vision_supported(
    provider_id: str | None = None, model_id: str | None = None
) -> bool:
    """Evaluates whether the specified (or currently active) provider & model natively supports image vision."""
    target_provider = provider_id or _active_provider
    target_model = model_id or _active_model

    # OpenAI supports multimodal vision directly across modern models
    if target_provider == "openai":
        return True

    # Bedrock models with native multimodal image vision support
    if target_provider == "bedrock":
        lower = (target_model or "").lower()
        if (
            "mistral" in lower
            or "vl" in lower
            or "vision" in lower
            or "pixtral" in lower
            or "gpt-6" in lower
            or "gpt-5.5" in lower
            or "luna" in lower
            or "gemma-4" in lower
        ):
            return True

    p_info = next((p for p in AVAILABLE_PROVIDERS if p["id"] == target_provider), None)
    if not p_info:
        return False

    m_info = next((m for m in p_info["models"] if m["id"] == target_model), None)
    if not m_info:
        return (
            target_model == "openrouter/free"
            or "pixtral" in (target_model or "").lower()
            or "gpt-4" in (target_model or "").lower()
            or "vision" in (target_model or "").lower()
            or "vl" in (target_model or "").lower()
            or "gemma-4" in (target_model or "").lower()
        )

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
        "api_keys_configured": {
            p["id"]: has_provider_api_key(p["id"]) for p in AVAILABLE_PROVIDERS
        },
        "providers": AVAILABLE_PROVIDERS,
    }


def set_active_provider(provider_id: str, model_id: str | None = None) -> dict:
    """Updates the active LLM provider and model."""
    global _active_provider, _active_model

    # Infer provider from model_id if provider_id is empty or omitted
    if not provider_id and model_id:
        lower = model_id.lower()
        if "/" in lower or lower.startswith("openrouter"):
            provider_id = "openrouter"
        elif (
            "gpt-oss" in lower
            or "gpt-6" in lower
            or "gpt-5.5" in lower
            or "luna" in lower
            or lower.startswith("openai.")
            or "ministral-3" in lower
            or "gemma-3" in lower
            or "gemma-4" in lower
            or lower.startswith("google.gemma")
            or "qwen3-32b" in lower
            or "claude-sonnet-5" in lower
            or "claude-opus-5" in lower
            or lower.startswith("bedrock")
        ):
            provider_id = "bedrock"
        elif (
            lower.startswith("gpt-")
            or lower.startswith("o1")
            or lower.startswith("o3")
            or "openai" in lower
        ):
            provider_id = "openai"
        elif lower == "qwen7b" or lower.startswith("freeai"):
            provider_id = "freeai"
        elif "mistral" in lower or "pixtral" in lower:
            provider_id = "mistral"

    if provider_id in ("freeai", "mistral", "openrouter", "openai", "bedrock"):
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
        # OpenAI models directly support image inputs without third-party or background vision extraction
        if _active_provider == "openai" or native_vision:
            print(
                f"[LLM Provider] Provider '{_active_provider}' model '{_active_model}' supports direct vision. "
                f"Directly passing image with message."
            )
            pass_image = image
        else:
            print(
                f"[LLM Provider] Active provider '{_active_provider}' model '{_active_model}' is text-only. "
                f"Extracting visual features via background vision analyzer..."
            )
            visual_analysis = analyze_image(image)
            if prompt and prompt.strip():
                effective_prompt = f"[Image description:\n{visual_analysis}]\n\n{prompt}"
            else:
                effective_prompt = f"[Image description:\n{visual_analysis}]"
            pass_image = None

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
    elif _active_provider == "openai":
        yield from openai_model.stream_chat(
            effective_prompt,
            history,
            model=_active_model,
            image=pass_image,
            tools_enabled=effective_tools_enabled,
            max_tool_rounds=max_tool_rounds,
            on_tool_activity=on_tool_activity,
            cancel_event=cancel_event,
        )
    elif _active_provider == "bedrock":
        yield from bedrock_model.stream_chat(
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
    elif _active_provider == "openai":
        return openai_model.classify_emotion(text, model=_active_model)
    elif _active_provider == "bedrock":
        return bedrock_model.classify_emotion(text, model=_active_model)
    return mistral_model.classify_emotion(text)


def classic_chat(
    prompt: str,
    history: list | None = None,
    model_id: str | None = None,
    image: str | None = None,
) -> str:
    """Routes one-shot classic_chat to the currently selected LLM provider."""
    active_m = model_id or _active_model
    hist = history or []
    if _active_provider == "freeai":
        return freeai_model.classic_chat(prompt, hist, model=active_m)
    elif _active_provider == "openrouter":
        return openrouter_model.classic_chat(prompt, hist, model=active_m, image=image)
    elif _active_provider == "openai":
        return openai_model.classic_chat(prompt, hist, model=active_m, image=image)
    elif _active_provider == "bedrock":
        return bedrock_model.classic_chat(prompt, hist, model=active_m, image=image)
    return mistral_model.classic_chat(prompt, hist, model_name=active_m, image=image)


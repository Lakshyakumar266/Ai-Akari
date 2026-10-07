"""
OpenAI LLM Provider
-------------------
Direct integration with official OpenAI API (https://api.openai.com/v1)
supporting GPT-4o, GPT-4o Mini, GPT-4 Turbo, and legacy models.
Includes full tool calling (function calling), native multimodal vision,
and dynamic API key configuration from client UI or environment.

API Key from environment: OPENAI_API_KEY (or dynamically configured via set_api_key)
"""

from __future__ import annotations

import os
import json
import asyncio
import threading
from typing import Generator, Callable
from dotenv import load_dotenv
from openai import OpenAI

from src.prompts.system_prompt_akari import SYSTEM_PROMPT_AKARI_ASSISTANT, get_system_prompt
from src.tools import tool_registry
from src.config import CHAT_TEMPERATURE, TOOL_TEMPERATURE, TOOL_EXECUTION_TIMEOUT

load_dotenv()

DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"
VALID_EMOTIONS = {"Happy", "Sad", "Angry", "Surprised", "Relaxed", "Neutral"}

# In-memory runtime API key override set via Settings UI
_runtime_api_key: str | None = None


def set_api_key(api_key: str):
    """Sets or clears the runtime OpenAI API key."""
    global _runtime_api_key
    cleaned = api_key.strip() if api_key else ""
    _runtime_api_key = cleaned if cleaned else None
    if cleaned:
        os.environ["OPENAI_API_KEY"] = cleaned
    print(f"[OpenAI] Runtime API key updated (configured={bool(_runtime_api_key)})")


def get_api_key() -> str:
    """Returns the effective OpenAI API key (runtime override or environment)."""
    return (
        _runtime_api_key
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("OPENAI_APIKEY")
        or ""
    )


def has_api_key() -> bool:
    """Checks whether an OpenAI API key is available."""
    return bool(get_api_key())


def get_client(api_key: str | None = None) -> OpenAI:
    """Creates an OpenAI client configured for official OpenAI endpoints."""
    key = api_key or get_api_key()
    base_url = os.getenv("OPENAI_BASE_URL") or DEFAULT_BASE_URL
    return OpenAI(
        base_url=base_url,
        api_key=key or "none",
        timeout=45.0,
    )


def _format_messages(
    prompt: str,
    history: list,
    image: str | None = None,
    tools_enabled: bool = False,
) -> list[dict]:
    """Converts mixed history items into standard OpenAI format with optional multimodal image support."""
    sys_prompt = get_system_prompt(tools_enabled=tools_enabled)
    messages = [{"role": "system", "content": sys_prompt}]

    for item in history:
        if isinstance(item, dict):
            role = item.get("role", "user")
            content = item.get("content", "")
        elif hasattr(item, "content"):
            class_name = item.__class__.__name__.lower()
            role = "assistant" if "assistant" in class_name else "user"
            content = item.content or ""
        else:
            continue

        # If history content is a multimodal list (e.g. from prior turn with image_url),
        # extract only the text so historical image payloads never poison text-only models
        if isinstance(content, list):
            text_parts = []
            for part in content:
                if isinstance(part, dict):
                    if part.get("type") == "text":
                        text_parts.append(part.get("text", ""))
                    elif part.get("type") == "image_url":
                        text_parts.append("[Attached Image]")
                elif hasattr(part, "text") and getattr(part, "text", None):
                    text_parts.append(getattr(part, "text"))
                elif isinstance(part, str):
                    text_parts.append(part)
            content = " ".join(filter(None, text_parts)).strip() or "[Attached Image]"
        elif not isinstance(content, str):
            content = str(content)

        messages.append({"role": role, "content": content})

    if image:
        user_content = []
        if prompt and prompt.strip():
            user_content.append({"type": "text", "text": prompt})
        else:
            user_content.append({"type": "text", "text": "What do you see in this image?"})
        user_content.append({"type": "image_url", "image_url": {"url": image}})
        messages.append({
            "role": "user",
            "content": user_content,
        })
    else:
        messages.append({"role": "user", "content": prompt})
    return messages


def classic_chat(
    prompt: str, history: list, model: str = DEFAULT_MODEL, image: str | None = None
) -> str:
    """Non-streaming chat completion using OpenAI API."""
    if not has_api_key():
        return "[OpenAI Notice: Please enter your OpenAI API key in Settings -> OpenAI to use GPT models.]"

    messages = _format_messages(prompt, history, image=image)
    chosen_model = model or DEFAULT_MODEL
    client = get_client()

    try:
        resp = client.chat.completions.create(
            model=chosen_model,
            messages=messages,
            temperature=CHAT_TEMPERATURE,
        )
        return resp.choices[0].message.content or ""
    except Exception as err:
        print(f"[OpenAI] Request error with model '{chosen_model}': {err}")
        return f"[OpenAI Error: Request failed: {err}]"


def stream_chat(
    prompt: str,
    history: list,
    model: str = DEFAULT_MODEL,
    image: str | None = None,
    tools_enabled: bool = False,
    max_tool_rounds: int = 5,
    on_tool_activity: Callable[[str, str], None] | None = None,
    cancel_event: threading.Event | None = None,
) -> Generator[str, None, None]:
    """
    Yields text deltas as OpenAI generates tokens.
    Supports tool calling, multi-round tool loops, and native vision.
    """
    if not has_api_key():
        yield "[OpenAI Notice: Please enter your OpenAI API key in Settings -> OpenAI to use GPT models.]"
        return

    chosen_model = model or DEFAULT_MODEL
    print(
        f"[OpenAI] stream_chat starting with model: '{chosen_model}' "
        f"(tools_enabled={tools_enabled}, has_image={bool(image)})"
    )

    client = get_client()
    messages = _format_messages(prompt, history, image=image, tools_enabled=tools_enabled)

    # Fast path: tools disabled
    if not tools_enabled:
        try:
            stream = client.chat.completions.create(
                model=chosen_model,
                messages=messages,
                temperature=CHAT_TEMPERATURE,
                stream=True,
            )
            for chunk in stream:
                if cancel_event is not None and cancel_event.is_set():
                    return
                if chunk.choices and chunk.choices[0].delta:
                    delta_content = chunk.choices[0].delta.content
                    if delta_content:
                        yield delta_content
        except Exception as err:
            print(f"[OpenAI] Stream error with model '{chosen_model}': {err}")
            yield f"[OpenAI Error: Model '{chosen_model}' failed: {err}]"
        return

    # Tool calling enabled path
    tools = tool_registry.get_tool_definitions(only_enabled=True)
    if not tools:
        try:
            stream = client.chat.completions.create(
                model=chosen_model,
                messages=messages,
                temperature=CHAT_TEMPERATURE,
                stream=True,
            )
            for chunk in stream:
                if cancel_event is not None and cancel_event.is_set():
                    return
                if chunk.choices and chunk.choices[0].delta:
                    delta_content = chunk.choices[0].delta.content
                    if delta_content:
                        yield delta_content
        except Exception as err:
            print(f"[OpenAI] Fallback stream error: {err}")
            yield f"[OpenAI Error: {err}]"
        return

    current_round = 0

    while current_round < max_tool_rounds:
        current_round += 1
        if cancel_event is not None and cancel_event.is_set():
            return

        try:
            stream = client.chat.completions.create(
                model=chosen_model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=TOOL_TEMPERATURE,
                stream=True,
            )
        except Exception as err:
            print(f"[OpenAI] Tool stream error with model '{chosen_model}': {err}")
            yield f"[OpenAI Error: Model '{chosen_model}' failed: {err}]"
            return

        tool_calls_dict: dict[int, dict] = {}
        round_content_chunks: list[str] = []

        try:
            for chunk in stream:
                if cancel_event is not None and cancel_event.is_set():
                    return

                if not chunk.choices:
                    continue

                choice = chunk.choices[0]
                if choice.delta.tool_calls:
                    for tc in choice.delta.tool_calls:
                        idx = tc.index if tc.index is not None else len(tool_calls_dict)
                        if idx not in tool_calls_dict:
                            tool_calls_dict[idx] = {
                                "id": tc.id or f"tc_{idx}",
                                "name": tc.function.name if tc.function else "",
                                "arguments": (
                                    tc.function.arguments or "" if tc.function else ""
                                ),
                            }
                        else:
                            if tc.id:
                                tool_calls_dict[idx]["id"] = tc.id
                            if tc.function and tc.function.name:
                                tool_calls_dict[idx]["name"] = tc.function.name
                            if tc.function and tc.function.arguments:
                                tool_calls_dict[idx]["arguments"] += tc.function.arguments

                if choice.delta.content:
                    round_content_chunks.append(choice.delta.content)
        except Exception as err:
            print(f"[OpenAI] Stream chunk iteration error with model '{chosen_model}': {err}")
            yield f"[OpenAI Error: Stream interrupted: {err}]"
            return

        # If no tool calls requested, yield generated conversational content
        if not tool_calls_dict:
            for c in round_content_chunks:
                yield c
            break

        # Append assistant tool call request message
        assistant_tool_calls = [
            {
                "id": t["id"],
                "type": "function",
                "function": {"name": t["name"], "arguments": t["arguments"]},
            }
            for t in tool_calls_dict.values()
        ]
        accumulated_text = "".join(round_content_chunks).strip()
        messages.append({
            "role": "assistant",
            "content": accumulated_text if accumulated_text else None,
            "tool_calls": assistant_tool_calls,
        })

        # Execute each requested tool and append response
        for t in tool_calls_dict.values():
            if cancel_event is not None and cancel_event.is_set():
                return

            t_name = t["name"]
            t_args = t["arguments"]
            t_id = t["id"]

            if on_tool_activity:
                try:
                    on_tool_activity(t_name, "start")
                except Exception:
                    pass

            print(f"[OpenAI Tool] Executing '{t_name}' (args: {t_args})")
            try:
                loop = asyncio.new_event_loop()
                result = loop.run_until_complete(
                    tool_registry.execute_tool(t_name, t_args, timeout=TOOL_EXECUTION_TIMEOUT)
                )
                loop.close()
            except Exception as e:
                result = {"status": "error", "error": str(e)}

            print(f"[OpenAI Tool] Executed '{t_name}' -> {result}")

            if on_tool_activity:
                try:
                    on_tool_activity(t_name, "end")
                except Exception:
                    pass

            messages.append({
                "role": "tool",
                "tool_call_id": t_id,
                "name": t_name,
                "content": json.dumps(result),
            })


def classify_emotion(text: str, model: str = DEFAULT_MODEL) -> str:
    """Classifies spoken response text into VRM emotion presets using OpenAI."""
    if not text or not text.strip() or not has_api_key():
        return "Neutral"

    try:
        client = get_client()
        prompt = (
            f"Analyze the character's speech and classify its primary emotion into EXACTLY ONE of these categories: "
            f"Happy, Sad, Angry, Surprised, Relaxed, Neutral.\n\n"
            f'Speech text: "{text}"\n\n'
            f"Respond ONLY with the single category word."
        )
        resp = client.chat.completions.create(
            model=model or DEFAULT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=10,
        )
        raw = (resp.choices[0].message.content or "").strip()
        for emotion_name in VALID_EMOTIONS:
            if emotion_name.lower() in raw.lower():
                return emotion_name
    except Exception as err:
        print(f"[OpenAI Emotion] Error classifying emotion: {err}")

    return "Neutral"

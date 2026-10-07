"""
OpenRouter LLM Provider
-----------------------
Integration for OpenRouter API (https://openrouter.ai/api/v1) supporting
free models with full tool calling (function calling) and streaming completions.

API Key from environment: OPENROUTER_APIKEY (or OPENROUTER_API_KEY)
"""

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
from .bedrock_model import extract_gemma4_tool_calls

load_dotenv()

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openrouter/free"
VALID_EMOTIONS = {"Happy", "Sad", "Angry", "Surprised", "Relaxed", "Neutral"}


def get_openrouter_credentials() -> tuple[str, str]:
    """Retrieves API key and base URL for OpenRouter."""
    key = os.getenv("OPENROUTER_APIKEY") or os.getenv("OPENROUTER_API_KEY") or ""
    base_url = os.getenv("OPENROUTER_BASE_URL") or DEFAULT_BASE_URL
    return key, base_url


def get_client() -> OpenAI:
    """Creates an OpenAI client configured for OpenRouter."""
    key, base_url = get_openrouter_credentials()
    if not key:
        print("[OpenRouter] Warning: OPENROUTER_APIKEY is not set in environment.")
    return OpenAI(
        base_url=base_url,
        api_key=key or "none",
        timeout=45.0,
        default_headers={
            "HTTP-Referer": "https://github.com/Lakshyakumar266/",
            "X-Title": "Akari Watanabe",
        },
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
            messages.append({
                "role": item.get("role", "user"),
                "content": item.get("content", ""),
            })
        elif hasattr(item, "content"):
            class_name = item.__class__.__name__.lower()
            role = "assistant" if "assistant" in class_name else "user"
            messages.append({"role": role, "content": item.content or ""})

    if image:
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image}},
            ],
        })
    else:
        messages.append({"role": "user", "content": prompt})
    return messages


def classic_chat(
    prompt: str, history: list, model: str = DEFAULT_MODEL, image: str | None = None
) -> str:
    """Non-streaming chat completion using OpenRouter API."""
    messages = _format_messages(prompt, history, image=image)
    chosen_model = model or DEFAULT_MODEL
    client = get_client()

    try:
        resp = client.chat.completions.create(
            model=chosen_model,
            messages=messages,
            temperature=CHAT_TEMPERATURE,
        )
        raw_text = resp.choices[0].message.content or ""
        _, clean_text = extract_gemma4_tool_calls(raw_text)
        return clean_text
    except Exception as err:
        print(f"[OpenRouter] Request error with model '{chosen_model}': {err}")
        return f"[OpenRouter Notice: Request failed: {err}]"


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
    """Yields text tokens as OpenRouter generates them in real-time, with multi-round tool calling support."""
    messages = _format_messages(prompt, history, image=image, tools_enabled=tools_enabled)
    chosen_model = model or DEFAULT_MODEL
    print(
        f"[OpenRouter] stream_chat starting with model: '{chosen_model}' (tools_enabled={tools_enabled}, has_image={bool(image)})"
    )

    client = get_client()

    if not tools_enabled:
        # Standard streaming without tool calling
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
            print(f"[OpenRouter] Stream error with model '{chosen_model}': {err}")
            yield f"[OpenRouter Error: Model '{chosen_model}' failed: {err}]"
        return

    # Tool calling enabled path
    tools = tool_registry.get_tool_definitions(only_enabled=True)
    if not tools:
        # Fallback to direct stream if no tools enabled
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
            print(f"[OpenRouter] Fallback stream error: {err}")
            yield f"[OpenRouter Error: {err}]"
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
            print(f"[OpenRouter] Tool stream error with model '{chosen_model}': {err}")
            yield f"[OpenRouter Error: Model '{chosen_model}' failed: {err}]"
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
            print(f"[OpenRouter] Stream chunk iteration error with model '{chosen_model}': {err}")
            yield f"[OpenRouter Error: Stream interrupted: {err}]"
            return

        # Check if Gemma 4 (or model) emitted native control tokens in content stream instead of delta.tool_calls
        if not tool_calls_dict and round_content_chunks:
            full_round_text = "".join(round_content_chunks)
            extracted_calls, cleaned_text = extract_gemma4_tool_calls(full_round_text)
            if extracted_calls:
                print(
                    f"[OpenRouter Gemma 4] Extracted {len(extracted_calls)} native tool calls from content stream."
                )
                for c_idx, ec in enumerate(extracted_calls):
                    tool_calls_dict[c_idx] = {
                        "id": ec["id"],
                        "name": ec["name"],
                        "arguments": ec["arguments"],
                    }
                round_content_chunks = [cleaned_text] if cleaned_text else []

        # If no tool calls were requested, this is the final conversational response
        if not tool_calls_dict:
            for c in round_content_chunks:
                yield c
            break

        # If a tool call was requested, isolate intermediate filler from TTS speech:
        # Append assistant message with tool_calls
        assistant_tool_calls = [
            {
                "id": t["id"],
                "type": "function",
                "function": {"name": t["name"], "arguments": t["arguments"]},
            }
            for t in tool_calls_dict.values()
        ]
        accumulated_text = "".join(round_content_chunks).strip()
        # Execute each tool call and collect results
        gemma4_tool_responses = []
        executed_tool_messages = []
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

            print(f"[OpenRouter Tool] Executing '{t_name}' (args: {t_args})")
            try:
                loop = asyncio.new_event_loop()
                result = loop.run_until_complete(
                    tool_registry.execute_tool(t_name, t_args, timeout=TOOL_EXECUTION_TIMEOUT)
                )
                loop.close()
            except Exception as e:
                result = {"status": "error", "error": str(e)}

            print(f"[OpenRouter Tool] Executed '{t_name}' -> {result}")

            if on_tool_activity:
                try:
                    on_tool_activity(t_name, "end")
                except Exception:
                    pass

            gemma4_tool_responses.append({
                "name": t_name,
                "response": result,
            })

            executed_tool_messages.append({
                "role": "tool",
                "tool_call_id": t_id,
                "name": t_name,
                "content": json.dumps(result) if isinstance(result, (dict, list)) else str(result),
            })

        assistant_msg = {
            "role": "assistant",
            "content": accumulated_text if accumulated_text else None,
            "tool_calls": assistant_tool_calls,
        }
        if "gemma" in chosen_model.lower():
            assistant_msg["tool_responses"] = gemma4_tool_responses

        messages.append(assistant_msg)
        messages.extend(executed_tool_messages)


def classify_emotion(text: str, model: str = DEFAULT_MODEL) -> str:
    """Classifies spoken response text into VRM emotion presets using OpenRouter LLM."""
    if not text or not text.strip():
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
        print(f"[OpenRouter Emotion] Error classifying emotion: {err}")

    return "Neutral"

"""
AWS Bedrock LLM Provider
-------------------------
Integration with Amazon Bedrock Mantle OpenAI-compatible API
(https://bedrock-mantle.{region}.api.aws/v1) using AWS_BEARER_TOKEN_BEDROCK.
Supports models such as Ministral 3 8B, Google Gemma 3, Qwen 3 32B, DeepSeek V3,
and Claude with full streaming and tool calling (function calling).

Authentication:
  - Environment variable: AWS_BEARER_TOKEN_BEDROCK (or BEDROCK_API_KEY)
  - Region: AWS_REGION or BEDROCK_REGION (default: ap-south-1)
"""

from __future__ import annotations

import os
import json
import asyncio
import threading
from typing import Generator, Callable
from dotenv import load_dotenv
from openai import OpenAI

from src.prompts.system_prompt_akari import SYSTEM_PROMPT_AKARI_ASSISTANT
from src.tools import tool_registry
from src.config import CHAT_TEMPERATURE, TOOL_TEMPERATURE, TOOL_EXECUTION_TIMEOUT

load_dotenv()

DEFAULT_REGION = "ap-south-1"
DEFAULT_MODEL = "mistral.ministral-3-8b-instruct"
VALID_EMOTIONS = {"Happy", "Sad", "Angry", "Surprised", "Relaxed", "Neutral"}

# In-memory runtime API key override set via Settings UI
_runtime_api_key: str | None = None
_runtime_region: str | None = None


def set_api_key(api_key: str):
    """Sets or clears the runtime AWS Bedrock Bearer Token."""
    global _runtime_api_key
    cleaned = api_key.strip() if api_key else ""
    _runtime_api_key = cleaned if cleaned else None
    if cleaned:
        os.environ["AWS_BEARER_TOKEN_BEDROCK"] = cleaned
    print(f"[Bedrock] Runtime Bearer Token updated (configured={bool(_runtime_api_key)})")


def set_region(region: str):
    """Sets or clears the runtime Bedrock region."""
    global _runtime_region
    cleaned = region.strip() if region else ""
    _runtime_region = cleaned if cleaned else None
    if cleaned:
        os.environ["BEDROCK_REGION"] = cleaned
    print(f"[Bedrock] Runtime Region updated: '{_runtime_region or DEFAULT_REGION}'")


def get_region() -> str:
    """Returns the effective AWS region for Bedrock Mantle."""
    if _runtime_region:
        return _runtime_region
    env_region = os.getenv("BEDROCK_REGION") or os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")
    if env_region and env_region.strip():
        return env_region.strip()

    # Try extracting region from bearer token if present
    token = get_api_key()
    if token and "bedrock-api-key-" in token:
        try:
            import base64
            b64_part = token.split("bedrock-api-key-", 1)[1]
            b64_part += "=" * (-len(b64_part) % 4)
            decoded = base64.b64decode(b64_part).decode("utf-8", errors="ignore")
            # Look for %2Fregion%2F or /region/
            for part in decoded.split("&"):
                if "Credential=" in part:
                    cred_val = part.split("Credential=", 1)[1]
                    # Format: ASIA.../YYYYMMDD/region/bedrock/aws4_request
                    pieces = cred_val.replace("%2F", "/").split("/")
                    if len(pieces) >= 3:
                        return pieces[2]
        except Exception:
            pass

    return DEFAULT_REGION


def get_base_url() -> str:
    """Returns the Bedrock Mantle OpenAI-compatible base URL."""
    region = get_region()
    return f"https://bedrock-mantle.{region}.api.aws/v1"


def get_api_key() -> str:
    """Returns the effective AWS Bedrock Bearer Token."""
    return (
        _runtime_api_key
        or os.getenv("AWS_BEARER_TOKEN_BEDROCK")
        or os.getenv("BEDROCK_API_KEY")
        or os.getenv("AWS_BEDROCK_API_KEY")
        or ""
    )


def has_api_key() -> bool:
    """Checks whether an AWS Bedrock Bearer Token is available."""
    return bool(get_api_key())


def get_client(api_key: str | None = None) -> OpenAI:
    """Creates an OpenAI client configured for Bedrock Mantle."""
    key = api_key or get_api_key()
    base_url = get_base_url()
    return OpenAI(
        base_url=base_url,
        api_key=key or "none",
        timeout=45.0,
    )


def _format_messages(prompt: str, history: list, image: str | None = None) -> list[dict]:
    """Converts mixed history items into standard message format."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT_AKARI_ASSISTANT}]

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
        # or bloat context limits
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


def _format_bedrock_error(chosen_model: str, err: Exception) -> str:
    """Formats Bedrock errors with helpful context about region and model availability."""
    err_str = str(err)
    reg = get_region()
    if "404" in err_str or "not_found" in err_str:
        return (
            f"[Bedrock Notice: Model '{chosen_model}' returned 404 Not Found on Amazon Bedrock Mantle. "
            f"AWS has this model in preview/catalog, but its runtime chat endpoint is not activated yet in region '{reg}'. "
            f"Please switch to 'mistral.ministral-3-8b-instruct', 'openai.gpt-oss-120b', or 'google.gemma-3-4b-it'.]"
        )
    if "401" in err_str or "access_denied" in err_str or "permission_denied" in err_str:
        return (
            f"[Bedrock Notice: Access to model '{chosen_model}' was denied by Amazon Bedrock for this account. "
            f"This model requires specialized entitlement or access agreement in region '{reg}'. "
            f"Please switch to 'mistral.ministral-3-8b-instruct', 'openai.gpt-oss-120b', or 'google.gemma-3-4b-it'.]"
        )
    return f"[Bedrock Error: Model '{chosen_model}' failed: {err}]"


def classic_chat(
    prompt: str, history: list, model: str = DEFAULT_MODEL, image: str | None = None
) -> str:
    """Non-streaming chat completion using AWS Bedrock Mantle API."""
    if not has_api_key():
        return "[AWS Bedrock Notice: Please configure AWS_BEARER_TOKEN_BEDROCK in Settings -> AWS Bedrock.]"

    messages = _format_messages(prompt, history, image=image)
    chosen_model = model or DEFAULT_MODEL
    client = get_client()

    kwargs = {
        "model": chosen_model,
        "messages": messages,
        "temperature": CHAT_TEMPERATURE,
    }
    if "gpt-oss" in chosen_model.lower():
        kwargs["max_tokens"] = 1000

    try:
        resp = client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content or ""
    except Exception as err:
        print(f"[Bedrock] Request error with model '{chosen_model}': {err}")
        return _format_bedrock_error(chosen_model, err)


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
    Yields text deltas as AWS Bedrock Mantle generates tokens.
    Supports streaming and multi-round tool loops.
    """
    if not has_api_key():
        yield "[AWS Bedrock Notice: Please configure AWS_BEARER_TOKEN_BEDROCK in Settings -> AWS Bedrock.]"
        return

    chosen_model = model or DEFAULT_MODEL
    print(
        f"[Bedrock] stream_chat starting with model: '{chosen_model}' "
        f"(region={get_region()}, tools_enabled={tools_enabled}, has_image={bool(image)})"
    )

    client = get_client()
    messages = _format_messages(prompt, history, image=image)

    # Extra parameters for reasoning models (e.g. OpenAI GPT-OSS on Bedrock)
    stream_kwargs = {}
    if "gpt-oss" in chosen_model.lower():
        stream_kwargs["max_tokens"] = 1000

    # Models like Google Gemma on Bedrock Mantle drop tokens when tools parameter is supplied with system prompts
    is_gemma = "gemma" in chosen_model.lower()
    effective_tools = tools_enabled and not is_gemma

    # Fast path: tools disabled or model unsupported for tools
    if not effective_tools:
        try:
            stream = client.chat.completions.create(
                model=chosen_model,
                messages=messages,
                temperature=CHAT_TEMPERATURE,
                stream=True,
                **stream_kwargs,
            )
            for chunk in stream:
                if cancel_event is not None and cancel_event.is_set():
                    return
                if chunk.choices and chunk.choices[0].delta:
                    delta_content = chunk.choices[0].delta.content
                    if delta_content:
                        yield delta_content
        except Exception as err:
            print(f"[Bedrock] Stream error with model '{chosen_model}': {err}")
            yield _format_bedrock_error(chosen_model, err)
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
                **stream_kwargs,
            )
            for chunk in stream:
                if cancel_event is not None and cancel_event.is_set():
                    return
                if chunk.choices and chunk.choices[0].delta:
                    delta_content = chunk.choices[0].delta.content
                    if delta_content:
                        yield delta_content
        except Exception as err:
            print(f"[Bedrock] Fallback stream error: {err}")
            yield _format_bedrock_error(chosen_model, err)
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
                **stream_kwargs,
            )
        except Exception as err:
            print(f"[Bedrock] Tool stream error with model '{chosen_model}': {err}")
            yield _format_bedrock_error(chosen_model, err)
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
                                tool_calls_dict[idx]["name"] += tc.function.name
                            if tc.function and tc.function.arguments:
                                tool_calls_dict[idx]["arguments"] += tc.function.arguments

                if choice.delta.content:
                    round_content_chunks.append(choice.delta.content)

        except Exception as err:
            print(f"[Bedrock] Stream iteration error with model '{chosen_model}': {err}")
            yield f"[Bedrock Error: Stream iteration failed: {err}]"
            return

        # Case 1: No tool calls requested -> final answer
        if not tool_calls_dict:
            for c in round_content_chunks:
                yield c
            return

        # Case 2: Tool calls requested
        executed_tool_calls_payload = []
        for idx in sorted(tool_calls_dict.keys()):
            tc_data = tool_calls_dict[idx]
            t_id = tc_data["id"]
            t_name = tc_data["name"]
            raw_args = tc_data["arguments"]

            try:
                t_args = json.loads(raw_args) if raw_args.strip() else {}
            except Exception:
                t_args = {}

            if on_tool_activity:
                on_tool_activity(t_name, "start")

            executed_tool_calls_payload.append({
                "id": t_id,
                "type": "function",
                "function": {
                    "name": t_name,
                    "arguments": raw_args,
                },
            })

            print(f"[Bedrock Tool] Executing '{t_name}' (args: {t_args})")
            try:
                coro = tool_registry.execute_tool(t_name, t_args)
                result = asyncio.run(
                    asyncio.wait_for(coro, timeout=TOOL_EXECUTION_TIMEOUT)
                )
            except Exception as e:
                print(f"[Bedrock Tool] Execution failed for '{t_name}': {e}")
                result = f"Error executing tool {t_name}: {e}"

            print(f"[Bedrock Tool] Executed '{t_name}' -> {result}")

            if on_tool_activity:
                on_tool_activity(t_name, "end")

            # Append assistant message with tool calls
            messages.append({
                "role": "assistant",
                "content": "".join(round_content_chunks) or None,
                "tool_calls": executed_tool_calls_payload,
            })

            # Append tool response
            messages.append({
                "role": "tool",
                "tool_call_id": t_id,
                "content": str(result),
            })

    # If max rounds exceeded, do one final conversational turn without tools
    try:
        final_stream = client.chat.completions.create(
            model=chosen_model,
            messages=messages,
            temperature=CHAT_TEMPERATURE,
            stream=True,
        )
        for chunk in final_stream:
            if cancel_event is not None and cancel_event.is_set():
                return
            if chunk.choices and chunk.choices[0].delta:
                delta_content = chunk.choices[0].delta.content
                if delta_content:
                    yield delta_content
    except Exception as err:
        print(f"[Bedrock] Final synthesis error with model '{chosen_model}': {err}")
        yield f"[Bedrock Error: {err}]"


def classify_emotion(text: str, model: str = DEFAULT_MODEL) -> str:
    """Classifies the emotion of a message using AWS Bedrock Mantle."""
    if not has_api_key():
        return "Neutral"

    client = get_client()
    chosen_model = model or DEFAULT_MODEL

    try:
        resp = client.chat.completions.create(
            model=chosen_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an emotion classifier for an anime companion. "
                        "Read the following text and reply with EXACTLY ONE word from: "
                        "Happy, Sad, Angry, Surprised, Relaxed, Neutral. "
                        "Do not output anything else."
                    ),
                },
                {"role": "user", "content": text},
            ],
            temperature=0.1,
            max_tokens=10,
        )
        raw = resp.choices[0].message.content or ""
        cleaned = raw.strip().capitalize()
        for emotion in VALID_EMOTIONS:
            if emotion.lower() in cleaned.lower():
                return emotion
        return "Neutral"
    except Exception as err:
        print(f"[Bedrock Emotion] Error classifying emotion: {err}")
        return "Neutral"

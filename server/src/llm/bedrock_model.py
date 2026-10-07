"""
AWS Bedrock LLM Provider
-------------------------
Integration with Amazon Bedrock Mantle OpenAI-compatible API
(https://bedrock-mantle.{region}.api.aws/v1) using AWS_BEARER_TOKEN_BEDROCK.
Supports models such as Ministral 3 8B, Google Gemma 4 (31B / 26B MoE / E2B with native tool calling),
Google Gemma 3, Qwen 3 32B, DeepSeek V3, and Claude with full streaming and tool calling.

Authentication:
  - Environment variable: AWS_BEARER_TOKEN_BEDROCK (or BEDROCK_API_KEY)
  - Region: AWS_REGION or BEDROCK_REGION (default: ap-south-1)
"""

from __future__ import annotations

import os
import json
import re
import ast
import asyncio
import threading
from typing import Generator, Callable
from dotenv import load_dotenv
from openai import OpenAI

from src.prompts.system_prompt_akari import SYSTEM_PROMPT_AKARI_ASSISTANT, get_system_prompt
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


def extract_gemma4_tool_calls(text: str) -> tuple[list[dict], str]:
    """
    Official Google Gemma 4 tool call extractor based on:
    https://ai.google.dev/gemma/docs/capabilities/text/function-calling-gemma4
    Parses <|tool_call|>call:name{args}<tool_call|>, <|tool_response|>, and casts arguments.
    """
    def cast(v: str):
        v_stripped = v.strip()
        try:
            return int(v_stripped)
        except ValueError:
            try:
                return float(v_stripped)
            except ValueError:
                return {"true": True, "false": False}.get(
                    v_stripped.lower(), v_stripped.strip("'\"")
                )

    def parse_args(args_str: str) -> dict:
        if not args_str or not args_str.strip():
            return {}
        cleaned = args_str.replace('<|">', '"').replace('<|"|>', '"')
        wrapped = cleaned if cleaned.strip().startswith("{") else "{" + cleaned + "}"
        try:
            parsed = json.loads(wrapped)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

        # Google's official regex extraction with cast()
        extracted = {}
        for k, v1, v2 in re.findall(
            r'(\w+):(?:<\|"\|>(.*?)<\|"\|>|([^,}]*))', args_str
        ):
            val = (v1 if v1 != "" else v2).strip()
            extracted[k] = cast(val)
        return extracted

    tool_call_pattern = re.compile(
        r"<\|tool_call\|?>call:(\w+)\{(.*?)\}<tool_call\|?>",
        re.DOTALL
    )

    calls = []
    for idx, (name, args) in enumerate(tool_call_pattern.findall(text)):
        parsed_args = parse_args(args)
        calls.append({
            "id": f"tc_{idx}_{name}",
            "name": name,
            "arguments": json.dumps(parsed_args),
            "parsed_arguments": parsed_args,
        })

    # Also handle standalone call:NAME{...} if emitted without tags
    if not calls:
        standalone_pattern = re.compile(r"\bcall:(\w+)\{(.*?)\}", re.DOTALL)
        for idx, (name, args) in enumerate(standalone_pattern.findall(text)):
            parsed_args = parse_args(args)
            calls.append({
                "id": f"tc_{idx}_{name}",
                "name": name,
                "arguments": json.dumps(parsed_args),
                "parsed_arguments": parsed_args,
            })
        cleaned = standalone_pattern.sub("", text)
    else:
        cleaned = tool_call_pattern.sub("", text)

    # Strip Gemma 4 tool_response control tokens and thinking blocks from user-visible speech
    cleaned = re.sub(r"<\|?tool_response\|?>", "", cleaned)
    cleaned = re.sub(r"=== Thoughts ===.*?=== Answer ===", "", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"<\|?thought\|?>.*?<\|?/?thought\|?>", "", cleaned, flags=re.DOTALL)
    cleaned = cleaned.strip()

    return calls, cleaned


def _format_messages(
    prompt: str,
    history: list,
    image: str | None = None,
    tools_enabled: bool = False,
) -> list[dict]:
    """Converts mixed history items into standard message format."""
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
            f"Please switch to 'mistral.ministral-3-8b-instruct', 'qwen.qwen3-32b', or 'openai.gpt-oss-120b'.]"
        )
    if "401" in err_str or "access_denied" in err_str or "permission_denied" in err_str:
        return (
            f"[Bedrock Notice: Access to model '{chosen_model}' was denied by Amazon Bedrock for this account. "
            f"This model requires specialized entitlement or access agreement in region '{reg}'. "
            f"Please switch to 'mistral.ministral-3-8b-instruct', 'qwen.qwen3-32b', or 'openai.gpt-oss-120b'.]"
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
        raw_text = resp.choices[0].message.content or ""
        _, clean_text = extract_gemma4_tool_calls(raw_text)
        return clean_text
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

    # Legacy Google Gemma (e.g. Gemma 3) on Bedrock Mantle drops tokens when tools parameter is supplied with system prompts.
    # Google Gemma 4 natively supports tool calling and multimodal agentic workflows!
    is_legacy_gemma = "gemma" in chosen_model.lower() and "gemma-4" not in chosen_model.lower()
    effective_tools = tools_enabled and not is_legacy_gemma

    client = get_client()
    messages = _format_messages(prompt, history, image=image, tools_enabled=effective_tools)

    # Extra parameters for reasoning models (e.g. OpenAI GPT-OSS on Bedrock)
    stream_kwargs = {}
    if "gpt-oss" in chosen_model.lower():
        stream_kwargs["max_tokens"] = 1000

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

        # Check if Gemma 4 (or model) emitted native control tokens in content stream instead of delta.tool_calls
        if not tool_calls_dict and round_content_chunks:
            full_round_text = "".join(round_content_chunks)
            extracted_calls, cleaned_text = extract_gemma4_tool_calls(full_round_text)
            if extracted_calls:
                print(
                    f"[Bedrock Gemma 4] Extracted {len(extracted_calls)} native tool calls from content stream."
                )
                for c_idx, ec in enumerate(extracted_calls):
                    tool_calls_dict[c_idx] = {
                        "id": ec["id"],
                        "name": ec["name"],
                        "arguments": ec["arguments"],
                    }
                round_content_chunks = [cleaned_text] if cleaned_text else []

        # Case 1: No tool calls requested -> final answer
        if not tool_calls_dict:
            for c in round_content_chunks:
                yield c
            return

        # Case 2: Tool calls requested
        assistant_tool_calls = [
            {
                "id": tc["id"],
                "type": "function",
                "function": {
                    "name": tc["name"],
                    "arguments": tc["arguments"],
                },
            }
            for tc in [tool_calls_dict[i] for i in sorted(tool_calls_dict.keys())]
        ]
        accumulated_text = "".join(round_content_chunks).strip()

        # Google Gemma 4 official tool response tracking (ai.google.dev/gemma/docs/capabilities/text/function-calling-gemma4)
        gemma4_tool_responses = []
        executed_tool_messages = []

        # Execute each requested tool and prepare responses
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
                try:
                    on_tool_activity(t_name, "start")
                except Exception:
                    pass

            print(f"[Bedrock Tool] Executing '{t_name}' (args: {t_args})")
            try:
                loop = asyncio.new_event_loop()
                result = loop.run_until_complete(
                    tool_registry.execute_tool(t_name, t_args, timeout=TOOL_EXECUTION_TIMEOUT)
                )
                loop.close()
            except Exception as e:
                print(f"[Bedrock Tool] Execution failed for '{t_name}': {e}")
                result = {"status": "error", "error": f"Tool execution failed: {e}"}

            print(f"[Bedrock Tool] Executed '{t_name}' -> {result}")

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

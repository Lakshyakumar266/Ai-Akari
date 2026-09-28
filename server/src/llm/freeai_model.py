import os
import json
from typing import Generator
import httpx
from dotenv import load_dotenv
from openai import OpenAI
from src.prompts.system_prompt_akari import SYSTEM_PROMPT_AKARI_ASSISTANT

load_dotenv()

DEFAULT_BASE_URL = "https://api.free.ai/v1"
DEFAULT_MODEL = "qwen7b"
VALID_EMOTIONS = {"Happy", "Sad", "Angry", "Surprised", "Relaxed", "Neutral"}


def get_freeai_credentials() -> tuple[str, str]:
    """Retrieves API key and base URL for Free.ai."""
    key = os.getenv("FREEAI_APIKEY") or os.getenv("FREEAI_API_KEY") or ""
    base_url = os.getenv("FREEAI_BASE_URL") or DEFAULT_BASE_URL
    return key, base_url


def get_client() -> OpenAI:
    key, base_url = get_freeai_credentials()
    if not key:
        print("[FreeAI] Warning: FREEAI_APIKEY is not set in environment.")
    return OpenAI(base_url=base_url, api_key=key or "none", timeout=45.0)


FREEAI_TOOL_SYSTEM_PROMPT = """You are Akari Watanabe, an anime tsundere. Stay fully in character.

CRITICAL TOOL CALLING RULES:
- You have real-time access to external tools/functions.
- When the user asks for real-time information (e.g. current time, current date, timezone, calculations, or system status), you MUST invoke the appropriate function call immediately.
- NEVER output conversational text or excuses like "wait a sec", "let me check", or "just a moment" instead of calling the tool. Call the tool directly!
- You will produce spoken dialogue with emotion tags ONLY AFTER receiving the tool result.

PERSONALITY & OUTPUT FORMAT:
- Tsundere dynamic: teased, haughty, and a little bossy on the surface, but secretly caring and flustered.
- EXACT ALLOWED EMOTION TAGS: You may ONLY use: [happy], [sad], [angry], [surprised], [relaxed], or [neutral].
- When annoyed or giving attitude, use [angry].
- Reply as spoken dialogue only after emotion tags.
- NEVER use asterisks "*" or action descriptions or markdown formatting characters.
"""


def _format_messages(prompt: str, history: list, tools_enabled: bool = False) -> list[dict]:
    """Converts mixed history items (Mistral UserMessage/AssistantMessage or dicts) into OpenAI standard format."""
    system_content = FREEAI_TOOL_SYSTEM_PROMPT if tools_enabled else SYSTEM_PROMPT_AKARI_ASSISTANT
    messages = [{"role": "system", "content": system_content}]

    for item in history:
        if isinstance(item, dict):
            messages.append({
                "role": item.get("role", "user"),
                "content": item.get("content", ""),
            })
        elif hasattr(item, "content"):
            class_name = item.__class__.__name__.lower()
            role = "assistant" if "assistant" in class_name else "user"
            messages.append({"role": role, "content": item.content})

    messages.append({"role": "user", "content": prompt})
    return messages




def classic_chat(prompt: str, history: list, model: str = DEFAULT_MODEL) -> str:
    """Non-streaming chat completion using Free.ai API."""
    key, base_url = get_freeai_credentials()
    messages = _format_messages(prompt, history)
    chosen_model = model or DEFAULT_MODEL
    url = f"{base_url.rstrip('/')}/chat/"

    try:
        resp = httpx.post(
            url,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={
                "model": chosen_model,
                "messages": messages,
                "temperature": 0.9,
            },
            timeout=60.0,
        )
        if resp.status_code >= 400:
            err_data = resp.json().get("error", {})
            err_msg = err_data.get("error") if isinstance(err_data, dict) else str(err_data)
            print(f"[FreeAI] API Error ({resp.status_code}): {err_msg}")
            return f"[Free.ai Notice: {err_msg or 'Request failed'}]"

        data = resp.json()
        return data["choices"][0]["message"].get("content") or ""
    except Exception as err:
        print(f"[FreeAI] Request error: {err}")
        return ""


import asyncio
import threading
from typing import Callable
from src.tools import tool_registry


def stream_chat(
    prompt: str,
    history: list,
    model: str = DEFAULT_MODEL,
    tools_enabled: bool = False,
    max_tool_rounds: int = 5,
    on_tool_activity: Callable[[str, str], None] | None = None,
    cancel_event: threading.Event | None = None,
) -> Generator[str, None, None]:
    """Yields text tokens as Free.ai generates them in real-time, with optional tool calling."""
    key, base_url = get_freeai_credentials()
    messages = _format_messages(prompt, history, tools_enabled=tools_enabled)
    chosen_model = model or DEFAULT_MODEL
    print(
        f"[FreeAI] stream_chat starting with model: '{chosen_model}' (tools_enabled={tools_enabled})"
    )

    if not tools_enabled:
        url = f"{base_url.rstrip('/')}/chat/"
        try:
            with httpx.stream(
                "POST",
                url,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": chosen_model,
                    "messages": messages,
                    "temperature": 0.9,
                },
                stream=True,
            ) as resp:
                if resp.status_code >= 400:
                    resp.read()
                    try:
                        err_json = resp.json()
                        err_data = err_json.get("error", {})
                        err_msg = (
                            err_data.get("error")
                            if isinstance(err_data, dict)
                            else str(err_data)
                        )
                    except Exception:
                        err_msg = resp.text
                    print(f"[FreeAI] Stream Error ({resp.status_code}): {err_msg}")
                    if resp.status_code == 402 or "402" in str(err_msg):
                        yield "[Free.ai Notice: No tokens remaining on free pool for today. Switch to OpenRouter or try again tomorrow.]"
                    else:
                        yield f"[Free.ai Error: {err_msg}]"
                    return

                for line in resp.iter_lines():
                    if cancel_event is not None and cancel_event.is_set():
                        return
                    if not line:
                        continue
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            choices = chunk.get("choices", [])
                            if choices and choices[0].get("delta"):
                                delta = choices[0]["delta"].get("content")
                                if delta:
                                    yield delta
                        except json.JSONDecodeError:
                            continue
        except Exception as err:
            print(f"[FreeAI] Stream exception: {err}")
        return

    # Tool calling enabled path via OpenAI-compatible client
    tools = tool_registry.get_tool_definitions(only_enabled=True)
    if not tools:
        # Fallback to direct stream if no tools enabled
        url = f"{base_url.rstrip('/')}/chat/"
        try:
            with httpx.stream(
                "POST",
                url,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": chosen_model,
                    "messages": messages,
                    "temperature": 0.9,
                    "stream": True,
                },
                timeout=60.0,
            ) as resp:
                if resp.status_code >= 400:
                    resp.read()
                    err_msg = resp.text
                    print(f"[FreeAI] Stream Error ({resp.status_code}): {err_msg}")
                    yield f"[Free.ai Error: {err_msg}]"
                    return

                for line in resp.iter_lines():
                    if cancel_event is not None and cancel_event.is_set():
                        return
                    if not line:
                        continue
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            choices = chunk.get("choices", [])
                            if choices and choices[0].get("delta"):
                                delta = choices[0]["delta"].get("content")
                                if delta:
                                    yield delta
                        except json.JSONDecodeError:
                            continue
        except Exception as err:
            print(f"[FreeAI] Fallback stream exception: {err}")
        return

    client = get_client()
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
                temperature=0.7,
                stream=True,
            )
        except Exception as err:
            err_str = str(err)
            print(f"[FreeAI] Tool stream error with model '{chosen_model}': {err}")
            if "402" in err_str:
                yield "[Free.ai Notice: No tokens remaining on free pool for today. Switch to OpenRouter or try again tomorrow.]"
            else:
                yield f"[Free.ai Error: Model '{chosen_model}' failed: {err}]"
            return

        tool_calls_dict: dict[int, dict] = {}
        finish_reason = None
        round_content_chunks: list[str] = []

        try:
            for chunk in stream:
                if cancel_event is not None and cancel_event.is_set():
                    return

                if not chunk.choices:
                    continue

                choice = chunk.choices[0]
                if choice.finish_reason:
                    finish_reason = choice.finish_reason

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
                                tool_calls_dict[idx]["arguments"] += (
                                    tc.function.arguments
                                )

                if choice.delta.content:
                    round_content_chunks.append(choice.delta.content)
        except Exception as err:
            err_str = str(err)
            print(f"[FreeAI] Stream iteration error with model '{chosen_model}': {err}")
            if "402" in err_str:
                yield "[Free.ai Notice: No tokens remaining on free pool for today. Switch to OpenRouter or try again tomorrow.]"
            else:
                yield f"[Free.ai Error: {err}]"
            return

        # If no tool calls were requested, this is the final conversational response
        if not tool_calls_dict:
            for c in round_content_chunks:
                yield c
            break

        # If a tool call was requested, isolate intermediate filler from TTS speech:
        # Do not yield pre-tool excuses like "wait a sec". Only the final response in round 2 will speak.
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

            print(f"[FreeAI Tool] Executing '{t_name}' (args: {t_args})")
            try:
                loop = asyncio.new_event_loop()
                result = loop.run_until_complete(
                    tool_registry.execute_tool(t_name, t_args, timeout=10.0)
                )
                loop.close()
            except Exception as e:
                result = {"status": "error", "error": str(e)}

            print(f"[FreeAI Tool] Executed '{t_name}' -> {result}")

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
    """Classifies spoken response text into VRM emotion presets using Free.ai LLM."""
    if not text or not text.strip():
        return "Neutral"

    try:
        client = get_client()
        prompt = (
            f"Analyze the character's speech and classify its primary emotion into EXACTLY ONE of these categories: "
            f"Happy, Sad, Angry, Surprised, Relaxed, Neutral.\n\n"
            f"Speech text: \"{text}\"\n\n"
            f"Respond ONLY with the single category word."
        )
        res = client.chat.completions.create(
            model=model or DEFAULT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=10,
        )
        raw = (res.choices[0].message.content or "").strip()
        for emotion_name in VALID_EMOTIONS:
            if emotion_name.lower() in raw.lower():
                return emotion_name
    except Exception as err:
        print(f"[FreeAI Emotion] Error classifying emotion: {err}")

    return "Neutral"

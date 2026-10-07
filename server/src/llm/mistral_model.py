import os
from dotenv import load_dotenv
from mistralai.client import Mistral
from mistralai.client.models import UserMessage, SystemMessage, AssistantMessage
from src.prompts.system_prompt_akari import SYSTEM_PROMPT_AKARI_ASSISTANT, get_system_prompt
from src.config import CHAT_TEMPERATURE, TOOL_TEMPERATURE, TOOL_EXECUTION_TIMEOUT, MAX_TOOL_CALL_ROUNDS

load_dotenv()

mistral_api_key = os.getenv("MISTRAL_API_KEY")

model = "ministral-8b-latest"
client = Mistral(api_key=mistral_api_key)


def classic_chat(
    prompt: str, history: list, model_name: str | None = None, image: str | None = None
) -> str:
    active_model = model_name or model
    print(f"[Mistral] classic_chat using model: '{active_model}' (has_image={bool(image)})")
    if image:
        user_msg = UserMessage(
            content=[
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image}},
            ]
        )
    else:
        user_msg = UserMessage(content=prompt)

    messages = (
        [SystemMessage(content=get_system_prompt(tools_enabled=False))]
        + _normalize_history_for_mistral(history)
        + [user_msg]
    )
    try:
        chat_response = client.chat.complete(
            model=active_model, messages=messages, temperature=CHAT_TEMPERATURE
        )
        return chat_response.choices[0].message.content or ""
    except Exception as err:
        print(f"[Mistral] Error with model '{active_model}': {err}")
        return f"[Mistral Error: Model '{active_model}' failed: {err}]"


def _normalize_history_for_mistral(history: list) -> list:
    normalized = []
    for item in history:
        if isinstance(item, dict):
            role = item.get("role", "user")
            content = item.get("content", "")
            if isinstance(content, list):
                text_parts = [p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text"]
                content = " ".join(filter(None, text_parts)).strip() or "[Image attached]"
            if role == "assistant":
                normalized.append(AssistantMessage(content=content))
            else:
                normalized.append(UserMessage(content=content))
        elif hasattr(item, "content"):
            content = item.content
            if isinstance(content, list):
                text_parts = []
                for p in content:
                    if isinstance(p, dict) and p.get("type") == "text":
                        text_parts.append(p.get("text", ""))
                    elif hasattr(p, "text") and getattr(p, "text", None):
                        text_parts.append(getattr(p, "text"))
                clean_text = " ".join(filter(None, text_parts)).strip() or "[Image attached]"
                if "assistant" in item.__class__.__name__.lower():
                    normalized.append(AssistantMessage(content=clean_text))
                else:
                    normalized.append(UserMessage(content=clean_text))
            else:
                normalized.append(item)
        else:
            normalized.append(item)
    return normalized


import json
import asyncio
import threading
import re
from typing import Callable, Generator
from mistralai.client.models import (
    UserMessage,
    SystemMessage,
    AssistantMessage,
    ToolMessage,
    ToolCall,
    FunctionCall,
)
from src.tools import tool_registry


def _has_explicit_tool_intent(text: str) -> bool:
    """Detects whether user prompt unambiguously asks for an action that requires tools."""
    lowered = text.lower()
    if (
        "http://" in lowered
        or "https://" in lowered
        or "www." in lowered
        or re.search(r"\b[a-zA-Z0-9-]+\.(?:com|org|net|io|co|app|ai|me)\b", lowered)
    ):
        return True
    tool_keywords = [
        "toolcall",
        "tool call",
        "use tool",
        "call tool",
        "call the tool",
        "what time",
        "current time",
        "time now",
        "whats time",
        "what's time",
        "timezone",
        "what date",
        "today's date",
        "todays date",
        "day of the week",
        "what day",
        "calculate",
        "search for",
        "google",
        "look up",
        "browse",
        "website",
    ]
    if any(kw in lowered for kw in tool_keywords):
        return True
    if re.search(r"\b\d+\s*[\+\-\*\/\^]\s*\d+\b", lowered):
        return True
    return False


def _is_conversational_stalling(text: str) -> bool:
    """Detects if model generated a conversational stalling excuse instead of calling the tool."""
    lowered = text.lower()
    stalling_phrases = [
        "i'll check",
        "ill check",
        "i will check",
        "let me check",
        "let me look",
        "i'll look",
        "ill look",
        "i will look",
        "checking the",
        "wait, let me",
        "hold on, let me",
        "i'm gonna look",
        "im gonna look",
        "just gonna look",
        "i'll check it out",
        "ill check it out",
    ]
    return any(p in lowered for p in stalling_phrases)


def stream_chat(
    prompt: str,
    history: list,
    model_name: str | None = None,
    image: str | None = None,
    tools_enabled: bool = False,
    max_tool_rounds: int = MAX_TOOL_CALL_ROUNDS,
    on_tool_activity: Callable[[str, str], None] | None = None,
    cancel_event: threading.Event | None = None,
) -> Generator[str, None, None]:
    """Yields text deltas as Mistral generates them, with optional multi-round tool calling."""
    active_model = model_name or model
    print(
        f"[Mistral] stream_chat starting with model: '{active_model}' (tools_enabled={tools_enabled}, has_image={bool(image)})"
    )
    normalized_history = _normalize_history_for_mistral(history)
    if image:
        user_msg = UserMessage(
            content=[
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image}},
            ]
        )
    else:
        user_msg = UserMessage(content=prompt)

    messages = (
        [SystemMessage(content=get_system_prompt(tools_enabled=tools_enabled))]
        + normalized_history
        + [user_msg]
    )

    if not tools_enabled:
        try:
            stream = client.chat.stream(
                model=active_model,
                messages=messages,
                temperature=CHAT_TEMPERATURE,
            )
            for chunk in stream:
                if cancel_event is not None and cancel_event.is_set():
                    return
                delta = chunk.data.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as err:
            print(f"[Mistral] Stream error with model '{active_model}': {err}")
            yield f"[Mistral Error: Model '{active_model}' failed: {err}]"
        return

    # Tool calling enabled:
    tools = tool_registry.get_tool_definitions(only_enabled=True)
    if not tools:
        # Fallback to direct stream if no tools enabled
        try:
            stream = client.chat.stream(
                model=active_model,
                messages=messages,
                temperature=CHAT_TEMPERATURE,
            )
            for chunk in stream:
                if cancel_event is not None and cancel_event.is_set():
                    return
                delta = chunk.data.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as err:
            yield f"[Mistral Error: Model '{active_model}' failed: {err}]"
        return

    current_round = 0
    has_explicit_intent = _has_explicit_tool_intent(prompt)

    while current_round < max_tool_rounds:
        current_round += 1
        if cancel_event is not None and cancel_event.is_set():
            return

        tool_choice_mode = "any" if (current_round == 1 and has_explicit_intent) else "auto"

        try:
            stream = client.chat.stream(
                model=active_model,
                messages=messages,
                tools=tools,
                tool_choice=tool_choice_mode,
                temperature=TOOL_TEMPERATURE,
            )
        except Exception as err:
            print(f"[Mistral] Tool stream error with model '{active_model}': {err}")
            yield f"[Mistral Error: Model '{active_model}' failed: {err}]"
            return

        tool_calls_dict: dict[str, dict] = {}
        round_content_chunks: list[str] = []

        for chunk in stream:
            if cancel_event is not None and cancel_event.is_set():
                return

            choice = chunk.data.choices[0]

            if choice.delta.tool_calls:
                for tc in choice.delta.tool_calls:
                    tc_id = tc.id or f"tc_{len(tool_calls_dict)}"
                    if tc_id not in tool_calls_dict:
                        tool_calls_dict[tc_id] = {
                            "id": tc.id or tc_id,
                            "name": tc.function.name if tc.function else "",
                            "arguments": (
                                tc.function.arguments or "" if tc.function else ""
                            ),
                        }
                    else:
                        if tc.function and tc.function.name:
                            tool_calls_dict[tc_id]["name"] = tc.function.name
                        if tc.function and tc.function.arguments:
                            tool_calls_dict[tc_id]["arguments"] += (
                                tc.function.arguments
                            )

            if choice.delta.content:
                round_content_chunks.append(choice.delta.content)

        # Fallback / Stalling recovery:
        # If no tool calls were generated but model gave conversational stalling excuses
        if not tool_calls_dict and current_round == 1:
            full_text = "".join(round_content_chunks)
            if _is_conversational_stalling(full_text) or has_explicit_intent:
                print(
                    f"[Mistral] Model generated text excuse without tool call ('{full_text[:60]}...'). Re-forcing tool execution with tool_choice='any'!"
                )
                try:
                    retry_stream = client.chat.stream(
                        model=active_model,
                        messages=messages,
                        tools=tools,
                        tool_choice="any",
                        temperature=TOOL_TEMPERATURE,
                    )
                    retry_tool_calls: dict[str, dict] = {}
                    for chunk in retry_stream:
                        if cancel_event is not None and cancel_event.is_set():
                            return
                        choice = chunk.data.choices[0]
                        if choice.delta.tool_calls:
                            for tc in choice.delta.tool_calls:
                                tc_id = tc.id or f"tc_{len(retry_tool_calls)}"
                                if tc_id not in retry_tool_calls:
                                    retry_tool_calls[tc_id] = {
                                        "id": tc.id or tc_id,
                                        "name": tc.function.name if tc.function else "",
                                        "arguments": tc.function.arguments or "" if tc.function else "",
                                    }
                                else:
                                    if tc.function and tc.function.name:
                                        retry_tool_calls[tc_id]["name"] = tc.function.name
                                    if tc.function and tc.function.arguments:
                                        retry_tool_calls[tc_id]["arguments"] += tc.function.arguments

                    if retry_tool_calls:
                        tool_calls_dict = retry_tool_calls
                        round_content_chunks = []
                except Exception as retry_err:
                    print(f"[Mistral] Tool retry error: {retry_err}")

        if not tool_calls_dict:
            # Direct response or completion without tool calls
            for c in round_content_chunks:
                yield c
            break

        # Model requested tool execution
        tool_call_objs = [
            ToolCall(
                id=t["id"],
                function=FunctionCall(name=t["name"], arguments=t["arguments"]),
            )
            for t in tool_calls_dict.values()
        ]
        messages.append(AssistantMessage(content="", tool_calls=tool_call_objs))

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

            print(f"[Mistral Tool] Executing '{t_name}' (args: {t_args})")
            try:
                loop = asyncio.new_event_loop()
                result = loop.run_until_complete(
                    tool_registry.execute_tool(t_name, t_args, timeout=TOOL_EXECUTION_TIMEOUT)
                )
                loop.close()
            except Exception as e:
                result = {"status": "error", "error": str(e)}

            print(f"[Mistral Tool] Executed '{t_name}' -> {result}")

            if on_tool_activity:
                try:
                    on_tool_activity(t_name, "end")
                except Exception:
                    pass

            messages.append(
                ToolMessage(
                    tool_call_id=t_id,
                    name=t_name,
                    content=json.dumps(result),
                )
            )



VALID_EMOTIONS = {"Happy", "Sad", "Angry", "Surprised", "Relaxed", "Neutral"}


def classify_emotion(text: str) -> str:
    """Classifies spoken response text into VRM emotion presets using Mistral LLM."""
    if not text or not text.strip():
        return "Neutral"

    try:
        prompt = (
            f"Analyze the character's speech and classify its primary emotion into EXACTLY ONE of these categories: "
            f"Happy, Sad, Angry, Surprised, Relaxed, Neutral.\n\n"
            f"Speech text: \"{text}\"\n\n"
            f"Respond ONLY with the single category word."
        )
        res = client.chat.complete(
            model=model,
            messages=[UserMessage(content=prompt)],
            temperature=0.1,
            max_tokens=10,
        )
        raw = res.choices[0].message.content.strip()
        for emotion_name in VALID_EMOTIONS:
            if emotion_name.lower() in raw.lower():
                return emotion_name
    except Exception as err:
        print(f"[LLM Emotion] Error classifying emotion: {err}")

    return "Neutral"


if __name__ == "__main__":
    history = []
    for token in stream_chat("Hello, how are you?", history):
        print(token, end="", flush=True)
    print()


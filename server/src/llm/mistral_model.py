import os
from dotenv import load_dotenv
from mistralai.client import Mistral
from mistralai.client.models import UserMessage, SystemMessage, AssistantMessage
from src.prompts.system_prompt_akari import SYSTEM_PROMPT_AKARI_ASSISTANT

load_dotenv()

mistral_api_key = os.getenv("MISTRAL_API_KEY")

model = "ministral-8b-latest"
client = Mistral(api_key=mistral_api_key)


def classic_chat(prompt: str, history: list, model_name: str | None = None) -> str:
    active_model = model_name or model
    print(f"[Mistral] classic_chat using model: '{active_model}'")
    messages = (
        [SystemMessage(content=SYSTEM_PROMPT_AKARI_ASSISTANT)]
        + _normalize_history_for_mistral(history)
        + [UserMessage(content=prompt)]
    )
    try:
        chat_response = client.chat.complete(
            model=active_model, messages=messages, temperature=0.9
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
            if role == "assistant":
                normalized.append(AssistantMessage(content=content))
            else:
                normalized.append(UserMessage(content=content))
        else:
            normalized.append(item)
    return normalized


import json
import asyncio
import threading
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


def stream_chat(
    prompt: str,
    history: list,
    model_name: str | None = None,
    tools_enabled: bool = False,
    max_tool_rounds: int = 5,
    on_tool_activity: Callable[[str, str], None] | None = None,
    cancel_event: threading.Event | None = None,
) -> Generator[str, None, None]:
    """Yields text deltas as Mistral generates them, with optional multi-round tool calling."""
    active_model = model_name or model
    print(
        f"[Mistral] stream_chat starting with model: '{active_model}' (tools_enabled={tools_enabled})"
    )
    normalized_history = _normalize_history_for_mistral(history)
    messages = (
        [SystemMessage(content=SYSTEM_PROMPT_AKARI_ASSISTANT)]
        + normalized_history
        + [UserMessage(content=prompt)]
    )

    if not tools_enabled:
        try:
            stream = client.chat.stream(
                model=active_model,
                messages=messages,
                temperature=0.9,
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
                temperature=0.9,
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
    while current_round < max_tool_rounds:
        current_round += 1
        if cancel_event is not None and cancel_event.is_set():
            return

        try:
            stream = client.chat.stream(
                model=active_model,
                messages=messages,
                tools=tools,
                temperature=0.9,
            )
        except Exception as err:
            print(f"[Mistral] Tool stream error with model '{active_model}': {err}")
            yield f"[Mistral Error: Model '{active_model}' failed: {err}]"
            return

        tool_calls_dict: dict[str, dict] = {}
        finish_reason = None

        for chunk in stream:
            if cancel_event is not None and cancel_event.is_set():
                return

            choice = chunk.data.choices[0]
            finish_reason = choice.finish_reason

            if choice.delta.tool_calls:
                for tc in choice.delta.tool_calls:
                    tc_id = tc.id or f"tc_{len(tool_calls_dict)}"
                    if tc_id not in tool_calls_dict:
                        tool_calls_dict[tc_id] = {
                            "id": tc.id,
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
                yield choice.delta.content

        if not tool_calls_dict or finish_reason != "tool_calls":
            # Direct response or completion without tool calls
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
                    tool_registry.execute_tool(t_name, t_args, timeout=10.0)
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


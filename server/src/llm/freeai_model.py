import os
from typing import Generator
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
    return OpenAI(base_url=base_url, api_key=key or "missing-key")


def _format_messages(prompt: str, history: list) -> list[dict]:
    """Converts mixed history items (Mistral UserMessage/AssistantMessage or dicts) into OpenAI standard format."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT_AKARI_ASSISTANT}]

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
    client = get_client()
    messages = _format_messages(prompt, history)
    chat_response = client.chat.completions.create(
        model=model or DEFAULT_MODEL,
        messages=messages,
        temperature=0.9,
    )
    return chat_response.choices[0].message.content or ""


def stream_chat(
    prompt: str, history: list, model: str = DEFAULT_MODEL
) -> Generator[str, None, None]:
    """Yields text tokens as Free.ai generates them in real-time."""
    client = get_client()
    messages = _format_messages(prompt, history)
    stream = client.chat.completions.create(
        model=model or DEFAULT_MODEL,
        messages=messages,
        temperature=0.9,
        stream=True,
    )
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta


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

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


def stream_chat(prompt: str, history: list, model_name: str | None = None):
    """Yields text deltas as Mistral generates them, instead of waiting for the full reply."""
    active_model = model_name or model
    print(f"[Mistral] stream_chat starting with model: '{active_model}'")
    normalized_history = _normalize_history_for_mistral(history)
    messages = (
        [SystemMessage(content=SYSTEM_PROMPT_AKARI_ASSISTANT)]
        + normalized_history
        + [UserMessage(content=prompt)]
    )
    try:
        stream = client.chat.stream(
            model=active_model,
            messages=messages,
            temperature=0.9,
        )
        for chunk in stream:
            delta = chunk.data.choices[0].delta.content
            if delta:
                yield delta
    except Exception as err:
        print(f"[Mistral] Stream error with model '{active_model}': {err}")
        yield f"[Mistral Error: Model '{active_model}' failed: {err}]"


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


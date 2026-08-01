import os
from dotenv import load_dotenv
from mistralai.client import Mistral
from mistralai.client.models import UserMessage, SystemMessage
from prompts.system_prompt_akari import SYSTEM_PROMPT_AKARI_ASSISTANT

load_dotenv()

mistral_api_key = os.getenv("MISTRAL_API_KEY")

model = "mistral-large-latest"
client = Mistral(api_key=mistral_api_key)


def classic_chat(prompt: str, history: list) -> str:
    messages = (
        [SystemMessage(content=SYSTEM_PROMPT_AKARI_ASSISTANT)]
        + history
        + [UserMessage(content=prompt)]
    )
    chat_response = client.chat.complete(
        model=model, messages=messages, temperature=0.9
    )
    return chat_response.choices[0].message.content


def stream_chat(prompt: str, history: list):
    """Yields text deltas as Mistral generates them, instead of waiting for the full reply."""
    messages = (
        [SystemMessage(content=SYSTEM_PROMPT_AKARI_ASSISTANT)]
        + history
        + [UserMessage(content=prompt)]
    )
    stream = client.chat.stream(
        model=model,
        messages=messages,
        temperature=0.9,
    )
    for chunk in stream:
        delta = chunk.data.choices[0].delta.content
        if delta:
            yield delta


if __name__ == "__main__":
    history = []
    for token in stream_chat("Hello, how are you?", history):
        print(token, end="", flush=True)
    print()

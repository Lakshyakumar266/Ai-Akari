"""
Chat Loop
---------
Processes a single chat message from the browser UI.

Mirrors the same LLM → TTS → dispatch pipeline as voice/loop.py,
but receives text directly instead of listening on the server mic.
"""

from __future__ import annotations

import asyncio
import re
import string
import base64
from concurrent.futures import ThreadPoolExecutor

from mistralai.client.models import (
    AssistantMessage,
    UserMessage,
)

from src.config import ENABLE_SUBTITLES
from src.bridge.dispatcher import dispatch
from src.bridge.events import (
    transcript,
    speech_start,
    speech_segment,
)
from src.llm.mistral_model import stream_chat
from src.tts.text_to_speech import convert_to_wav
from src.voice.emotion_feature import (
    EmotionFeatureManager,
    strip_all_emotion_tags,
    split_dialogue_units_with_emotions,
)
from src.prompts.system_prompt_akari import EXIT_PHRASES


def split_into_dialogue_units(text: str, max_words: int = 16) -> list[str]:
    sentences = re.split(r"(?<=[.!?\n])\s+", text.strip())
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        return [text.strip()] if text.strip() else []

    units: list[str] = []
    current_unit: list[str] = []
    current_word_count = 0

    for s in sentences:
        s_words = len(s.split())
        if current_unit and (current_word_count + s_words > max_words):
            units.append(" ".join(current_unit))
            current_unit = [s]
            current_word_count = s_words
        else:
            current_unit.append(s)
            current_word_count += s_words

    if current_unit:
        units.append(" ".join(current_unit))

    return units


# ─── Shared conversation history ─────────────────────────────────────────────

_history: list = []


async def process_chat_message(user_text: str):
    """
    End-to-end pipeline for a user chat message:
      1. Dispatch transcript event (so client can show what the user said)
      2. Stream LLM response
      3. Generate TTS audio per dialogue unit
      4. Dispatch speech_segment events to client
    """
    global _history

    if not user_text.strip():
        return

    print(f"[Chat] You: {user_text}")
    await transcript(user_text)

    # Check for exit phrases
    cleaned = user_text.strip().lower().strip(string.punctuation)
    if cleaned in EXIT_PHRASES:
        goodbye = "...fine, bye. Don't miss me too much."
        print(f"[Chat] Akari: {goodbye}")
        wav_bytes = await asyncio.to_thread(convert_to_wav, goodbye)
        b64_audio = base64.b64encode(wav_bytes).decode("ascii")
        data_uri = f"data:audio/wav;base64,{b64_audio}"
        await speech_start()
        await speech_segment(
            text=goodbye if ENABLE_SUBTITLES else "",
            audio=data_uri,
            is_last=True,
            segment_index=0,
            total_segments=1,
            emotion="Sad",
        )
        return

    full_reply: list[str] = []
    emotion_mgr = EmotionFeatureManager()

    loop = asyncio.get_running_loop()
    unit_queue: asyncio.Queue[tuple[str, str] | None] = asyncio.Queue()

    def stream_and_chunk():
        print("[Chat] Akari: ", end="", flush=True)
        buffer = ""
        current_sentence = ""

        try:
            for token in stream_chat(user_text, _history):
                print(token, end="", flush=True)
                full_reply.append(token)
                buffer += token

                buffer = emotion_mgr.on_token(token, buffer, dispatch)
                current_emotion = emotion_mgr.detected_emotion or "Neutral"

                if "[" in buffer:
                    last_bracket = buffer.rfind("[")
                    if last_bracket > 0:
                        current_sentence += buffer[:last_bracket]
                        buffer = buffer[last_bracket:]
                else:
                    if buffer:
                        current_sentence += buffer
                        buffer = ""

                # Check for dialogue unit boundary (. ! ? followed by space, or max 16 words)
                words = current_sentence.split()
                has_sentence_end = bool(re.search(r"[.!?\n]\s*$", current_sentence))
                if (has_sentence_end and len(words) >= 3) or len(words) >= 16:
                    clean = strip_all_emotion_tags(current_sentence).strip()
                    if clean:
                        loop.call_soon_threadsafe(unit_queue.put_nowait, (clean, current_emotion))
                    current_sentence = ""

            if buffer:
                current_sentence += buffer
            clean = strip_all_emotion_tags(current_sentence).strip()
            if clean:
                current_emotion = emotion_mgr.detected_emotion or "Neutral"
                loop.call_soon_threadsafe(unit_queue.put_nowait, (clean, current_emotion))

        except Exception as e:
            print("[Chat] LLM stream error:", e)
        finally:
            print()
            loop.call_soon_threadsafe(unit_queue.put_nowait, None)

    llm_task = asyncio.create_task(asyncio.to_thread(stream_and_chunk))

    segment_index = 0
    speech_started = False

    while True:
        unit = await unit_queue.get()
        if unit is None:
            break

        u_text, u_emotion = unit

        try:
            wav_bytes = await asyncio.to_thread(convert_to_wav, u_text)
            b64_audio = base64.b64encode(wav_bytes).decode("ascii")
            data_uri = f"data:audio/wav;base64,{b64_audio}"

            if not speech_started:
                await speech_start()
                speech_started = True

            await speech_segment(
                text=u_text if ENABLE_SUBTITLES else "",
                audio=data_uri,
                is_last=False,
                segment_index=segment_index,
                total_segments=-1,
                emotion=u_emotion if emotion_mgr.mode == "synced" else None,
            )
            segment_index += 1
        except Exception as e:
            print(f"[Chat] TTS error for '{u_text}':", e)

    await llm_task

    emotion_mgr.on_speech_concluded(dispatch)

    raw_reply = "".join(full_reply)
    clean_reply = strip_all_emotion_tags(raw_reply).strip()
    _history.append(UserMessage(content=user_text))
    _history.append(AssistantMessage(content=clean_reply))

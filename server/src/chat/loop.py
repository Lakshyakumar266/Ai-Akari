"""
Chat Loop
---------
Processes a single chat message from the browser UI.

Mirrors the same LLM → TTS → dispatch pipeline as voice/loop.py,
but receives text directly instead of listening on the server mic.
Supports immediate stream cancellation when user clicks Stop.
"""

from __future__ import annotations

import asyncio
import re
import string
import base64
import threading

from mistralai.client.models import (
    AssistantMessage,
    UserMessage,
)

from src.config import ENABLE_SUBTITLES
from src.bridge.dispatcher import dispatch
from src.bridge.events import (
    transcript,
    speech_start,
    speech_end,
    speech_segment,
    turn_end,
    thinking_start,
    thinking_end,
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


# ─── Shared conversation history & active task tracking ──────────────────────

_history: list = []
_active_cancel_event: threading.Event | None = None
_active_chat_task: asyncio.Task | None = None
_suppress_cancel_speech_end = False


def set_active_chat_task(task: asyncio.Task | None):
    global _active_chat_task
    _active_chat_task = task


async def stop_chat_stream(emit_speech_end: bool = True):
    """Immediately halts the active LLM stream, TTS synthesis, and speech dispatch."""
    global _active_cancel_event, _active_chat_task, _suppress_cancel_speech_end
    print(f"[Chat] Stopping active stream (emit_speech_end={emit_speech_end})...")

    if not emit_speech_end:
        _suppress_cancel_speech_end = True

    if _active_cancel_event is not None:
        _active_cancel_event.set()

    if _active_chat_task is not None and not _active_chat_task.done():
        _active_chat_task.cancel()
        try:
            await _active_chat_task
        except (asyncio.CancelledError, Exception):
            pass
        _active_chat_task = None

    if emit_speech_end:
        await speech_end()

    _suppress_cancel_speech_end = False
    print("[Chat] Stream successfully stopped.")


async def process_chat_message(user_text: str):
    """
    End-to-end pipeline for a user chat message:
      1. Dispatch transcript event (so client can show what the user said)
      2. Stream LLM response
      3. Generate TTS audio per dialogue unit
      4. Dispatch speech_segment events to client
    """
    global _history, _active_cancel_event

    if not user_text.strip():
        return

    cancel_event = threading.Event()
    _active_cancel_event = cancel_event

    print(f"[Chat] You: {user_text}")
    await transcript(user_text)
    await thinking_start()

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
        await turn_end()
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
                if cancel_event.is_set():
                    print("\n[Chat] Stream cancelled by user stop request.")
                    return

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
            if not cancel_event.is_set():
                print("[Chat] LLM stream error:", e)
        finally:
            print()
            loop.call_soon_threadsafe(unit_queue.put_nowait, None)

    llm_task = asyncio.create_task(asyncio.to_thread(stream_and_chunk))

    segment_index = 0
    speech_started = False
    pending: tuple[str, str, str, int] | None = None

    try:
        while True:
            if cancel_event.is_set():
                break

            try:
                unit = await asyncio.wait_for(unit_queue.get(), timeout=0.1)
            except asyncio.TimeoutError:
                if cancel_event.is_set():
                    break
                if llm_task.done() and unit_queue.empty():
                    break
                continue

            if cancel_event.is_set():
                break

            # If we had a pending unit, we now know whether it was the last or not:
            if pending is not None:
                p_text, p_emotion, p_audio, p_idx = pending
                is_last_unit = (unit is None)
                if not speech_started:
                    await speech_start()
                    speech_started = True

                await speech_segment(
                    text=p_text if ENABLE_SUBTITLES else "",
                    audio=p_audio,
                    is_last=is_last_unit,
                    segment_index=p_idx,
                    total_segments=-1,
                    emotion=p_emotion if emotion_mgr.mode == "synced" else None,
                )
                pending = None

            if unit is None:
                break

            u_text, u_emotion = unit

            try:
                wav_bytes = await asyncio.to_thread(convert_to_wav, u_text)
                if cancel_event.is_set():
                    break

                b64_audio = base64.b64encode(wav_bytes).decode("ascii")
                data_uri = f"data:audio/wav;base64,{b64_audio}"
                pending = (u_text, u_emotion, data_uri, segment_index)
                segment_index += 1
            except Exception as e:
                if not cancel_event.is_set():
                    print(f"[Chat] TTS error for '{u_text}':", e)

        # Flush any remaining pending unit as is_last=True
        if pending is not None and not cancel_event.is_set():
            p_text, p_emotion, p_audio, p_idx = pending
            if not speech_started:
                await speech_start()
                speech_started = True

            await speech_segment(
                text=p_text if ENABLE_SUBTITLES else "",
                audio=p_audio,
                is_last=True,
                segment_index=p_idx,
                total_segments=-1,
                emotion=p_emotion if emotion_mgr.mode == "synced" else None,
            )

        if not cancel_event.is_set():
            await llm_task
            await turn_end()
            emotion_mgr.on_speech_concluded(dispatch)

            raw_reply = "".join(full_reply)
            clean_reply = strip_all_emotion_tags(raw_reply).strip()
            if clean_reply:
                _history.append(UserMessage(content=user_text))
                _history.append(AssistantMessage(content=clean_reply))
        else:
            if not llm_task.done():
                llm_task.cancel()
            await speech_end()
            emotion_mgr.on_speech_concluded(dispatch)

    except asyncio.CancelledError:
        cancel_event.set()
        if not llm_task.done():
            llm_task.cancel()
        if not _suppress_cancel_speech_end:
            await speech_end()
            emotion_mgr.on_speech_concluded(dispatch)
        raise
    finally:
        _active_cancel_event = None

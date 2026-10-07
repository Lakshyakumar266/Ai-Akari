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

from src.config import ENABLE_SUBTITLES, MAX_TOOL_CALL_ROUNDS
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
from src.llm import stream_chat, compact_conversation_async, should_compact
from src.tts.text_to_speech import convert_to_wav
from src.voice.emotion_feature import (
    EmotionFeatureManager,
    strip_all_emotion_tags,
    split_dialogue_units_with_emotions,
    strip_tool_leakage,
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


async def process_chat_message(
    user_text: str,
    image: str | None = None,
    tools_enabled: bool = False,
    max_tool_rounds: int = MAX_TOOL_CALL_ROUNDS,
):
    """
    End-to-end pipeline for a user chat message:
      1. Dispatch transcript event (so client can show what the user said)
      2. Stream LLM response (with optional vision and tool execution)
      3. Generate TTS audio per dialogue unit
      4. Dispatch speech_segment events to client
    """
    global _history, _active_cancel_event

    if not user_text.strip() and not image:
        return

    cancel_event = threading.Event()
    _active_cancel_event = cancel_event

    print(f"[Chat] You: {user_text} (has_image={bool(image)}, tools_enabled={tools_enabled})")
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

    def on_tool_activity(tool_name: str, stage: str):
        from src.bridge.events import tool_start, tool_end

        if stage == "start":
            loop.call_soon_threadsafe(asyncio.create_task, tool_start(tool_name))
        else:
            loop.call_soon_threadsafe(asyncio.create_task, tool_end(tool_name))

    def stream_and_chunk():
        started_printing = False
        buffer = ""
        current_sentence = ""
        leak_buffer = ""
        holding_potential_leak = False

        try:
            for token in stream_chat(
                user_text,
                _history,
                image=image,
                tools_enabled=tools_enabled,
                max_tool_rounds=max_tool_rounds,
                on_tool_activity=on_tool_activity,
                cancel_event=cancel_event,
            ):
                if cancel_event.is_set():
                    print("\n[Chat] Stream cancelled by user stop request.")
                    return

                # Suppress leaked JSON tool envelopes or control tags at the start of generation
                if not started_printing and (token.lstrip().startswith(("{", "<|", "<tool_call")) or holding_potential_leak):
                    holding_potential_leak = True
                    leak_buffer += token
                    cleaned_leak = strip_tool_leakage(leak_buffer)
                    if cleaned_leak.strip():
                        holding_potential_leak = False
                        try:
                            print("[Chat] Akari: ", end="", flush=True)
                            print(cleaned_leak, end="", flush=True)
                        except Exception:
                            pass
                        started_printing = True
                        token = cleaned_leak
                        leak_buffer = ""
                    else:
                        continue
                else:
                    if not started_printing:
                        try:
                            print("[Chat] Akari: ", end="", flush=True)
                        except Exception:
                            pass
                        started_printing = True

                    try:
                        print(token, end="", flush=True)
                    except Exception:
                        pass

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
                # Store text context in conversation history rather than giant base64 image data URIs
                # so subsequent turns do not bloat context or crash text-only models
                history_text = user_text
                if image:
                    history_text = f"[Image attached] {user_text}".strip() if user_text else "[Image attached]"
                _history.append(UserMessage(content=history_text))
                _history.append(AssistantMessage(content=clean_reply))
                if should_compact(_history):
                    _history = await compact_conversation_async(_history)
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

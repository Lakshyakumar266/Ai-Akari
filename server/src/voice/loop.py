import asyncio
import re
import string
import threading
import base64
from concurrent.futures import ThreadPoolExecutor

from src.config import ENABLE_SUBTITLES
from src.voice.emotion_feature import (
    EmotionFeatureManager,
    strip_all_emotion_tags,
    split_dialogue_units_with_emotions,
)

from mistralai.client.models import (
    AssistantMessage,
    UserMessage,
)

from src.asr.server_asr import (
    listen_and_capture,
    transcribe_audio,
)

from src.bridge.dispatcher import dispatch
from src.bridge.events import (
    transcript,
    emotion,
    subtitle,
    speech_start,
    speech_end,
    speech_segment,
    turn_end,
)


from src.llm.mistral_model import (
    stream_chat,
    classify_emotion,
)


from src.prompts.system_prompt_akari import (
    EXIT_PHRASES,
)

from src.tts.text_to_speech import (
    convert_to_wav,
    stream_audio,
)


def split_into_dialogue_units(text: str, max_words: int = 16) -> list[str]:
    sentences = re.split(r"(?<=[.!?\n])\s+", text.strip())
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        return [text.strip()] if text.strip() else []

    units = []
    current_unit = []
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


async def run_voice_loop(stop_event: threading.Event | None = None):
    history = []

    print(
        "[VoiceLoop] Akari companion voice loop is live. Say 'stop' to exit.\n"
    )

    while True:
        if stop_event and stop_event.is_set():
            print("[VoiceLoop] Stop event detected before listening.")
            break

        try:
            #
            # Listen
            #
            audio = await asyncio.to_thread(
                listen_and_capture,
                stop_event,
            )

            if stop_event and stop_event.is_set():
                break

            if audio.size == 0:
                continue

            user_text = await asyncio.to_thread(
                transcribe_audio,
                audio,
            )

            if stop_event and stop_event.is_set():
                break

            if not user_text.strip():
                continue

            print(f"You: {user_text}")

            dispatch(
                transcript(user_text)
            )

            cleaned = (
                user_text.strip()
                .lower()
                .strip(string.punctuation)
            )

            if cleaned in EXIT_PHRASES:
                goodbye = (
                    "...fine, bye. Don't miss me too much."
                )

                print(f"Akari: {goodbye}")

                wav_bytes = await asyncio.to_thread(convert_to_wav, goodbye)
                b64_audio = base64.b64encode(wav_bytes).decode("ascii")
                data_uri = f"data:audio/wav;base64,{b64_audio}"

                dispatch(speech_start())
                dispatch(
                    speech_segment(
                        text=goodbye if ENABLE_SUBTITLES else "",
                        audio=data_uri,
                        is_last=True,
                        segment_index=0,
                        total_segments=1,
                        emotion="Neutral",
                    )
                )
                dispatch(turn_end())
                break

            full_reply: list[str] = []
            clean_chunks: list[str] = []
            emotion_mgr = EmotionFeatureManager()

            def collect_chunks():
                print("Akari: ", end="", flush=True)

                buffer = ""

                for token in stream_chat(user_text, history):
                    if stop_event and stop_event.is_set():
                        break

                    print(token, end="", flush=True)
                    full_reply.append(token)

                    buffer += token

                    # Handle emotion tags via shiftable EmotionFeatureManager
                    buffer = emotion_mgr.on_token(token, buffer, dispatch)

                    # Hold partial bracket tags (e.g. "[hap") until closing bracket arrives
                    if "[" in buffer:
                        last_bracket = buffer.rfind("[")
                        if last_bracket > 0:
                            clean_chunks.append(buffer[:last_bracket])
                            buffer = buffer[last_bracket:]
                    else:
                        if buffer:
                            clean_chunks.append(buffer)
                            buffer = ""

                if buffer:
                    clean = strip_all_emotion_tags(buffer)
                    if clean:
                        clean_chunks.append(clean)

                print()

            #
            # Collect all LLM tokens first.
            #
            await asyncio.to_thread(collect_chunks)

            if stop_event and stop_event.is_set():
                break

            raw_reply = "".join(full_reply)
            
            if emotion_mgr.mode == "synced":
                units_with_emotions = split_dialogue_units_with_emotions(raw_reply, max_words=16)
            else:
                clean_reply = strip_all_emotion_tags(raw_reply).strip()
                legacy_units = split_into_dialogue_units(clean_reply, max_words=16)
                units_with_emotions = [(u, emotion_mgr.detected_emotion or "Neutral") for u in legacy_units]

            clean_reply = " ".join([u[0] for u in units_with_emotions]).strip()

            if units_with_emotions:
                unit_texts = [u[0] for u in units_with_emotions]

                def gen_unit(u: str) -> tuple[str, bytes]:
                    return u, convert_to_wav(u)

                # Generate TTS audio for each dialogue unit in parallel
                with ThreadPoolExecutor(max_workers=max(1, len(units_with_emotions))) as executor:
                    generated = await asyncio.to_thread(
                        lambda: list(executor.map(gen_unit, unit_texts))
                    )

                if stop_event and stop_event.is_set():
                    break

                dispatch(speech_start())

                for i, ((u_text, u_emotion), (_, wav_bytes)) in enumerate(zip(units_with_emotions, generated)):
                    b64_audio = base64.b64encode(wav_bytes).decode("ascii")
                    data_uri = f"data:audio/wav;base64,{b64_audio}"
                    dispatch(
                        speech_segment(
                            text=u_text if ENABLE_SUBTITLES else "",
                            audio=data_uri,
                            is_last=(i == len(units_with_emotions) - 1),
                            segment_index=i,
                            total_segments=len(units_with_emotions),
                            emotion=u_emotion if emotion_mgr.mode == "synced" else None,
                        )
                    )

                dispatch(turn_end())
                emotion_mgr.on_speech_concluded(dispatch)

            history.append(
                UserMessage(
                    content=user_text
                )
            )

            history.append(
                AssistantMessage(
                    content=clean_reply
                )
            )
        except asyncio.CancelledError:
            print("[VoiceLoop] Voice loop task cancelled.")
            break
        except KeyboardInterrupt:
            print("\nStopped.")
            break


# ─── Global Background Task Management for Voice Loop ────────────────────────

_voice_loop_task: asyncio.Task | None = None
_voice_loop_stop_event = threading.Event()


def is_voice_loop_running() -> bool:
    return _voice_loop_task is not None and not _voice_loop_task.done()


async def start_voice_loop():
    """Starts the server-side voice loop task in the background if not already running."""
    global _voice_loop_task, _voice_loop_stop_event
    if is_voice_loop_running():
        print("[VoiceLoop] Background loop already running.")
        return

    _voice_loop_stop_event.clear()
    _voice_loop_task = asyncio.create_task(run_voice_loop(_voice_loop_stop_event))
    print("[VoiceLoop] Started background voice loop task.")


async def stop_voice_loop():
    """Gracefully halts the server-side voice loop task."""
    global _voice_loop_task, _voice_loop_stop_event
    _voice_loop_stop_event.set()
    if _voice_loop_task is not None and not _voice_loop_task.done():
        _voice_loop_task.cancel()
        try:
            await _voice_loop_task
        except (asyncio.CancelledError, Exception):
            pass
        _voice_loop_task = None
        print("[VoiceLoop] Stopped background voice loop task.")
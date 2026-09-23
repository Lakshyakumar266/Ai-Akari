import asyncio
import re
import string

EMOTION_TAG_PATTERN = re.compile(r"^\[(happy|sad|angry|surprised|relaxed|neutral)\]", re.IGNORECASE)

from mistralai.client.models import (
    AssistantMessage,
    UserMessage,
)

from src.asr.voice_to_text import (
    listen_and_capture,
    transcribe_audio,
)

import base64
from concurrent.futures import ThreadPoolExecutor

from src.bridge.dispatcher import dispatch
from src.bridge.events import (
    transcript,
    emotion,
    subtitle,
    speech_start,
    speech_end,
    speech_segment,
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


async def run_voice_loop():
    history = []

    print(
        "Akari companion is live. Say 'stop' to exit.\n"
    )

    while True:
        try:
            #
            # Listen
            #
            audio = await asyncio.to_thread(
                listen_and_capture
            )

            user_text = await asyncio.to_thread(
                transcribe_audio,
                audio,
            )

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

                await asyncio.to_thread(
                    stream_audio,
                    iter([goodbye]),
                )
                break

            full_reply: list[str] = []
            clean_chunks: list[str] = []

            def collect_chunks():
                print("Akari: ", end="", flush=True)

                buffer = ""

                for token in stream_chat(user_text, history):
                    
                    print(token, end="", flush=True)
                    full_reply.append(token)

                    buffer += token

                    # Detect and dispatch any emotion tags in the streaming buffer
                    matches = list(EMOTION_TAG_PATTERN.finditer(buffer))
                    if matches:
                        for match in matches:
                            tag_emotion = match.group(1).capitalize()
                            print(f"\n[{tag_emotion}]")
                            dispatch(emotion(tag_emotion))

                        buffer = EMOTION_TAG_PATTERN.sub("", buffer)

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
                    clean = EMOTION_TAG_PATTERN.sub("", buffer)
                    if clean:
                        clean_chunks.append(clean)

                print()

            #
            # Collect all LLM tokens first.
            #
            await asyncio.to_thread(collect_chunks)

            raw_reply = "".join(clean_chunks)
            clean_reply = EMOTION_TAG_PATTERN.sub("", raw_reply).strip()

            if clean_reply:
                units = split_into_dialogue_units(clean_reply, max_words=16)

                def gen_unit(u: str) -> tuple[str, bytes]:
                    return u, convert_to_wav(u)

                # Generate TTS audio for each dialogue unit in parallel
                with ThreadPoolExecutor(max_workers=max(1, len(units))) as executor:
                    generated = await asyncio.to_thread(
                        lambda: list(executor.map(gen_unit, units))
                    )

                dispatch(speech_start())

                for i, (u_text, wav_bytes) in enumerate(generated):
                    b64_audio = base64.b64encode(wav_bytes).decode("ascii")
                    data_uri = f"data:audio/wav;base64,{b64_audio}"
                    dispatch(
                        speech_segment(
                            text=u_text,
                            audio=data_uri,
                            is_last=(i == len(generated) - 1),
                            segment_index=i,
                            total_segments=len(generated),
                        )
                    )

                dispatch(emotion("Neutral"))


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
        except KeyboardInterrupt:
            print("\nStopped.")
            break
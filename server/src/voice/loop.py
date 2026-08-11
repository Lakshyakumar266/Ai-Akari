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

from src.bridge.dispatcher import dispatch
from src.bridge.events import (
    transcript,
    emotion,
    speech_start,
    speech_end,
)


from src.llm.mistral_model import (
    stream_chat,
    classify_emotion,
)


from src.prompts.system_prompt_akari import (
    EXIT_PHRASES,
)

from src.tts.text_to_speech import (
    stream_audio,
)


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

            def text_chunks():
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
                            print(f"\n[Akari Emotion Tag] {tag_emotion}")
                            dispatch(emotion(tag_emotion))

                        buffer = EMOTION_TAG_PATTERN.sub("", buffer)

                    # Hold partial bracket tags (e.g. "[hap") until closing bracket arrives
                    if "[" in buffer:
                        last_bracket = buffer.rfind("[")
                        if last_bracket > 0:
                            yield buffer[:last_bracket]
                            buffer = buffer[last_bracket:]
                    else:
                        if buffer:
                            yield buffer
                            buffer = ""

                if buffer:
                    clean = EMOTION_TAG_PATTERN.sub("", buffer)
                    if clean:
                        yield clean

                print()

            #
            # Start streaming TTS to browser.
            #
            dispatch(speech_start())
            await asyncio.to_thread(
                stream_audio,
                text_chunks(),
            )
            dispatch(speech_end())
            dispatch(emotion("Neutral"))


            #
            # Clean reply text for conversation history (remove all [emotion] tags)
            #
            raw_reply = "".join(full_reply)
            clean_reply = EMOTION_TAG_PATTERN.sub("", raw_reply).strip()


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
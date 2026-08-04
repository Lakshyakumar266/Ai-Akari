import asyncio
import string

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
)

from src.llm.mistral_model import (
    stream_chat,
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

                for token in stream_chat(
                    user_text,
                    history,
                ):
                    print(
                        token,
                        end="",
                        flush=True,
                    )

                    full_reply.append(token)

                    #
                    # FishAudio receives every token immediately.
                    #
                    yield token

                print()

            #
            # Start streaming TTS to browser.
            #
            await asyncio.to_thread(
                stream_audio,
                text_chunks(),
            )

            #
            # Store conversation history.
            #
            reply = "".join(full_reply)

            history.append(
                UserMessage(
                    content=user_text
                )
            )

            history.append(
                AssistantMessage(
                    content=reply
                )
            )

        except KeyboardInterrupt:
            print("\nStopped.")
            break
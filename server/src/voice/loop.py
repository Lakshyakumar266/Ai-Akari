import asyncio
import string
import time

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
    speech,
    transcript,
)

from src.lipsync.speech import (
    build_speech_timeline,
)

from src.llm.mistral_model import (
    stream_chat,
)

from src.prompts.system_prompt_akari import (
    EXIT_PHRASES,
)

from src.streaming.splitter import (
    SentenceSplitter,
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

            splitter = SentenceSplitter()

            def text_chunks():

                print(
                    "Akari: ",
                    end="",
                    flush=True,
                )
                print("Generator started")

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

                    #
                    # As soon as a sentence finishes,
                    # send its viseme timeline.
                    #
                    for sentence in splitter.push(token):

                        timeline = build_speech_timeline(
                            sentence
                        )

                        print(
                            f"[SERVER] Dispatch speech @ {time.perf_counter():.3f}"
                        )

                        dispatch(
                            speech(timeline)
                        )
                print("Generator finished")

                #
                # Flush remaining text.
                #
                for sentence in splitter.flush():

                    timeline = build_speech_timeline(
                        sentence
                    )

                    dispatch(
                        speech(timeline)
                    )

                print()

            #
            # Start streaming TTS.
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
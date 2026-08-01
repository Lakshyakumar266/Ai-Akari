from mistralai.client.models import UserMessage, AssistantMessage
import string

from asr.voice_to_text import listen_and_capture, transcribe_audio
from prompts.system_prompt_akari import EXIT_PHRASES
from tts.text_to_speech import stream_audio
from llm.mistral_model import stream_chat


def run_voice_loop():
    history = []

    print("Akari companion is live. Say 'stop' to exit.\n")

    while True:
        try:
            audio = listen_and_capture()
            user_text = transcribe_audio(audio)

            if not user_text.strip():
                continue

            print(f"You: {user_text}")

            cleaned = user_text.strip().lower().strip(string.punctuation)
            if cleaned in EXIT_PHRASES:
                print("Akari: ...fine, bye. Don't miss me too much.")
                stream_audio("...fine, bye. Don't miss me too much.")  
                break

            full_reply = []

            def text_chunks():
                print("Akari: ", end="", flush=True)
                for token in stream_chat(user_text, history):
                    print(token, end="", flush=True)
                    full_reply.append(token)
                    yield token
                print()

            stream_audio(
                text_chunks()
            )  # audio starts playing before the full reply exists

            reply = "".join(full_reply)
            history.append(UserMessage(content=user_text))
            history.append(AssistantMessage(content=reply))

        except KeyboardInterrupt:
            print("\nStopped.")
            break


if __name__ == "__main__":
    run_voice_loop()

import os
from dotenv import load_dotenv
from fishaudio import FishAudio

from src.bridge.audio import audio_chunk, audio_end
from src.bridge.dispatcher import dispatch

load_dotenv()

fish_audio_api_key = os.getenv("FISH_AUDIO_API_KEY")
fishClient = FishAudio(api_key=fish_audio_api_key)

REFERENCE_ID = os.getenv("FISH_AUDIO_REFERENCE_ID")
TTS_MODEL = "s2.1-pro-free"


def get_audio(text: str):
    audio = fishClient.tts.convert(
        text=text,
        reference_id=REFERENCE_ID,
        model=TTS_MODEL,
    )
    dispatch(audio_chunk(audio))
    dispatch(audio_end())


def convert_to_wav(text: str) -> bytes:
    return fishClient.tts.convert(
        text=text,
        reference_id=REFERENCE_ID,
        model=TTS_MODEL,
        format="wav",   
    )


def stream_audio(text_chunks):
    print("[TTS] Calling Fish WebSocket stream...")
    audio_stream = fishClient.tts.stream_websocket(
        text_chunks,
        reference_id=REFERENCE_ID,
        model=TTS_MODEL,
        format="pcm",
        latency="balanced",
    )
    print("[TTS] Streaming audio chunks to browser...")
    try:
        for chunk in audio_stream:
            if chunk:
                dispatch(audio_chunk(chunk))
    finally:
        dispatch(audio_end())
        print("[TTS] Audio stream finished.")


if __name__ == "__main__":
    def demo_chunks():
        yield "Hey, "
        yield "this is "
        yield "streaming audio!"

    stream_audio(demo_chunks())
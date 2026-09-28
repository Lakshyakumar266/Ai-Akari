import os
from dotenv import load_dotenv
from fishaudio import FishAudio

from . import sovits_client

load_dotenv()

fish_audio_api_key = os.getenv("FISH_AUDIO_API_KEY")
fishClient = FishAudio(api_key=fish_audio_api_key)

REFERENCE_ID = os.getenv("FISH_AUDIO_REFERENCE_ID")
TTS_MODEL = "s2.1-pro-free"

AVAILABLE_TTS_ENGINES = ["fish", "sovits"]
_active_tts_engine = os.getenv("TTS_ENGINE", "fish").lower()
if _active_tts_engine not in AVAILABLE_TTS_ENGINES:
    _active_tts_engine = "fish"


def set_active_tts_engine(engine: str) -> str:
    """Switches the active TTS engine ('fish' or 'sovits')."""
    global _active_tts_engine
    target = (engine or "").lower().strip()
    if target in AVAILABLE_TTS_ENGINES:
        _active_tts_engine = target
        print(f"[TTS] Active voice engine set to: '{_active_tts_engine}'")
    else:
        print(f"[TTS] Unknown engine '{engine}', keeping '{_active_tts_engine}'")
    return _active_tts_engine


def get_active_tts_engine() -> str:
    """Returns the currently active TTS engine identifier."""
    return _active_tts_engine


def get_audio(text: str):
    from src.bridge.audio import audio_chunk, audio_end
    from src.bridge.dispatcher import dispatch

    wav = convert_to_wav(text)
    dispatch(audio_chunk(wav))
    dispatch(audio_end())


def convert_to_wav(text: str) -> bytes:
    """Synthesizes speech to WAV bytes using the active TTS engine (Fish Audio or GPT-SoVITS)."""
    if _active_tts_engine == "sovits":
        return sovits_client.convert_to_wav(text)

    return fishClient.tts.convert(
        text=text,
        reference_id=REFERENCE_ID,
        model=TTS_MODEL,
        format="wav",
    )


def stream_audio(text_chunks):
    from src.bridge.audio import audio_chunk, audio_end
    from src.bridge.dispatcher import dispatch

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
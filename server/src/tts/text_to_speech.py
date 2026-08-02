import os
import subprocess
import time

from dotenv import load_dotenv
from fishaudio import FishAudio
from fishaudio.utils import play

load_dotenv()

fish_audio_api_key = os.getenv("FISH_AUDIO_API_KEY")
fishClient = FishAudio(api_key=fish_audio_api_key)

REFERENCE_ID = os.getenv("FISH_AUDIO_REFERENCE_ID")
TTS_MODEL = "s2.1-pro-free"

"""Absolute path — no dependency on PATH or winget, download from https://sourceforge.net/projects/mpv-player-windows/files/64bit/"""
MPV_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "bin",
    "mpv-windows",
    "mpv.exe",
)


def get_audio(text: str):
    audio = fishClient.tts.convert(
        text=text,
        reference_id=REFERENCE_ID,
        model=TTS_MODEL,
    )
    play(audio, use_ffmpeg=False)


def stream_audio(text_chunks):
    print("Calling Fish")
    audio_stream = fishClient.tts.stream_websocket(
        text_chunks,
        reference_id=REFERENCE_ID,
        model=TTS_MODEL,
        latency="balanced",
    )
    print("Fish returned iterator")
    proc = subprocess.Popen(
        [
            MPV_PATH,
            "--no-terminal",
            "--no-cache",
            "-",
        ],
        stdin=subprocess.PIPE,
    )

    first_chunk = True

    try:
        for chunk in audio_stream:
            print("First audio")
            if not chunk:
                continue

            if first_chunk:
                print(
                    f"[SERVER] First audio chunk @ {time.perf_counter():.6f}"
                )
                first_chunk = False

            proc.stdin.write(chunk)
            proc.stdin.flush()

    finally:
        if proc.stdin:
            proc.stdin.close()

        proc.wait()


if __name__ == "__main__":

    def demo_chunks():
        yield "Hey, "
        yield "this is "
        yield "streaming audio!"

    stream_audio(demo_chunks())
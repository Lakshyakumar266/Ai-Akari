import os
import threading
from dotenv import load_dotenv
import sounddevice as sd
import numpy as np
from faster_whisper import WhisperModel

load_dotenv()

MODEL_CACHE_DIR = "E:/HuggingFace_Cache/faster-whisper"

model = WhisperModel(
    "medium", device="cpu", compute_type="int8", download_root=MODEL_CACHE_DIR
)

SAMPLE_RATE = 16000
BLOCK_DURATION = 0.02  # 20 ms (better responsiveness)
SILENCE_HANG_TIME = 1.5  # Stop after 0.8 s of silence
MAX_RECORD_SECONDS = 15  # Voice commands rarely exceed this
CALIBRATION_SECONDS = 1.0  # Better ambient noise estimation
THRESHOLD_MULTIPLIER = 2.5  # Less likely to trigger on background noise
STOP_THRESHOLD_RATIO = 0.65  # More forgiving while speaking


def calibrate_silence_threshold(stop_event: threading.Event | None = None) -> float:
    """Measures ambient noise for a moment to set a threshold relative to the room, not a fixed guess."""
    block_size = int(SAMPLE_RATE * BLOCK_DURATION)
    num_blocks = int(CALIBRATION_SECONDS / BLOCK_DURATION)

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32") as stream:
        levels = []
        for _ in range(num_blocks):
            if stop_event and stop_event.is_set():
                return 0.005
            block, _ = stream.read(block_size)
            levels.append(np.sqrt(np.mean(block.flatten() ** 2)))

    ambient_rms = float(np.mean(levels)) if levels else 0.005
    threshold = max(ambient_rms * THRESHOLD_MULTIPLIER, 0.005)
    print(f"[calibration] ambient rms={ambient_rms:.5f}, threshold={threshold:.5f}")
    return threshold


def listen_and_capture(stop_event: threading.Event | None = None) -> np.ndarray:
    if stop_event and stop_event.is_set():
        return np.array([], dtype="float32")
    start_threshold = calibrate_silence_threshold(stop_event)
    if stop_event and stop_event.is_set():
        return np.array([], dtype="float32")
    stop_threshold = (
        start_threshold * STOP_THRESHOLD_RATIO
    )  # lower bar once already talking
    print("Speak now...")

    block_size = int(SAMPLE_RATE * BLOCK_DURATION)
    silence_blocks_needed = int(SILENCE_HANG_TIME / BLOCK_DURATION)
    max_blocks = int(MAX_RECORD_SECONDS / BLOCK_DURATION)

    chunks = []
    speech_started = False
    silence_count = 0

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32") as stream:
        for _ in range(max_blocks):
            if stop_event and stop_event.is_set():
                return np.array([], dtype="float32")
            block, _ = stream.read(block_size)
            block = block.flatten()
            rms = np.sqrt(np.mean(block**2))

            active_threshold = stop_threshold if speech_started else start_threshold

            if rms > active_threshold:
                speech_started = True
                silence_count = 0
                chunks.append(block)
            elif speech_started:
                silence_count += 1
                chunks.append(block)
                if silence_count >= silence_blocks_needed:
                    break

    if not chunks:
        print("[warning] no speech detected before timeout")
        return np.array([], dtype="float32")

    if silence_count > 0:
        chunks = chunks[:-silence_count]

    captured_seconds = len(chunks) * BLOCK_DURATION
    print(f"[info] captured {captured_seconds:.1f}s of audio")
    return np.concatenate(chunks)


def transcribe_audio(audio: np.ndarray) -> str:
    if audio.size == 0:
        return ""
    segments, info = model.transcribe(
        audio,
        language="en",
        beam_size=1,
        best_of=1,
        temperature=0,
        condition_on_previous_text=False,
        vad_filter=False,
        without_timestamps=True,
        word_timestamps=False,
        compression_ratio_threshold=2.4,
        log_prob_threshold=-1.0,
        no_speech_threshold=0.6,
        repetition_penalty=1.05,
        hallucination_silence_threshold=2.0,
    )
    return " ".join(segment.text.strip() for segment in segments)


if __name__ == "__main__":
    audio = listen_and_capture()
    print(transcribe_audio(audio))

import os

from dotenv import load_dotenv
from fishaudio import FishAudio

load_dotenv()

client = FishAudio(
    api_key=os.getenv("FISH_AUDIO_API_KEY")
)

REFERENCE_ID = os.getenv("FISH_AUDIO_REFERENCE_ID")

stream = client.tts.stream_websocket(
    ["Hello from Akari."],
    reference_id=REFERENCE_ID,
    model="s2.1-pro-free",
)

chunk = next(stream)

print(type(chunk))
print(len(chunk))
print(chunk[:32].hex())
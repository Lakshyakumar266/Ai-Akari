# Anime Wifu Companion

A local, two-part anime companion that brings **Akari Watanabe** (*More Than a Married Couple, But Not Lovers*) to life:

- **`client/`** — a 3D web viewer that renders a VRM model of Akari in the browser (React + Three.js). The character blinks, breathes, follows your camera, and can play animations and facial expressions.
- **`server/`** — a voice-in / voice-out loop. Your speech is transcribed on-device, replies are streamed from Mistral with an Akari persona, and Fish Audio speaks them back through mpv.

The two halves are independent today: the client is a self-contained VRM scene, and the server is a microphone-driven CLI companion. A full voice → 3D avatar pipeline is a natural next step.

## Repository layout

```
AkariWattnabe-companion/
├── client/              # 3D VRM character viewer (React + Vite + Three.js)
│   ├── public/
│   │   ├── character.vrm         # Akari model
│   │   └── animations/           # .vrma clips (Blush, Jump, Sad, ...)
│   └── src/components/character/ # controllers: animation, blink, emotion, lip-sync...
└── server/              # Voice companion (Python)
    ├── src/
    │   ├── main.py               # Voice loop entry point
    │   ├── asr/voice_to_text.py  # Mic + faster-whisper
    │   ├── llm/mistral_model.py  # Mistral streaming chat
    │   ├── tts/text_to_speech.py # Fish Audio + mpv playback
    │   └── prompts/system_prompt_akari.py
    ├── bin/mpv-windows/          # Bundled mpv for audio playback (Windows)
    └── pyproject.toml
```

## Getting started

### Client (3D viewer)

Requires [Bun](https://bun.sh/) (or npm).

```bash
cd client
bun install
bun run dev        # http://localhost:5173
```

Scripts: `bun run dev`, `bun run build`, `bun run lint` (oxlint), `bun run preview`.

### Server (voice companion)

Requires **Python 3.11+**, [uv](https://docs.astral.sh/uv/), a microphone, speakers, and mpv on Windows. See [`server/README.md`](server/README.md) for full setup and API-key instructions.

```bash
cd server
uv sync
# create .env from .env.example with your Mistral + Fish Audio keys
uv run src/main.py
```

## Features

- On-device speech-to-text with ambient-noise calibration and silence-based end-of-utterance detection
- In-character chat with Mistral, streamed token by token
- Low-latency TTS via Fish Audio's WebSocket API, piped to bundled mpv
- 3D VRM character with idle motion (blink, breathing, look-at), playable `.vrma` animations, and blendable facial expressions

## License

See repository metadata and third-party licenses for Mistral, Fish Audio, faster-whisper, mpv, and @pixiv/three-vrm.

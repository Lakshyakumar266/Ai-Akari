# AiAkari Assistant

A local, two-part AI assistant that brings **Akari Watanabe** (*More Than a Married Couple, But Not Lovers*) to life:

- **`client/`** — a 3D web viewer that renders a VRM model of Akari in the browser (React + Three.js). The character blinks, breathes, follows your camera, and can play animations and facial expressions.
- **`server/`** — a voice-in / voice-out loop. Your speech is transcribed on-device, replies are streamed from Mistral with an Akari persona, and Fish Audio speaks them back through mpv.

The two halves are independent today: the client is a self-contained VRM scene, and the server is a microphone-driven CLI . A full voice → 3D avatar pipeline is a natural next step.

## Repository layout

```
AkariWattnabe/
├── client/              # 3D VRM character viewer (React + Vite + Three.js)
│   ├── public/
│   │   ├── character.vrm         # Akari model
│   │   └── animations/           # .vrma clips (Blush, Jump, Sad, ...)
│   └── src/components/character/ # controllers: animation, blink, emotion, lip-sync...
└── server/              # Voice assistant (Python)
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

### Server (voice assistant)

Requires **Python 3.11+**, [uv](https://docs.astral.sh/uv/), a microphone, speakers, and mpv on Windows. See [`server/README.md`](server/README.md) for full setup and API-key instructions.

```bash
cd server
uv sync
# create .env from .env.example with your Mistral + Fish Audio keys
uv run python -m src.main
```

## Features

- **Multi-Character Companion Support**: Interactive 3D avatars including **Akari Watanabe** and **Espeon** with idle motion (blinking, breathing, camera tracking), playable `.vrma` animations, and blendable facial expressions.
- **Pluggable LLM Inference Providers**: Dynamic runtime switching between foundation model providers:
  - **AWS Bedrock Mantle**: Ministral 3 (8B/14B), Mistral Large 3, OpenAI GPT-OSS (120B/20B), Google Gemma 3 (1B–27B), and Qwen 3 (VL 8B–235B).
  - **OpenAI**: GPT-4o, GPT-4o Mini, GPT-4 Turbo.
  - **OpenRouter (Free Tier)**: Multi-model auto router, Google Gemma 4 (Free, with native tool calling), Ling 3.0 Flash, Liquid LFM, and Space Bunny.
  - **Free.ai Gateway**: Qwen 2.5 7B and Qwen 3 8B.
  - **Mistral AI**: Ministral 8B, Pixtral 12B, and Mistral Small.
- **Built-in Tool Calling & Function Execution**:
  - Up to 20 multi-turn tool execution rounds per window with automated pre-decline catalog inspection
  - Dynamic tool discovery (`get_available_tools` / `get_tool_list`)
  - Live DuckDuckGo & Tavily Web Search and direct web page reading
  - System Analytics (CPU, memory, storage telemetry)
  - Timezone-aware Clock, World Time, and Calendar tools
  - Math & calculation evaluation
- **Multimodal Vision & Image Input**:
  - Native multimodal image understanding for supported models (Ministral 3, Qwen 3 VL, OpenAI GPT-4o, GPT-6 Luna, GPT-5.5)
  - Automated background visual feature extraction for text-only foundation models
- **Full-Duplex WebSocket Streaming Architecture**:
  - Binary audio streaming for real-time live Whisper transcription (int16 PCM)
  - Live token streaming, real-time emotion classification, and audio-reactive 3D lip sync

## License

This project is licensed under the **GNU General Public License v3.0 (GPL-3.0)**. See [LICENSE](LICENSE) for the full text.

Third-party components (Mistral, Fish Audio, faster-whisper, mpv, @pixiv/three-vrm) are licensed separately under their own terms.

# Anime Wife Companion

A local voice companion that lets you talk with **Akari Watanabe** (*More Than a Married Couple, But Not Lovers*). Your speech is transcribed on-device, replies are streamed from Mistral with a character system prompt, and Fish Audio speaks the response back—often before the full text is finished.

## Features

- **Voice-in, voice-out loop** — speak, listen, repeat until you say stop
- **On-device STT** — [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (`medium`, CPU) with ambient-noise calibration and silence-based end-of-utterance detection
- **In-character chat** — Mistral (`mistral-large-latest`) with a detailed Akari persona and conversation history
- **Streaming TTS** — Fish Audio WebSocket streaming piped to bundled [mpv](https://mpv.io/) on Windows for low-latency playback

## Requirements

- **Python** 3.11+
- **[uv](https://docs.astral.sh/uv/)** (recommended) or another way to install dependencies from `pyproject.toml`
- **Microphone** and speakers/headphones
- **Windows** — playback uses `bin/mpv-windows/mpv.exe` (other platforms would need mpv on `PATH` or a code change)
- API keys:
  - [Mistral AI](https://console.mistral.ai/) — chat
  - [Fish Audio](https://fish.audio/) — text-to-speech (voice reference is configured in `src/text_to_speech.py`)

## Setup

1. Clone the repository and enter the project directory.

2. Install dependencies:

   ```bash
   uv sync
   ```

3. Create a `.env` file in the project root (see `.gitignore`; do not commit it):

   ```env
   MISTRAL_API_KEY=your_mistral_api_key
   FISH_AUDIO_API_KEY=your_fish_audio_api_key
   ```

4. On first run, faster-whisper will download the `medium` model (~1.5 GB).

## Usage

From the project root:

```bash
uv run src/main.py
```

You should see `Akari companion is live. Say 'stop' to exit.` After calibration, **Speak now...** means the app is listening. Replies print as `Akari:` and play through mpv.

**Exit:** say **stop**, **exit**, **goodbye**, or **quit**, or press `Ctrl+C`.

## How it works

```mermaid
flowchart LR
  Mic[Microphone] --> VAD[Listen and capture]
  VAD --> STT[faster-whisper]
  STT --> LLM[Mistral stream]
  LLM --> TTS[Fish Audio stream]
  TTS --> MPV[mpv playback]
```

| Step | Module | Notes |
|------|--------|--------|
| Capture | `src/voice_to_text.py` | 16 kHz mono, ~0.8 s silence ends recording |
| Transcribe | `src/voice_to_text.py` | English, optimized for short utterances |
| Reply | `src/model.py` | System prompt + history, token streaming |
| Speak | `src/text_to_speech.py` | Chunks from the LLM stream into Fish Audio |

Persona and exit phrases live in `src/prompts/system_prompt_akari.py`.

## Project layout

```
AkariWattnabe-companion/
├── bin/mpv-windows/     # mpv for streaming audio (Windows)
├── src/
│   ├── main.py          # Voice loop entry point
│   ├── model.py         # Mistral client
│   ├── voice_to_text.py # Mic + Whisper
│   ├── text_to_speech.py# Fish Audio + mpv
│   └── prompts/
│       └── system_prompt_akari.py
├── pyproject.toml
└── .env                 # Your API keys (local only)
```

## Optional: run modules alone

From the project root (each script adds `src` to the import path when run as `src/<module>.py`):

```bash
uv run src/voice_to_text.py    # Record once and print transcription
uv run src/model.py            # Stream a test chat line
uv run src/text_to_speech.py   # Demo streaming TTS
```

## License

See repository metadata and third-party licenses for Mistral, Fish Audio, faster-whisper, and mpv.

# GPT-SoVITS Integration & Dynamic TTS Voice Pipeline Architecture

**Status**: Active  
**Date**: 2026-09-29  
**Components**: `./server/src/tts/sovits_client.py`, `./server/src/tts/text_to_speech.py`, `./server/src/bridge/websocket_server.py`, `./client/src/components/screens/OverviewScreen.tsx`, `./client/src/components/screens/OverviewScreen.css`, `./client/src/components/screens/SettingsScreen.tsx`, `./client/src/components/screens/SettingsScreen.css`, `./client/src/networking/AvatarSocket.ts`, `./client/src/networking/types.ts`

---

## 1. Executive Summary

This document specifies the integration of **GPT-SoVITS** as an alternative high-fidelity voice synthesis pipeline alongside **Fish Audio**, with dynamic runtime selection directly from the UI.

Users can:
1. Select their active voice pipeline (**Fish Audio** vs **GPT-SoVITS**) directly from `screen=characters` under the **Voice** tab, as well as in **Settings**.
2. Configure their public or local GPT-SoVITS server connection URL through the UI, stored locally in `localStorage` (`akari_gpt_sovits_url`) and synchronized in real time to the Python backend session.
3. Automatically route conversational speech chunks in both **Chat Mode** (`./server/src/chat/loop.py`) and **Voice/Stream Mode** (`./server/src/voice/loop.py`) to the active engine, producing raw WAV audio for lip-synced playback in the browser.

---

## 2. GPT-SoVITS REST API Protocol

### 2.1 Endpoint Normalization
GPT-SoVITS instances (running `api.py` or `api_v2.py`) expose a `/tts` endpoint. The client normalizes user input:
- Input: `https://sovits.example.com` or `http://127.0.0.1:9880`
- Normalized Target: `{base_url}/tts`

### 2.2 Payload Structure & Cross-Version Aliases
`api_v2.py` strictly validates `check_params` (`ref_audio_path`, `text_lang`, `prompt_lang`, `text`), while `api.py` (v1) uses `refer_wav_path`, `text_language`, `prompt_language`. The client sends dual aliases for total compatibility:
```json
{
  "text": "Hello, darling! What are you doing today?",
  "text_lang": "auto",
  "text_language": "auto",
  "ref_audio_path": "ref.wav",
  "refer_wav_path": "ref.wav",
  "prompt_text": "Sample voice prompt transcript",
  "prompt_lang": "en",
  "prompt_language": "en",
  "top_k": 15,
  "top_p": 1.0,
  "temperature": 1.0,
  "text_split_method": "cut5",
  "batch_size": 1,
  "speed_factor": 1.0,
  "media_type": "wav",
  "streaming_mode": false,
  "parallel_infer": true,
  "repetition_penalty": 1.35,
  "sample_steps": 32
}
```
- **Language Codes**: `"auto"`, `"en"`, `"zh"`, `"ja"`, `"ko"`, `"yue"`.
- **Response**: Binary `audio/wav` audio stream (status 200).
- **Diagnostics**: Status 400 JSON is parsed and surfaced directly to help resolve missing reference audio or model mismatches.

---

## 3. Dynamic Server Synchronization

### 3.1 WebSocket Protocol Extension

#### Client to Server: `set_tts_engine`
```json
{
  "type": "set_tts_engine",
  "engine": "sovits"
}
```

#### Client to Server: `set_sovits_url`
```json
{
  "type": "set_sovits_url",
  "url": "https://sovits.example.com"
}
```

#### Client to Server: `set_sovits_params`
```json
{
  "type": "set_sovits_params",
  "ref_audio": "ref.wav",
  "prompt_text": "Voice reference transcript",
  "prompt_lang": "en",
  "text_lang": "auto"
}
```

#### Server to Client: `config` Broadcast
```json
{
  "type": "config",
  "tts_engine": "sovits",
  "sovits_url": "https://sovits.example.com",
  "sovits_url_configured": true,
  "available_tts_engines": ["fish", "sovits"]
}
```

---

## 4. UI/UX Design System

### 4.1 Character Overview Voice Tab (`screen=characters`)
1. **Pipeline Selector**: Segmented toggle between **Fish Audio** and **GPT-SoVITS**.
2. **Inline Server Connection Card**:
   - Monospace URL input field.
   - Status badge: Emerald `Connected` when configured, Amber `URL Needed` when empty.
   - Save & Connect button with checkmark state transition.
   - Clear button.
3. **Fish Audio Info Box**: Displays active cloud preset (`s2.1-pro-free`).

### 4.2 Application Settings Screen (`screen=settings`)
1. **Dedicated Voice & Audio Pipeline Section**:
   - Card-based selector for Fish Audio (Cloud Fast) vs GPT-SoVITS (Self-Hosted).
   - Public Server Connection URL card with input, show/hide, save, test, and clear buttons.
   - Local storage privacy assurance.

---

## 5. Fault Tolerance & Strict Engine Isolation

1. **Strict Engine Isolation (No Unintended Fallbacks)**: When GPT-SoVITS is selected, it does **not** silently fall back to Fish Audio. If GPT-SoVITS fails or errors, it logs clear diagnostics and raises the error so the user has full transparency over what occurred.
2. **Tunnel Bypass Headers**: Requests automatically send `ngrok-skip-browser-warning: 1` and `Bypass-Tunnel-Reminder: 1` so remote servers exposed via ngrok or localtunnel don't return HTML interstitials instead of WAV bytes.
3. **WebUI (`webui.py`) vs API Server (`api_v2.py`) Distinction**:
   - `webui.py` (port 9874) is the Gradio frontend for training and data slicing. It does **not** expose the `/tts` endpoint and returns `404 Not Found`.
   - `api_v2.py` (port 9880) is the dedicated FastAPI REST server hosting `/tts`.
   - If a `*.gradio.live` or Gradio 404 is detected, `sovits_client.py` logs explicit instructions to start `api_v2.py` on port 9880.
4. **No Third-Party Telemetry**: Connection URLs and audio streams are handled strictly between the browser and the user's configured server.

"""
GPT-SoVITS Client for Text-to-Speech synthesis.
Supports both:
1. Standard FastAPI REST instances (api.py / api_v2.py via /tts or /)
2. Gradio WebUI instances (inference_webui.py via gradio_client /inference)
"""
from __future__ import annotations

import os
from typing import Optional
from dotenv import load_dotenv
import requests

load_dotenv()

_runtime_sovits_url: Optional[str] = None
_ref_audio_path: str = os.getenv("GPT_SOVITS_REF_AUDIO", "")
_prompt_text: str = os.getenv("GPT_SOVITS_PROMPT_TEXT", "")
_prompt_lang: str = os.getenv("GPT_SOVITS_PROMPT_LANG", "en")
_text_lang: str = os.getenv("GPT_SOVITS_TEXT_LANG", "auto")
_speed_factor: float = 1.0

_cached_gradio_client: Optional[tuple[str, any]] = None

_CLIENT_HEADERS = {
    "User-Agent": "Akari-Companion/1.0",
    "ngrok-skip-browser-warning": "true",
    "Bypass-Tunnel-Reminder": "true",
}


def normalize_endpoint(url: str) -> str:
    """Normalizes a user-provided GPT-SoVITS URL into a valid /tts endpoint."""
    cleaned = (url or "").strip().rstrip("/")
    if not cleaned:
        return ""
    if cleaned.endswith("/tts"):
        return cleaned
    return f"{cleaned}/tts"


def set_sovits_url(url: str) -> None:
    """Configures the runtime GPT-SoVITS connection URL."""
    global _runtime_sovits_url, _cached_gradio_client
    cleaned = (url or "").strip()
    _cached_gradio_client = None  # Reset client cache on URL change
    if cleaned:
        _runtime_sovits_url = cleaned
        os.environ["GPT_SOVITS_URL"] = cleaned
        print(f"[GPT-SoVITS] Connection URL updated: {cleaned}")
    else:
        _runtime_sovits_url = None
        os.environ.pop("GPT_SOVITS_URL", None)
        print("[GPT-SoVITS] Connection URL cleared.")


def get_sovits_url() -> str:
    """Returns the active GPT-SoVITS connection URL."""
    return (
        _runtime_sovits_url
        or os.getenv("GPT_SOVITS_URL")
        or os.getenv("SOVITS_URL")
        or ""
    )


def has_sovits_url() -> bool:
    """Checks whether a valid GPT-SoVITS URL is configured."""
    return bool(get_sovits_url())


def get_sovits_params() -> dict:
    """Returns the currently active GPT-SoVITS reference audio and language parameters."""
    return {
        "ref_audio": _ref_audio_path,
        "prompt_text": _prompt_text,
        "prompt_lang": _prompt_lang,
        "text_lang": _text_lang,
        "speed": _speed_factor,
    }


def set_sovits_params(
    ref_audio: Optional[str] = None,
    prompt_text: Optional[str] = None,
    prompt_lang: Optional[str] = None,
    text_lang: Optional[str] = None,
    speed: Optional[float] = None,
) -> None:
    """Updates optional and required synthesis parameters for GPT-SoVITS."""
    global _ref_audio_path, _prompt_text, _prompt_lang, _text_lang, _speed_factor
    if ref_audio is not None:
        _ref_audio_path = ref_audio.strip()
    if prompt_text is not None:
        _prompt_text = prompt_text.strip()
    if prompt_lang is not None and prompt_lang.strip():
        _prompt_lang = prompt_lang.strip().lower()
    if text_lang is not None and text_lang.strip():
        _text_lang = text_lang.strip().lower()
    if speed is not None and speed > 0:
        _speed_factor = speed
    print(
        f"[GPT-SoVITS] Params updated: ref_audio='{_ref_audio_path}', "
        f"prompt_lang='{_prompt_lang}', text_lang='{_text_lang}'"
    )


def _map_lang_to_gradio(code: str) -> str:
    """Maps shorthand language codes to Gradio inference choices."""
    c = (code or "").lower().strip()
    if c in ("en", "english"):
        return "English"
    if c in ("ja", "jp", "japanese"):
        return "Japanese"
    if c in ("zh", "cn", "chinese"):
        return "Chinese"
    if c in ("ko", "korean"):
        return "Korean"
    if c in ("yue", "cantonese"):
        return "Yue"
    if "mix" in c or c == "auto":
        return "English"
    return "English"


def _get_gradio_client(base_url: str):
    """Retrieves or creates a cached Gradio client for the given URL."""
    global _cached_gradio_client
    clean = base_url.strip().rstrip("/")
    if clean.endswith("/tts"):
        clean = clean[:-4].rstrip("/")

    if _cached_gradio_client and _cached_gradio_client[0] == clean:
        return _cached_gradio_client[1]

    try:
        from gradio_client import Client
        print(f"[GPT-SoVITS] Connecting Gradio client to {clean}...")
        client = Client(clean)
        _cached_gradio_client = (clean, client)
        return client
    except Exception as e:
        print(f"[GPT-SoVITS] Gradio connection failed: {e}")
        return None


def _synthesize_gradio(base_url: str, text: str) -> bytes:
    """Synthesizes speech using the Gradio inference_webui.py /inference endpoint."""
    client = _get_gradio_client(base_url)
    if client is None:
        raise RuntimeError(f"Unable to connect to Gradio WebUI at {base_url}")

    t_lang = _map_lang_to_gradio(_text_lang)
    p_lang = _map_lang_to_gradio(_prompt_lang)

    print(f"[GPT-SoVITS] Calling Gradio /inference (lang={t_lang}, len={len(text)})...")
    res = client.predict(
        text=text,
        text_lang=t_lang,
        ref_audio_path=_ref_audio_path or None,
        aux_ref_audio_paths=[],
        prompt_text=_prompt_text or "",
        prompt_lang=p_lang,
        top_k=15,
        top_p=1.0,
        temperature=1.0,
        text_split_method="Slice once every 4 sentences",
        batch_size=20,
        speed_factor=_speed_factor,
        ref_text_free=False if _ref_audio_path else True,
        split_bucket=True,
        fragment_interval=0.3,
        seed=-1,
        keep_random=True,
        parallel_infer=True,
        repetition_penalty=1.35,
        sample_steps=32,
        super_sampling=False,
        api_name="/inference",
    )

    audio_path = res[0] if isinstance(res, (list, tuple)) else res
    if not audio_path or not os.path.exists(audio_path):
        raise ValueError(f"Gradio inference returned empty or missing audio file: {audio_path}")

    with open(audio_path, "rb") as f:
        wav_bytes = f.read()

    print(f"[GPT-SoVITS] Gradio synthesized {len(wav_bytes)} bytes of WAV audio.")
    return wav_bytes


def _synthesize_rest(endpoint: str, text: str, timeout: float = 45.0) -> bytes:
    """
    Synthesizes speech using the standard FastAPI api_v2.py / api.py /tts endpoint.
    Includes full parameter compatibility across api_v2.py and api.py.
    """
    t_lang = (_text_lang or "auto").strip().lower()
    p_lang = (_prompt_lang or "en").strip().lower()

    payload: dict = {
        "text": text,
        "text_lang": t_lang,
        "text_language": t_lang,
        "ref_audio_path": _ref_audio_path or "",
        "refer_wav_path": _ref_audio_path or "",
        "prompt_text": _prompt_text or "",
        "prompt_lang": p_lang,
        "prompt_language": p_lang,
        "top_k": 15,
        "top_p": 1.0,
        "temperature": 1.0,
        "text_split_method": "cut5",
        "batch_size": 1,
        "speed_factor": _speed_factor,
        "media_type": "wav",
        "streaming_mode": False,
        "parallel_infer": True,
        "repetition_penalty": 1.35,
        "sample_steps": 32,
    }

    # Standard GPT-SoVITS api_v2.py / api.py accepts POST with JSON body
    response = requests.post(endpoint, json=payload, headers=_CLIENT_HEADERS, timeout=timeout)

    # Fallback to GET query params if POST is not permitted (e.g. 405 Method Not Allowed)
    if response.status_code == 405:
        print("[GPT-SoVITS] POST returned 405; retrying via GET...")
        response = requests.get(endpoint, params=payload, headers=_CLIENT_HEADERS, timeout=timeout)

    # Handle 400 Bad Request with actionable diagnostics
    if response.status_code == 400:
        err_msg = ""
        try:
            err_msg = response.json().get("message", response.text)
        except Exception:
            err_msg = response.text
        print(f"[GPT-SoVITS] HTTP 400 Bad Request: {err_msg}")
        if "ref_audio_path is required" in err_msg:
            raise RuntimeError(
                "GPT-SoVITS requires a reference audio file path on the server (ref_audio_path). "
                "Please configure the Reference Audio Path in Settings -> GPT-SoVITS Configuration (e.g. 'ref.wav')."
            )
        raise RuntimeError(f"GPT-SoVITS 400: {err_msg}")

    response.raise_for_status()

    wav_bytes = response.content
    if not wav_bytes:
        raise ValueError("GPT-SoVITS returned empty audio response.")

    if wav_bytes.startswith(b"<!DOCTYPE") or wav_bytes.startswith(b"<html"):
        raise ValueError(
            f"GPT-SoVITS endpoint returned HTML instead of audio: {wav_bytes[:120].decode('utf-8', errors='ignore')}"
        )

    print(f"[GPT-SoVITS] REST API synthesized {len(wav_bytes)} bytes of WAV audio.")
    return wav_bytes


def convert_to_wav(text: str, timeout: float = 45.0) -> bytes:
    """
    Synthesizes speech for the provided text using the configured GPT-SoVITS server.
    Seamlessly supports both Gradio WebUI instances and FastAPI REST api_v2 instances.
    """
    base_url = get_sovits_url()
    if not base_url:
        raise ValueError(
            "GPT-SoVITS connection URL is not configured. "
            "Please provide a public or local server URL in Settings or the Voice tab."
        )

    is_gradio = "gradio.live" in base_url or base_url.endswith(".live")

    # If the URL is identified as Gradio, try Gradio client first
    if is_gradio:
        try:
            return _synthesize_gradio(base_url, text)
        except Exception as e:
            print(f"[GPT-SoVITS] Gradio synthesis failed ({e}), attempting REST fallback...")

    # Standard REST API attempt
    endpoint = normalize_endpoint(base_url)
    try:
        return _synthesize_rest(endpoint, text, timeout=timeout)
    except requests.exceptions.HTTPError as err:
        if err.response.status_code == 404 and not is_gradio:
            try:
                print("[GPT-SoVITS] REST /tts returned 404; checking if instance is a Gradio WebUI...")
                return _synthesize_gradio(base_url, text)
            except Exception as ge:
                print(f"[GPT-SoVITS] Gradio check also failed: {ge}")

        print(f"[GPT-SoVITS] HTTP error: {err}")
        raise RuntimeError(f"GPT-SoVITS request failed: {err}") from err
    except requests.exceptions.RequestException as err:
        print(f"[GPT-SoVITS] HTTP connection error: {err}")
        raise RuntimeError(f"GPT-SoVITS request failed: {err}") from err

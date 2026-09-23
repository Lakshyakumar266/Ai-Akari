"""
Emotion Feature Module
----------------------
Manages character emotion tag parsing, text cleaning, and shiftable dispatching.

Modes (configured via `src.config.EMOTION_SYNC_MODE`):
- "synced": Facial expressions synchronize per dialogue segment with audio playback.
- "stream": Legacy mode — dispatches emotion tags immediately as LLM tokens stream in.
- "off": Disables emotion processing entirely.
"""

import re
from typing import Callable, Optional
from src.config import EMOTION_SYNC_MODE
from src.bridge.events import emotion

# Matches any of the 6 valid emotion tags anywhere in dialogue text
EMOTION_TAG_PATTERN = re.compile(
    r"\[(happy|sad|angry|surprised|relaxed|neutral)\]",
    re.IGNORECASE,
)

VALID_EMOTIONS = {"Happy", "Sad", "Angry", "Surprised", "Relaxed", "Neutral"}


def strip_all_emotion_tags(text: str) -> str:
    """Removes all emotion brackets from text so TTS does not speak them."""
    return EMOTION_TAG_PATTERN.sub("", text).strip()


def extract_dialogue_and_emotion(raw_text: str) -> tuple[str, Optional[str]]:
    """
    Parses dialogue text.
    Returns:
        tuple of (clean_spoken_text, capitalized_emotion_name or None)
    """
    matches = list(EMOTION_TAG_PATTERN.finditer(raw_text))
    detected_emotion = None

    if matches:
        raw_name = matches[0].group(1).capitalize()
        if raw_name in VALID_EMOTIONS:
            detected_emotion = raw_name

    clean_text = strip_all_emotion_tags(raw_text)
    return clean_text, detected_emotion


def split_dialogue_units_with_emotions(
    raw_text: str, max_words: int = 16
) -> list[tuple[str, str]]:
    """
    Parses dialogue text containing emotion tags anywhere in the text.
    Splits the text into 1-2 line visual dialogue units (max_words) and associates
    each unit with the active emotion at that point in the dialogue.

    Returns:
        list of (clean_unit_text, emotion_name) tuples
    """
    # Split raw_text by emotion tag matches while retaining the tags
    tokens = re.split(
        r"(\[(?:happy|sad|angry|surprised|relaxed|neutral)\])",
        raw_text,
        flags=re.IGNORECASE,
    )

    current_emotion = "Neutral"
    sections: list[tuple[str, str]] = []  # (text_chunk, emotion)

    for token in tokens:
        if not token:
            continue
        tag_match = EMOTION_TAG_PATTERN.fullmatch(token.strip())
        if tag_match:
            tag_name = tag_match.group(1).capitalize()
            if tag_name in VALID_EMOTIONS:
                current_emotion = tag_name
        else:
            text = token.strip()
            if text:
                sections.append((text, current_emotion))

    if not sections:
        clean = strip_all_emotion_tags(raw_text)
        return [(clean, "Neutral")] if clean else []

    dialogue_units: list[tuple[str, str]] = []

    for text, section_emotion in sections:
        sentences = re.split(r"(?<=[.!?\n])\s+", text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if not sentences:
            sentences = [text]

        current_unit = []
        current_word_count = 0

        for s in sentences:
            s_words = len(s.split())
            if current_unit and (current_word_count + s_words > max_words):
                dialogue_units.append((" ".join(current_unit), section_emotion))
                current_unit = [s]
                current_word_count = s_words
            else:
                current_unit.append(s)
                current_word_count += s_words

        if current_unit:
            dialogue_units.append((" ".join(current_unit), section_emotion))

    return dialogue_units


class EmotionFeatureManager:
    """
    Decoupled, shiftable manager for emotion dispatching.
    Allows toggling between synced mode and legacy stream mode anytime.
    """

    def __init__(self, mode: Optional[str] = None):
        self.mode = mode or EMOTION_SYNC_MODE
        self.detected_emotion: Optional[str] = None

    def on_token(self, token: str, buffer: str, dispatch_fn: Callable) -> str:
        """
        Called during LLM streaming.
        In 'stream' mode, immediately dispatches emotion tags as they arrive (legacy).
        In 'synced' mode, stores detected emotion for synchronized playback dispatch.
        Returns the updated buffer after stripping matched tags.
        """
        if self.mode == "off":
            return EMOTION_TAG_PATTERN.sub("", buffer)

        matches = list(EMOTION_TAG_PATTERN.finditer(buffer))
        if matches:
            for match in matches:
                tag_emotion = match.group(1).capitalize()
                if tag_emotion in VALID_EMOTIONS:
                    self.detected_emotion = tag_emotion
                    if self.mode == "stream":
                        print(f"\n[Akari Emotion Tag - Stream Mode] {tag_emotion}")
                        dispatch_fn(emotion(tag_emotion))

            buffer = EMOTION_TAG_PATTERN.sub("", buffer)

        return buffer

    def on_speech_start(self, dispatch_fn: Callable):
        """
        Called when speech segments are ready to be dispatched to the browser.
        In 'synced' mode, triggers the initial emotion at the start of speech.
        """
        if self.mode == "synced" and self.detected_emotion:
            print(f"\n[Akari Emotion - Synced Mode] Activating {self.detected_emotion} with speech start")
            dispatch_fn(emotion(self.detected_emotion))

    def on_speech_concluded(self, dispatch_fn: Callable):
        """
        Called after speech_segment loop on the server.
        In 'stream' mode (legacy), immediately sends Neutral.
        In 'synced' mode, does NOT send premature Neutral (the client resets on physical audio finish).
        """
        if self.mode == "stream":
            print("\n[Akari Emotion - Stream Mode] Resetting to Neutral on server")
            dispatch_fn(emotion("Neutral"))

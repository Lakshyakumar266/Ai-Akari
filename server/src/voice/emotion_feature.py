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

# Matches any bracketed emotion tag or word, e.g. [happy], [annoyed], [blush], [sigh]
EMOTION_TAG_PATTERN = re.compile(
    r"\[([a-zA-Z_\-]+)\]",
    re.IGNORECASE,
)

VALID_EMOTIONS = {"Happy", "Sad", "Angry", "Surprised", "Relaxed", "Neutral"}

# Comprehensive emotion aliases mapped to the 6 canonical VRM emotions (aligned with client EmotionController)
EMOTION_ALIASES: dict[str, str] = {
    # Exact 6 VRM emotions
    "neutral": "Neutral",
    "happy": "Happy",
    "sad": "Sad",
    "angry": "Angry",
    "relaxed": "Relaxed",
    "surprised": "Surprised",

    # Tsundere / expressive aliases
    "annoyed": "Angry",
    "mad": "Angry",
    "furious": "Angry",
    "pouting": "Angry",
    "irritated": "Angry",
    "grumpy": "Angry",

    "blush": "Happy",
    "flustered": "Happy",
    "smirk": "Happy",
    "teasing": "Happy",
    "joy": "Happy",
    "embarrassed": "Happy",
    "excited": "Happy",

    "shocked": "Surprised",
    "confused": "Surprised",
    "gasp": "Surprised",
    "amazed": "Surprised",

    "unhappy": "Sad",
    "crying": "Sad",
    "sulky": "Sad",
    "depressed": "Sad",
    "hurt": "Sad",

    "calm": "Relaxed",
    "sleepy": "Relaxed",
    "tired": "Relaxed",
}


# Matches JSON objects up to 2 levels of nesting containing function / tool parameters or results
NESTED_JSON_LEAK_PATTERN = re.compile(
    r'\{(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*\}',
    re.DOTALL
)

TOOL_CONTROL_TOKENS_PATTERN = re.compile(
    r'<\|?(?:tool_call|tool_response|thought)\|?>.*?<\|?/?(?:tool_call|tool_response|thought)\|?>',
    re.DOTALL
)


def strip_tool_leakage(text: str) -> str:
    """Strips leaked raw JSON tool call envelopes, results, or control tokens from spoken text."""
    if not text:
        return ""
    def replace_json(match):
        content = match.group(0)
        # Strip if it looks like a function call or tool response envelope
        if any(k in content for k in ('"function"', '"arguments"', '"time"', '"name"', '"parameters"', '"result"', '"call"')):
            return ""
        return content

    cleaned = NESTED_JSON_LEAK_PATTERN.sub(replace_json, text)
    cleaned = TOOL_CONTROL_TOKENS_PATTERN.sub("", cleaned)
    cleaned = re.sub(r"<\|?tool_call\|?>call:\w+\{.*?\}<tool_call\|?>", "", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"<\|?tool_response\|?>", "", cleaned)
    return cleaned


def resolve_emotion(tag_text: str) -> str:
    """Resolves any emotion tag or alias into one of the 6 canonical VRM emotions."""
    clean_tag = tag_text.strip().lower()
    return EMOTION_ALIASES.get(clean_tag, "Neutral")


def strip_all_emotion_tags(text: str) -> str:
    """Removes all emotion brackets, leaked tool JSON, and markdown formatting from text so TTS and subtitles are completely clean."""
    if not text:
        return ""
    # Strip any leaked toolcall JSON or control tags first
    cleaned = strip_tool_leakage(text)
    # Strip any [tag]
    cleaned = EMOTION_TAG_PATTERN.sub("", cleaned)
    # Strip Markdown asterisks for actions/emphasis e.g. *any* -> any, *sigh*
    cleaned = re.sub(r"\*+([^*]+)\*+", r"\1", cleaned)
    cleaned = cleaned.replace("*", "")
    return re.sub(r"\s+", " ", cleaned).strip()


def extract_dialogue_and_emotion(raw_text: str) -> tuple[str, Optional[str]]:
    """
    Parses dialogue text.
    Returns:
        tuple of (clean_spoken_text, capitalized_emotion_name or None)
    """
    cleaned_input = strip_tool_leakage(raw_text)
    matches = list(EMOTION_TAG_PATTERN.finditer(cleaned_input))
    detected_emotion = None

    if matches:
        raw_name = matches[0].group(1).lower()
        if raw_name in EMOTION_ALIASES:
            detected_emotion = EMOTION_ALIASES[raw_name]

    clean_text = strip_all_emotion_tags(cleaned_input)
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
    # Strip any leaked toolcall JSON before splitting into dialogue units
    cleaned_text = strip_tool_leakage(raw_text)

    # Split cleaned_text by emotion tag matches while retaining the tags
    tokens = re.split(
        r"(\[[a-zA-Z_\-]+\])",
        cleaned_text,
        flags=re.IGNORECASE,
    )

    current_emotion = "Neutral"
    sections: list[tuple[str, str]] = []  # (text_chunk, emotion)

    for token in tokens:
        if not token:
            continue
        tag_match = EMOTION_TAG_PATTERN.fullmatch(token.strip())
        if tag_match:
            tag_name = tag_match.group(1).lower()
            if tag_name in EMOTION_ALIASES:
                current_emotion = EMOTION_ALIASES[tag_name]
        else:
            text = strip_all_emotion_tags(token)
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
                tag_name = match.group(1).lower()
                if tag_name in EMOTION_ALIASES:
                    resolved = EMOTION_ALIASES[tag_name]
                    self.detected_emotion = resolved
                    if self.mode == "stream":
                        from src.bridge.events import emotion
                        # print(f"\n[Akari Emotion Tag - Stream Mode] {resolved} (from [{tag_name}])")
                        dispatch_fn(emotion(resolved))

            buffer = EMOTION_TAG_PATTERN.sub("", buffer)

        return buffer

    def on_speech_start(self, dispatch_fn: Callable):
        """
        Called when speech segments are ready to be dispatched to the browser.
        In 'synced' mode, triggers the initial emotion at the start of speech.
        """
        if self.mode == "synced" and self.detected_emotion:
            print(f"\n[Akari Emotion - Synced Mode] Activating {self.detected_emotion} with speech start")
            from src.bridge.events import emotion
            dispatch_fn(emotion(self.detected_emotion))

    def on_speech_concluded(self, dispatch_fn: Callable):
        """
        Called after speech_segment loop on the server.
        In 'stream' mode (legacy), immediately sends Neutral.
        In 'synced' mode, does NOT send premature Neutral (the client resets on physical audio finish).
        """
        if self.mode == "stream":
            print("\n[Akari Emotion - Stream Mode] Resetting to Neutral on server")
            from src.bridge.events import emotion
            dispatch_fn(emotion("Neutral"))

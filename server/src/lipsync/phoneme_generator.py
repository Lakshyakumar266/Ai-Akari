from __future__ import annotations

from phonemizer import phonemize
from phonemizer.separator import Separator


PHONE_SEPARATOR = "|"


IPA_TO_VISEME = {
    "aa": [
        "a", "ɑ", "æ", "ʌ", "ə", "ɐ"
    ],

    "ih": [
        "ɪ", "i", "e", "ɛ", "ɛɹ"
    ],

    "ee": [
        "iː", "eɪ"
    ],

    "oh": [
        "o", "oʊ", "ɔ", "ɔɹ"
    ],

    "ou": [
        "u", "ʊ", "uː"
    ]
}

def text_to_phonemes(text: str) -> list[str]:
    """
    Converts English text into a list of IPA phonemes.

    Example:
        "Hello there"

    Returns:
        [
            "h",
            "ə",
            "l",
            "oʊ",
            "ð",
            "ɛ",
            "ɹ",
        ]
    """

    ipa = phonemize(
        text,
        language="en-us",
        backend="espeak",
        strip=True,
        preserve_punctuation=False,
        with_stress=False,
        separator=Separator(
            phone=PHONE_SEPARATOR,
            word=" "
        ),
    )

    phones: list[str] = []

    for word in ipa.split():
        phones.extend(
            p
            for p in word.split(PHONE_SEPARATOR)
            if p
        )

    return phones


if __name__ == "__main__":
    print(text_to_phonemes("Hello there."))
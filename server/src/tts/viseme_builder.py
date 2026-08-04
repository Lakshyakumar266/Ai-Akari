from __future__ import annotations

from src.lipsync.phoneme_generator import (
    text_to_phonemes,
)

from src.lipsync.types import (
    VisemeFrame,
)

from src.lipsync.visemes import (
    phone_to_viseme,
)

from .stream_models import (
    WordAlignment,
)


def build_word_visemes(
    word: WordAlignment,
) -> list[VisemeFrame]:
    """
    Build visemes for ONE Fish-aligned word.

    Fish already tells us:

        start
        end

    We simply distribute the phonemes
    evenly across that interval.
    """

    phones = text_to_phonemes(
        word.text
    )

    if not phones:
        return []

    duration = (
        word.end - word.start
    )

    step = (
        duration / len(phones)
    )

    frames: list[
        VisemeFrame
    ] = []

    t = word.start

    for phone in phones:

        frames.append(
            VisemeFrame(
                t=t,
                viseme=phone_to_viseme(
                    phone
                ),
                weight=1.0,
            )
        )

        t += step

    return frames
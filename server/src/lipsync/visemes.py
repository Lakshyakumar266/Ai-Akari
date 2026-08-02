from __future__ import annotations

from .types import VisemeName


AA = {
    "a",
    "ɑ",
    "æ",
    "ʌ",
    "ə",
    "ɐ",
}

IH = {
    "ɪ",
    "ɛ",
    "ɛɹ",
}

EE = {
    "i",
    "iː",
    "e",
    "eɪ",
}

OH = {
    "o",
    "oʊ",
    "ɔ",
    "ɔɹ",
}

OU = {
    "u",
    "uː",
    "ʊ",
}


def phone_to_viseme(phone: str) -> VisemeName:
    """
    Convert an IPA phone into one
    of VRM's five mouth shapes.
    """

    phone = phone.strip()

    if phone in AA:
        return "aa"

    if phone in IH:
        return "ih"

    if phone in EE:
        return "ee"

    if phone in OH:
        return "oh"

    if phone in OU:
        return "ou"

    #
    # consonants
    #

    return "sil"



if __name__ == "__main__":
    tests = [
        "ə",
        "oʊ",
        "ɛɹ",
        "u",
        "b",
        "m",
        "s",
    ]

    for phone in tests:
        print(phone, "->", phone_to_viseme(phone))
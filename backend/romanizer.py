"""Transliteration and romanization utility for Indic scripts (Devanagari and Gurmukhi).

Converts Hindi (Devanagari) and Punjabi (Gurmukhi) text into clean, phonetic
Roman/Latin script (English alphabet).
"""

import re
from typing import Tuple

# Devanagari vowel letters (independent)
DEV_INDEPENDENT_VOWELS = {
    "अ": "a",
    "आ": "aa",
    "इ": "i",
    "ई": "ee",
    "उ": "u",
    "ऊ": "oo",
    "ऋ": "ri",
    "ए": "e",
    "ऐ": "ai",
    "ओ": "o",
    "औ": "au",
}

# Devanagari vowel signs (matras attached to consonants)
DEV_MATRAS = {
    "ा": "aa",
    "ि": "i",
    "ी": "ee",
    "ु": "u",
    "ू": "oo",
    "ृ": "ri",
    "े": "e",
    "ै": "ai",
    "ो": "o",
    "ौ": "au",
}

# Devanagari consonants (with inherent 'a' handled dynamically)
DEV_CONSONANTS = {
    "क": "k",
    "ख": "kh",
    "ग": "g",
    "घ": "gh",
    "ङ": "ng",
    "च": "ch",
    "छ": "chh",
    "ज": "j",
    "झ": "jh",
    "ञ": "ny",
    "ट": "t",
    "ठ": "th",
    "ड": "d",
    "ढ": "dh",
    "ण": "n",
    "त": "t",
    "थ": "th",
    "द": "d",
    "ध": "dh",
    "न": "n",
    "प": "p",
    "फ": "ph",
    "ब": "b",
    "भ": "bh",
    "म": "m",
    "य": "y",
    "र": "r",
    "ल": "l",
    "व": "v",
    "श": "sh",
    "ष": "sh",
    "स": "s",
    "ह": "h",
    # Nukta consonants
    "क़": "q",
    "ख़": "kh",
    "ग़": "gh",
    "ज़": "z",
    "ड़": "r",
    "ढ़": "rh",
    "फ़": "f",
}

# Gurmukhi vowel letters (independent)
GUR_INDEPENDENT_VOWELS = {
    "ਅ": "a",
    "ਆ": "aa",
    "ਇ": "i",
    "ਈ": "ee",
    "ਉ": "u",
    "ਊ": "oo",
    "ਏ": "e",
    "ਐ": "ai",
    "ਓ": "o",
    "ਔ": "au",
}

# Gurmukhi vowel signs (matras attached to consonants)
GUR_MATRAS = {
    "ਾ": "aa",
    "ਿ": "i",
    "ੀ": "ee",
    "ੁ": "u",
    "ੂ": "oo",
    "ੇ": "e",
    "ੈ": "ai",
    "ੋ": "o",
    "ੌ": "au",
}

# Gurmukhi consonants
GUR_CONSONANTS = {
    "ਕ": "k",
    "ਖ": "kh",
    "ਗ": "g",
    "ਘ": "gh",
    "ਙ": "ng",
    "ਚ": "ch",
    "ਛ": "chh",
    "ਜ": "j",
    "ਝ": "jh",
    "ਞ": "ny",
    "ਟ": "t",
    "ਠ": "th",
    "ਡ": "d",
    "ਢ": "dh",
    "ਣ": "n",
    "ਤ": "t",
    "ਥ": "th",
    "ਦ": "d",
    "ਧ": "dh",
    "ਨ": "n",
    "ਪ": "p",
    "ਫ": "ph",
    "ਬ": "b",
    "ਭ": "bh",
    "ਮ": "m",
    "ਯ": "y",
    "ਰ": "r",
    "ਲ": "l",
    "ਵ": "v",
    "ੜ": "r",
    # With bindi / nukta
    "ਸ਼": "sh",
    "ਖ਼": "kh",
    "ਗ਼": "gh",
    "ਜ਼": "z",
    "ਫ਼": "f",
    "ਲ਼": "l",
}


def is_indic_text(text: str) -> bool:
    """Checks whether the text contains Devanagari or Gurmukhi characters."""
    for ch in text:
        code = ord(ch)
        # Devanagari: U+0900 to U+097F
        # Gurmukhi: U+0A00 to U+0A7F
        if 0x0900 <= code <= 0x097F or 0x0A00 <= code <= 0x0A7F:
            return True
    return False


def romanize_indic(text: str) -> str:
    """Transliterates Devanagari and Gurmukhi text into readable Romanized English.
    
    Preserves existing Latin characters, punctuation, and line breaks.
    """
    if not text:
        return ""

    out = []
    chars = list(text)
    n = len(chars)
    i = 0

    while i < n:
        c = chars[i]

        # Check for two-character nukta composite (e.g. क + ़ = क़ or ਕ + ਼ = ਖ਼)
        if i + 1 < n and chars[i + 1] in ("़", "਼"):
            composite = c + chars[i + 1]
            if composite in DEV_CONSONANTS or composite in GUR_CONSONANTS:
                c = composite
                i += 1

        # Devanagari Independent Vowel
        if c in DEV_INDEPENDENT_VOWELS:
            out.append(DEV_INDEPENDENT_VOWELS[c])

        # Gurmukhi Independent Vowel
        elif c in GUR_INDEPENDENT_VOWELS:
            out.append(GUR_INDEPENDENT_VOWELS[c])

        # Devanagari Consonant
        elif c in DEV_CONSONANTS:
            base = DEV_CONSONANTS[c]
            # Check next character
            if i + 1 < n and chars[i + 1] == "्":  # Virama / Halant
                out.append(base)
                i += 1
            elif i + 1 < n and chars[i + 1] in DEV_MATRAS:  # Matra
                out.append(base + DEV_MATRAS[chars[i + 1]])
                i += 1
            else:
                # Schwa rule: suppress 'a' if followed by space, punctuation, or end of line
                next_c = chars[i + 1] if i + 1 < n else " "
                if next_c in " \n\r\t.,!?;:()[]\"'-—":
                    out.append(base)
                else:
                    out.append(base + "a")

        # Gurmukhi Consonant
        elif c in GUR_CONSONANTS:
            base = GUR_CONSONANTS[c]
            if i + 1 < n and chars[i + 1] == "੍":  # Halant
                out.append(base)
                i += 1
            elif i + 1 < n and chars[i + 1] in GUR_MATRAS:
                out.append(base + GUR_MATRAS[chars[i + 1]])
                i += 1
            else:
                next_c = chars[i + 1] if i + 1 < n else " "
                if next_c in " \n\r\t.,!?;:()[]\"'-—":
                    out.append(base)
                else:
                    out.append(base + "a")

        # Gurmukhi Addak (doubles next consonant)
        elif c == "ੱ":
            if i + 1 < n:
                next_cons = chars[i + 1]
                if next_cons in GUR_CONSONANTS:
                    rep = GUR_CONSONANTS[next_cons][0]
                    out.append(rep)

        # Anusvara / Bindi / Tippi / Chandrabindu
        elif c in ("ं", "ँ", "ਂ", "ੰ"):
            out.append("n")

        # Visarga
        elif c == "ः":
            out.append("h")

        # Danda (।) / Double Danda (॥)
        elif c in ("।", "॥"):
            out.append(".")

        else:
            # Leave Latin, digits, whitespace, punctuation untouched
            out.append(c)

        i += 1

    result = "".join(out)
    # Clean up any duplicate 'aa' if preceded by another vowel or doubled spaces
    result = re.sub(r" +", " ", result)
    return result

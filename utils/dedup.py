from __future__ import annotations

import hashlib
import re
from uuid import uuid4

# Legal suffixes to strip (order matters — check multi-word first)
LEGAL_SUFFIXES: list[str] = ["l.l.c.", "llc", "inc.", "inc", "corp.", "corp", "ltd.", "ltd", "co.", "co"]

# Common words to strip
COMMON_WORDS: set[str] = {"the", "and", "&"}


def normalize_name(name: str) -> str:
    """Normalize a business name for fingerprinting.

    Steps:
        1. Lowercase the entire string.
        2. Strip recognised legal suffixes (as whole words at end of string,
           case-insensitive).  Multi-word / punctuated suffixes are checked
           first because LEGAL_SUFFIXES is ordered that way.
        3. Remove all punctuation EXCEPT hyphens.  Retains a-z, 0-9, hyphens,
           and spaces.
        4. Split into words and discard any word in COMMON_WORDS.
        5. Collapse runs of whitespace and strip leading/trailing space.
    """
    if not name:
        return ""

    # 1. Lowercase
    result = name.lower().strip()

    # 2. Strip legal suffixes (whole-word match at end of string)
    for suffix in LEGAL_SUFFIXES:
        # Escape dots for regex; match as whole word at the end
        pattern = r"\b" + re.escape(suffix) + r"\s*$"
        result = re.sub(pattern, "", result).strip()

    # 3. Remove all punctuation except hyphens.
    #    Keep: a-z, 0-9, hyphen, whitespace
    result = re.sub(r"[^a-z0-9\- ]", "", result)

    # 4. Split into words, remove common words
    words = result.split()
    words = [w for w in words if w not in COMMON_WORDS]

    # 5. Rejoin with single spaces
    result = " ".join(words)

    return result


def normalize_city(city: str) -> str:
    """Lowercase and strip whitespace from a city name."""
    if not city:
        return ""
    return city.lower().strip()


def generate_fingerprint(name: str, city: str, source_url: str = "") -> str:
    """Generate a short fingerprint for deduplication.

    Concatenates normalize_name(name) and normalize_city(city) separated by a
    pipe character, then returns the first 32 hex characters of the SHA-256
    digest (128 bits for better collision resistance).

    If *name* is empty or None, includes source_url in the fingerprint to
    prevent collisions between distinct records that lack a business name.
    """
    norm_name = normalize_name(name) if name else ""
    norm_city = normalize_city(city) if city else ""

    if norm_name:
        raw = f"{norm_name}|{norm_city}"
    else:
        # Include source_url to avoid collisions for nameless records
        raw = f"|{norm_city}|{source_url or uuid4().hex}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return digest[:32]  # 128 bits for better collision resistance

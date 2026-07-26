"""User identity intents — set vs query, never confuse 'adım ne' with a name.

Architecture:
  classify_identity(text) → IdentityIntent | None
  Rules/agent call this BEFORE any "remember name" side effect.
  Names must pass validate_display_name (no question words, no device jargon).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class IdentityKind(str, Enum):
    QUERY = "query"  # "adım ne?", "ismim ne?"
    SET = "set"  # "benim adım Murat"


@dataclass(frozen=True)
class IdentityIntent:
    kind: IdentityKind
    name: Optional[str] = None  # only for SET


# Words that are NEVER a personal name
_BLOCKLIST = frozenset(
    {
        # questions
        "ne",
        "nedir",
        "kim",
        "kimin",
        "nasil",
        "nasıl",
        "nerede",
        "neden",
        "niye",
        "hangi",
        "kaç",
        "kac",
        "var",
        "yok",
        "mi",
        "mı",
        "mu",
        "mü",
        "misin",
        "musun",
        # pronouns / fillers
        "ben",
        "sen",
        "o",
        "biz",
        "siz",
        "bu",
        "su",
        "şu",
        "bir",
        "bana",
        "beni",
        "benim",
        "adim",
        "adım",
        "isim",
        "ismim",
        "adimi",
        "adımı",
        # greetings mixed in
        "selam",
        "merhaba",
        "hey",
        "hi",
        "hello",
        # home jargon (avoid "adım ışık" nonsense)
        "isik",
        "ışık",
        "lamba",
        "ampul",
        "tv",
        "televizyon",
        "hava",
        "ev",
        "snow",
        "asistan",
    }
)

_QUERY_PATTERNS = [
    # "adım ne", "benim adım ne", "ismim nedir"
    re.compile(
        r"(?i)\b(?:benim\s+)?(?:ad[ıi]m|ismim|ismimi|ad[ıi]m[ıi])\s+"
        r"(?:ne|nedir|kim|neydi)\b"
    ),
    re.compile(r"(?i)\b(?:ad[ıi]m[ıi]|ismimi)\s+(?:s[oö]yle|hat[ıi]rl[aı]|bil)\b"),
    re.compile(r"(?i)\b(?:beni\s+)?tan[ıi]yor\s*musun\b"),
    re.compile(r"(?i)\b(?:ismimi|ad[ıi]m[ıi])\s+biliyor\s*musun\b"),
    re.compile(r"(?i)\bwho\s+am\s+i\b"),
    re.compile(r"(?i)\bwhat(?:'s|\s+is)\s+my\s+name\b"),
]

# SET: explicit introduction — name must be captured group 1
_SET_PATTERNS = [
    re.compile(
        r"(?i)(?:^|[\s,.!])(?:benim\s+)?ad[ıi]m\s+"
        r"([A-Za-zÇĞİÖŞÜçğıöşü]{2,24})(?:\s|$|[.,!?])"
    ),
    re.compile(
        r"(?i)(?:^|[\s,.!])(?:benim\s+)?ismim\s+"
        r"([A-Za-zÇĞİÖŞÜçğıöşü]{2,24})(?:\s|$|[.,!?])"
    ),
    re.compile(
        r"(?i)bana\s+([A-Za-zÇĞİÖŞÜçğıöşü]{2,24})\s+de(?:\s|$|[.,!?])"
    ),
    re.compile(
        r"(?i)ad[ıi]m[ıi]\s+([A-Za-zÇĞİÖŞÜçğıöşü]{2,24})\s+"
        r"(?:olarak\s+)?(?:kaydet|hat[ıi]rla|yaz)(?:\s|$|[.,!?])"
    ),
    re.compile(
        r"(?i)ben\s+([A-Za-zÇĞİÖŞÜçğıöşü]{2,24})(?:'y[ıi]m|'yim|im|um|üm)(?:\s|$|[.,!?])"
    ),
]


def _fold_token(s: str) -> str:
    s = s.casefold().strip()
    for a, b in (
        ("ı", "i"),
        ("ğ", "g"),
        ("ü", "u"),
        ("ş", "s"),
        ("ö", "o"),
        ("ç", "c"),
    ):
        s = s.replace(a, b)
    return s


def validate_display_name(raw: str) -> Optional[str]:
    """Return normalized display name or None if invalid."""
    if not raw:
        return None
    name = raw.strip()
    # strip trailing punctuation
    name = re.sub(r"[.,!?;:]+$", "", name).strip()
    if len(name) < 2 or len(name) > 24:
        return None
    # only letters (unicode) and optional hyphen/apostrophe inside
    if not re.fullmatch(r"[A-Za-zÇĞİÖŞÜçğıöşü][A-Za-zÇĞİÖŞÜçğıöşü'\-]{0,23}", name):
        return None
    folded = _fold_token(name)
    if folded in _BLOCKLIST:
        return None
    # reject pure question fragments
    if folded in {"ne", "nedir", "kim"}:
        return None
    # Title-case carefully for Turkish I/i
    return name[0].upper() + name[1:] if name else None


def classify_identity(text: str) -> Optional[IdentityIntent]:
    """
    Classify user text for identity set/query.
    QUERY always wins over SET when both could match (e.g. 'adım ne').
    """
    if not text or not text.strip():
        return None
    t = " ".join(text.strip().split())

    for pat in _QUERY_PATTERNS:
        if pat.search(t):
            return IdentityIntent(kind=IdentityKind.QUERY)

    # folded query safety net: "adim ne" after ASCII lower
    folded = _fold_token(t)
    if re.search(r"\b(?:benim\s+)?(?:adim|ismim)\s+(?:ne|nedir|kim)\b", folded):
        return IdentityIntent(kind=IdentityKind.QUERY)
    if re.search(r"\badim\s+ne\b", folded):
        return IdentityIntent(kind=IdentityKind.QUERY)

    for pat in _SET_PATTERNS:
        m = pat.search(t)
        if not m:
            continue
        candidate = m.group(1)
        # if the capture is a question word, this is QUERY mis-parse → skip set
        if _fold_token(candidate) in _BLOCKLIST:
            continue
        name = validate_display_name(candidate)
        if name:
            return IdentityIntent(kind=IdentityKind.SET, name=name)

    return None

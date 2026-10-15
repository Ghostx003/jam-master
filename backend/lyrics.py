"""Online lyrics fetching and romanization service for Shuffle Master.

Fetches lyrics from public online services and automatically romanizes
Hindi and Punjabi text into phonetic English.
"""

import json
import logging
import re
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

from backend.romanizer import is_indic_text, romanize_indic

logger = logging.getLogger("shuffle_master.lyrics")

# In-memory cache for fetched lyrics: key -> Dict[str, Any]
_LYRICS_CACHE: Dict[str, Dict[str, Any]] = {}


def _clean_string(text: str) -> str:
    """Cleans track titles and artist names of common audio tags, BOM marks, and rip labels."""
    if not text:
        return ""
    # Strip unicode BOM and zero-width characters
    t = text.replace("\ufeff", "").replace("\u200b", "").strip()
    # Remove file extensions like .mp3, .flac, .m4a
    t = re.sub(r"\.(mp3|flac|m4a|wav|aac|ogg|wma)$", "", t, flags=re.IGNORECASE)
    # Remove YouTube rip tags like (MP3_320K), [320kbps], ( 256kbps cbr ), etc.
    t = re.sub(r"[\(\[](?:mp3_\d+k|\d+kbps.*?|cbr).*?[\)\]]", "", t, flags=re.IGNORECASE)
    # Remove (feat. ...), [feat. ...], (ft. ...), (with ...), (official ...)
    t = re.sub(r"[\(\[](?:feat\.|ft\.|with|prod\.|official|full audio|lyrics|lyric video|audio song|video).*?[\)\]]", "", t, flags=re.IGNORECASE)
    # Remove trailing/leading slowed + reverb annotations
    t = re.sub(r"[\-_~ﾉ]\s*(?:slowed|reverb|remix|lofi).*$", "", t, flags=re.IGNORECASE)
    # Remove extra spaces and quotes
    t = re.sub(r"\s+", " ", t).strip(" '\"`-_~")
    return t


def _extract_artist_and_title(artist: str, title: str) -> tuple[str, str]:
    """Extracts true artist and clean title if combined in filename or title tag."""
    c_art = _clean_string(artist)
    c_tit = _clean_string(title)

    # Check if artist is empty, generic or a VEVO/Topic channel name
    is_generic_art = (
        not c_art
        or "unknown" in c_art.lower()
        or c_art.lower().endswith("vevo")
        or c_art.lower().endswith("- topic")
    )

    if " - " in c_tit:
        parts = c_tit.split(" - ", 1)
        potential_art = _clean_string(parts[0])
        potential_tit = _clean_string(parts[1])
        if is_generic_art or (c_art and potential_art.lower() in c_art.lower()):
            c_art = potential_art
            c_tit = potential_tit

    # Normalize primary artist (strip multiple artists separated by commas/ampersands)
    primary_art = re.split(r"[,/&]|(?:\s+ft\.?\s+)|\s+feat\.?\s+", c_art, flags=re.IGNORECASE)[0].strip()
    return primary_art or c_art, c_tit


def _resolve_metadata_from_title(title: str) -> tuple[Optional[str], Optional[str]]:
    """Resolves clean artist name and track title from song title alone using iTunes Search API."""
    c_tit = _clean_string(title)
    if not c_tit:
        return None, None

    url = f"https://itunes.apple.com/search?term={urllib.parse.quote(c_tit)}&entity=song&limit=1"
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        )
        with urllib.request.urlopen(req, timeout=4.0) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
            results = data.get("results", [])
            if results and len(results) > 0:
                art = results[0].get("artistName")
                tit = results[0].get("trackName")
                if art and tit:
                    return _clean_string(art), _clean_string(tit)
    except Exception as e:
        logger.debug(f"iTunes title resolution failed for '{title}': {e}")
    return None, None


def _fetch_from_lyrics_ovh(artist: str, title: str) -> Optional[str]:
    """Attempts to fetch lyrics from api.lyrics.ovh."""
    primary_art, clean_tit = _extract_artist_and_title(artist, title)
    if not clean_tit or not primary_art:
        return None

    url = f"https://api.lyrics.ovh/v1/{urllib.parse.quote(primary_art)}/{urllib.parse.quote(clean_tit)}"
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "ShuffleMasterApp/2.0 (nayak@github.com)",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=4.0) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
            lyrics = data.get("lyrics")
            if lyrics and isinstance(lyrics, str) and len(lyrics.strip()) > 10:
                return lyrics.strip()
    except Exception as e:
        logger.debug(f"lyrics.ovh lookup failed for {artist} - {title}: {e}")

    return None


def _fetch_from_lrclib(artist: str, title: str) -> Optional[str]:
    """Attempts to fetch lyrics from lrclib.net as primary/secondary provider."""
    primary_art, clean_tit = _extract_artist_and_title(artist, title)
    if not clean_tit:
        return None

    # Search clean title alone first, then artist + title
    queries = [clean_tit]
    if primary_art and primary_art.lower() not in clean_tit.lower():
        queries.append(f"{primary_art} {clean_tit}")

    for q in queries:
        url = f"https://lrclib.net/api/search?q={urllib.parse.quote(q)}"
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "ShuffleMasterApp/2.0 (nayak@github.com)",
                    "Accept": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=4.0) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="replace"))
                if isinstance(data, list) and len(data) > 0:
                    for item in data:
                        lyrics = item.get("plainLyrics") or item.get("syncedLyrics")
                        if lyrics and isinstance(lyrics, str) and len(lyrics.strip()) > 10:
                            # Strip sync timestamps if synced
                            plain = re.sub(r"\[\d+:\d+\.\d+\]", "", lyrics).strip()
                            return plain
        except Exception as e:
            logger.debug(f"lrclib search failed for query '{q}': {e}")
    return None


def get_lyrics(artist: str, title: str) -> Dict[str, Any]:
    """Fetches lyrics for the given artist and title, applying Romanization if Indic."""
    cache_key = f"{artist.lower().strip()}||{title.lower().strip()}"
    if cache_key in _LYRICS_CACHE:
        return _LYRICS_CACHE[cache_key]

    clean_art = _clean_string(artist)
    clean_tit = _clean_string(title)

    # If title has "Artist - Song", separate them
    if " - " in clean_tit:
        extracted_art, extracted_tit = _extract_artist_and_title(clean_art, clean_tit)
        if not clean_art or clean_art.lower() in ("unknown", "unknown artist"):
            clean_art = extracted_art
        clean_tit = extracted_tit

    raw_lyrics = None
    resolved_art = clean_art
    resolved_tit = clean_tit

    # If artist is missing or generic, resolve via iTunes
    if not clean_art or clean_art.lower() in ("unknown", "unknown artist", "various artists"):
        itunes_art, itunes_tit = _resolve_metadata_from_title(clean_tit)
        if itunes_art:
            resolved_art = itunes_art
            if itunes_tit:
                resolved_tit = itunes_tit

    # Try 1: lrclib with title
    raw_lyrics = _fetch_from_lrclib(resolved_art, resolved_tit)

    # Try 2: lyrics.ovh with artist and title
    if not raw_lyrics and resolved_art:
        raw_lyrics = _fetch_from_lyrics_ovh(resolved_art, resolved_tit)

    # Try 3: if still not found and we haven't tried resolving metadata yet, resolve via iTunes now
    if not raw_lyrics and resolved_art == clean_art:
        itunes_art, itunes_tit = _resolve_metadata_from_title(clean_tit)
        if itunes_art and itunes_art.lower() != clean_art.lower():
            resolved_art = itunes_art
            resolved_tit = itunes_tit or clean_tit
            raw_lyrics = _fetch_from_lyrics_ovh(resolved_art, resolved_tit) or _fetch_from_lrclib(resolved_art, resolved_tit)

    if not raw_lyrics:
        result = {
            "found": False,
            "artist": resolved_art or artist,
            "title": resolved_tit or title,
            "lyrics": None,
            "romanized": None,
            "is_indic": False,
            "message": f"Lyrics could not be found online for '{title}'. Use the search bar above to try the exact song title.",
        }
        _LYRICS_CACHE[cache_key] = result
        return result

    # Check for Indic script (Devanagari / Gurmukhi) in lyrics or metadata
    has_indic = is_indic_text(raw_lyrics) or is_indic_text(resolved_art) or is_indic_text(resolved_tit)
    romanized = None

    if has_indic:
        romanized = romanize_indic(raw_lyrics)

    result = {
        "found": True,
        "artist": resolved_art or artist,
        "title": resolved_tit or title,
        "lyrics": raw_lyrics,
        "romanized": romanized,
        "is_indic": has_indic,
        "message": None,
    }
    _LYRICS_CACHE[cache_key] = result
    return result

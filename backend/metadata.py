"""Audio metadata extraction and embedded artwork extraction using Mutagen.
"""

from __future__ import annotations

import base64
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Tuple

try:
    import mutagen
    from mutagen.id3 import ID3, APIC
    from mutagen.flac import FLAC, Picture
    from mutagen.mp4 import MP4
except ImportError:
    mutagen = None


@dataclass
class AudioMetadata:
    """Extracted and normalized audio metadata."""
    title: Optional[str]
    artist: Optional[str]
    album: Optional[str]
    genre: Optional[str]
    duration: float  # seconds


def clean_filename_title(filename_stem: str) -> str:
    """Converts a raw filename stem into a clean, human-readable title.
    
    Examples:
        '01 - Bohemian Rhapsody' -> 'Bohemian Rhapsody'
        '04. Hotel California'   -> 'Hotel California'
        'track_12_stairway'      -> 'Track 12 Stairway'
    """
    cleaned = re.sub(r"^\s*\d+[\s._-]+", "", filename_stem)
    cleaned = cleaned.replace("_", " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned if cleaned else filename_stem


def _extract_first_tag(tags: Any, keys: list[str]) -> Optional[str]:
    """Safely extracts the first non-empty string for any of the given tag keys."""
    if not tags:
        return None
    for key in keys:
        val = tags.get(key)
        if val:
            if isinstance(val, (list, tuple)):
                if len(val) > 0 and str(val[0]).strip():
                    return str(val[0]).strip()
            elif str(val).strip():
                return str(val).strip()
    return None


def extract_audio_metadata(file_path: Path) -> AudioMetadata:
    """Extracts metadata and duration from an audio file safely.
    
    Returns clean fallback values if tags are absent or file is corrupt.
    Never raises an exception on corrupted files.
    """
    stem = file_path.stem
    fallback_title = clean_filename_title(stem)

    if mutagen is None:
        return AudioMetadata(
            title=fallback_title,
            artist=None,
            album=None,
            genre=None,
            duration=0.0,
        )

    try:
        audio = mutagen.File(str(file_path))
        if audio is None:
            return AudioMetadata(
                title=fallback_title,
                artist=None,
                album=None,
                genre=None,
                duration=0.0,
            )

        duration = 0.0
        if hasattr(audio, "info") and audio.info and hasattr(audio.info, "length"):
            duration = max(0.0, float(audio.info.length))

        tags = getattr(audio, "tags", None)
        title: Optional[str] = None
        artist: Optional[str] = None
        album: Optional[str] = None
        genre: Optional[str] = None

        if tags:
            title = _extract_first_tag(tags, ["title", "TIT2", "\xa9nam", "Title", "TITLE"])
            artist = _extract_first_tag(tags, ["artist", "TPE1", "\xa9ART", "Author", "ARTIST"])
            album = _extract_first_tag(tags, ["album", "TALB", "\xa9alb", "Album", "ALBUM"])
            genre = _extract_first_tag(tags, ["genre", "TCON", "\xa9gen", "Genre", "GENRE"])

        if not title or not title.strip():
            title = fallback_title

        return AudioMetadata(
            title=title.strip() if title else fallback_title,
            artist=artist.strip() if artist else None,
            album=album.strip() if album else None,
            genre=genre.strip() if genre else None,
            duration=duration,
        )

    except Exception:
        return AudioMetadata(
            title=fallback_title,
            artist=None,
            album=None,
            genre=None,
            duration=0.0,
        )


def extract_embedded_artwork(file_path: Path) -> Optional[Tuple[bytes, str]]:
    """Extracts raw embedded artwork bytes and MIME type from an audio file.
    
    Returns:
        (image_data, mime_type) or None if no artwork is embedded.
    """
    if mutagen is None:
        return None

    try:
        audio = mutagen.File(str(file_path))
        if audio is None:
            return None

        # 1. ID3 Tags (MP3, AIFF, WAV with ID3 chunk)
        if hasattr(audio, "tags") and audio.tags:
            tags = audio.tags
            # ID3 APIC frames
            if hasattr(tags, "getall"):
                apic_frames = tags.getall("APIC")
                if apic_frames:
                    apic = apic_frames[0]
                    mime = getattr(apic, "mime", "image/jpeg") or "image/jpeg"
                    return apic.data, mime

            # 2. MP4 / M4A / AAC covr atom
            if hasattr(tags, "get") and "covr" in tags:
                covr_list = tags.get("covr")
                if covr_list and len(covr_list) > 0:
                    covr = covr_list[0]
                    # MP4Cover has imageformat attribute
                    mime = "image/png" if getattr(covr, "imageformat", None) == 14 else "image/jpeg"
                    return bytes(covr), mime

        # 3. FLAC pictures
        if hasattr(audio, "pictures") and audio.pictures:
            pic = audio.pictures[0]
            mime = getattr(pic, "mime", "image/jpeg") or "image/jpeg"
            return pic.data, mime

        # 4. Vorbis comments METADATA_BLOCK_PICTURE (OGG, OPUS)
        if hasattr(audio, "get") and audio.get("metadata_block_picture"):
            blocks = audio.get("metadata_block_picture")
            if blocks and len(blocks) > 0:
                raw_b64 = blocks[0]
                pic_data = base64.b64decode(raw_b64)
                # Parse FLAC Picture structure
                flac_pic = Picture(pic_data)
                mime = flac_pic.mime or "image/jpeg"
                return flac_pic.data, mime

    except Exception:
        pass

    return None


def get_or_create_artwork_thumbnail(track_id: int, canonical_path: str) -> Optional[Path]:
    """Retrieves cached artwork or extracts and caches it.
    
    Returns path to thumbnail file on disk, or None if no artwork exists.
    """
    from backend.config import get_artwork_cache_dir

    cache_dir = get_artwork_cache_dir()
    # Check for existing cached file
    for ext in [".jpg", ".png", ".webp"]:
        cached = cache_dir / f"{track_id}{ext}"
        if cached.exists() and cached.stat().st_size > 0:
            return cached

    # Extract artwork
    p = Path(canonical_path)
    if not p.exists():
        return None

    art = extract_embedded_artwork(p)
    if not art:
        return None

    img_bytes, mime = art
    ext = ".png" if "png" in mime.lower() else ".jpg"
    target_file = cache_dir / f"{track_id}{ext}"

    try:
        with open(target_file, "wb") as f:
            f.write(img_bytes)
        return target_file
    except Exception:
        return None

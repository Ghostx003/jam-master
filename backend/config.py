"""Configuration and system paths for Shuffle Master.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Set

# Default Audio Extensions supported by AIMP and Mutagen
DEFAULT_AUDIO_EXTENSIONS: Set[str] = {
    ".mp3",
    ".flac",
    ".wav",
    ".m4a",
    ".aac",
    ".ogg",
    ".opus",
    ".wma",
    ".aiff",
    ".aif",
    ".ape",
    ".wv",
    ".alac",
    ".mpc",
}

# Shuffle Algorithm Tuning Parameters (NO RATINGS OR LIKES)
DEFAULT_SHUFFLE_CONFIG = {
    # Fraction of eligible tracks excluded from immediate reselection
    "history_ratio": 0.25,
    # Hard bounds on recent-history window size
    "min_history_window": 1,
    "max_history_window": 50,
    # Exposure bonus for tracks that have never been played
    "discovery_boost": 1.40,
    # Logarithmic dampening multiplier for high-play tracks
    "frequency_dampening": 0.15,
    # Multiplicative penalty per recent skip (decaying over time)
    "skip_penalty": 0.50,
    "min_skip_factor": 0.20,
    # How many tracks after a skip before the skip penalty completely expires
    "skip_decay_plays": 8,
    # Comeback recovery half-life (in plays) for tracks unplayed for a long time
    "recency_half_life": 40,
    "max_recency_boost": 1.50,
    # Algorithm randomness: 0.0 = smart weighted shuffle, 1.0 = pure uniform random
    "randomness_factor": 0.0,
}

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8765


def get_app_data_dir() -> Path:
    """Returns the dedicated application data directory.
    
    Defaults to %APPDATA%/ShuffleMaster on Windows, with fallback to ~/.shuffle_master.
    Respects SHUFFLE_MASTER_APP_DIR and JAM_ENGINE_APP_DIR environment variables.
    """
    env_dir = os.environ.get("SHUFFLE_MASTER_APP_DIR") or os.environ.get("JAM_ENGINE_APP_DIR")
    if env_dir:
        path = Path(env_dir).resolve()
    else:
        appdata = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA")
        if appdata:
            path = Path(appdata) / "ShuffleMaster"
        else:
            path = Path.home() / ".shuffle_master"

    path.mkdir(parents=True, exist_ok=True)
    return path


def get_db_path() -> Path:
    """Returns the path to the persistent SQLite database."""
    env_db = os.environ.get("SHUFFLE_MASTER_DB_PATH") or os.environ.get("JAM_ENGINE_DB_PATH")
    if env_db:
        db_path = Path(env_db).resolve()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return db_path
    return get_app_data_dir() / "library.db"


def get_artwork_cache_dir() -> Path:
    """Returns the directory used for caching extracted album artwork."""
    cache_dir = get_app_data_dir() / "artwork_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_supported_extensions() -> Set[str]:
    """Returns the set of active supported audio extensions (lowercase with leading dot)."""
    return set(DEFAULT_AUDIO_EXTENSIONS)

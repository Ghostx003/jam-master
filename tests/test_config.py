"""Tests for backend.config module.
"""

import os
from pathlib import Path
from backend.config import (
    DEFAULT_AUDIO_EXTENSIONS,
    get_app_data_dir,
    get_db_path,
    get_artwork_cache_dir,
    get_supported_extensions,
)


def test_default_extensions():
    exts = get_supported_extensions()
    assert ".mp3" in exts
    assert ".flac" in exts
    assert ".wav" in exts
    assert ".m4a" in exts
    assert ".opus" in exts
    assert ".wma" in exts
    assert ".aiff" in exts


def test_custom_app_data_env(tmp_path, monkeypatch):
    custom_dir = tmp_path / "custom_app_dir"
    monkeypatch.setenv("SHUFFLE_MASTER_APP_DIR", str(custom_dir))

    resolved = get_app_data_dir()
    assert resolved == custom_dir
    assert resolved.exists()


def test_custom_db_env(tmp_path, monkeypatch):
    custom_db = tmp_path / "subdir" / "test.db"
    monkeypatch.setenv("SHUFFLE_MASTER_DB_PATH", str(custom_db))

    resolved = get_db_path()
    assert resolved == custom_db
    assert custom_db.parent.exists()


def test_artwork_cache_dir():
    cache_dir = get_artwork_cache_dir()
    assert cache_dir.exists()
    assert cache_dir.is_dir()

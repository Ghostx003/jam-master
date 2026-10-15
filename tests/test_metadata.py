"""Tests for audio metadata extraction and filename cleaning.
"""

from pathlib import Path
from backend.metadata import clean_filename_title, extract_audio_metadata, extract_embedded_artwork


def test_clean_filename_title():
    assert clean_filename_title("01 - Bohemian Rhapsody") == "Bohemian Rhapsody"
    assert clean_filename_title("04. Hotel California") == "Hotel California"
    assert clean_filename_title("12_Stairway_To_Heaven") == "Stairway To Heaven"
    assert clean_filename_title("02  Imagine") == "Imagine"
    assert clean_filename_title("Just Track Name") == "Just Track Name"


def test_missing_or_corrupt_file_graceful():
    fake_path = Path("non_existent_audio_file_12345.mp3")
    meta = extract_audio_metadata(fake_path)
    assert meta.title == "non existent audio file 12345"
    assert meta.artist is None
    assert meta.duration == 0.0


def test_corrupt_bytes_graceful(tmp_path):
    bad_file = tmp_path / "corrupt_song.mp3"
    bad_file.write_bytes(b"NOT_REAL_MP3_DATA_RANDOM_BYTES_!@#$%^")

    meta = extract_audio_metadata(bad_file)
    assert meta.title == "corrupt song"
    assert meta.duration == 0.0


def test_extract_artwork_none():
    fake_path = Path("non_existent.mp3")
    assert extract_embedded_artwork(fake_path) is None

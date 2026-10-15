"""Tests for filesystem scanner and incremental indexer.
"""

from pathlib import Path
from backend.database import Database
from backend.scanner import LibraryScanner


def test_scan_and_incremental_refresh(tmp_path):
    db = Database(tmp_path / "test.db")
    scanner = LibraryScanner(db)

    music_dir = tmp_path / "Music"
    rock_dir = music_dir / "Rock"
    jazz_dir = music_dir / "Jazz"
    empty_dir = music_dir / "EmptyFolder"
    text_dir = music_dir / "Docs"

    rock_dir.mkdir(parents=True)
    jazz_dir.mkdir(parents=True)
    empty_dir.mkdir(parents=True)
    text_dir.mkdir(parents=True)

    # Audio files
    (rock_dir / "song1.mp3").write_bytes(b"dummy_mp3_content_1")
    (rock_dir / "song2.flac").write_bytes(b"dummy_flac_content_2")
    (jazz_dir / "track.wav").write_bytes(b"dummy_wav_content_3")
    # Non-audio file
    (text_dir / "lyrics.txt").write_text("la la la")

    # Initial scan
    total, new_or_updated, unavailable = scanner.scan_directory(music_dir)
    assert total == 3
    assert new_or_updated == 3
    assert unavailable == 0

    # Folders summary: empty_dir and text_dir MUST NOT be in eligible folders!
    folders = scanner.get_eligible_folders(music_dir)
    folder_names = [f.display_name for f in folders]
    assert "Rock" in folder_names
    assert "Jazz" in folder_names
    assert "EmptyFolder" not in folder_names
    assert "Docs" not in folder_names

    # Incremental scan without any file changes: new_or_updated must be 0!
    total2, new_or_updated2, unavailable2 = scanner.scan_directory(music_dir)
    assert total2 == 3
    assert new_or_updated2 == 0, "Incremental refresh should not re-read unchanged files!"
    assert unavailable2 == 0

    # Add 1 file and delete 1 file
    (jazz_dir / "new_jazz.ogg").write_bytes(b"dummy_ogg")
    (rock_dir / "song1.mp3").unlink()

    total3, new_or_updated3, unavailable3 = scanner.scan_directory(music_dir)
    assert total3 == 3  # (song2, track, new_jazz)
    assert new_or_updated3 == 1
    assert unavailable3 == 1  # song1 marked unavailable

    # Check that song1 is marked unavailable in DB
    s1 = db.get_track_by_path(str((rock_dir / "song1.mp3").resolve()))
    assert s1 is not None
    assert s1.is_available is False

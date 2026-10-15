"""Tests for SQLite database persistence and operations.
Zero ratings or likes. Strict verification of clean schema.
"""

import pytest
from pathlib import Path
from backend.database import Database, TrackRecord


@pytest.fixture
def db(tmp_path):
    db_path = tmp_path / "test_master.db"
    return Database(db_path)


def test_rating_column_support(db):
    """Verifies that the rating column exists and can be set."""
    with db._get_connection() as conn:
        cursor = conn.execute("PRAGMA table_info(tracks)")
        columns = [row["name"] for row in cursor.fetchall()]
        assert "rating" in columns, "Rating column must exist in tracks table!"

    tid = db.upsert_scanned_track(
        canonical_path="D:/music/track.mp3",
        folder_path="D:/music",
        filename="track.mp3",
        file_size=1000,
        mtime=1.0,
        title="Test Song",
        artist="Test Artist",
        album="Test Album",
        genre="Rock",
        duration=120.0,
    )
    t = db.get_track_by_id(tid)
    assert t.rating == 0

    assert db.set_track_rating(tid, 5)
    t = db.get_track_by_id(tid)
    assert t.rating == 5


def test_settings_crud(db):
    assert db.get_setting("non_existent") is None
    assert db.get_setting("non_existent", "default_val") == "default_val"

    db.set_setting("saved_music_dir", "D:/Music")
    assert db.get_setting("saved_music_dir") == "D:/Music"

    db.set_setting("saved_music_dir", "D:/NewMusic")
    assert db.get_setting("saved_music_dir") == "D:/NewMusic"

    db.delete_setting("saved_music_dir")
    assert db.get_setting("saved_music_dir") is None


def test_music_roots_crud(db):
    roots = db.get_all_roots()
    assert len(roots) == 0

    root1 = db.add_music_root("D:/Music/Rock", "Rock Classics")
    assert root1.id is not None
    assert root1.display_name == "Rock Classics"

    roots = db.get_all_roots()
    assert len(roots) == 1
    assert roots[0].id == root1.id

    db.update_root_scanned(root1.id)
    updated = db.get_all_roots()[0]
    assert updated.last_scanned_at is not None

    removed = db.remove_music_root(root1.id)
    assert removed is True
    assert len(db.get_all_roots()) == 0


def test_upsert_and_retrieve_track(db):
    tid = db.upsert_scanned_track(
        canonical_path="D:/Music/Rock/song1.mp3",
        folder_path="D:/Music/Rock",
        filename="song1.mp3",
        file_size=10240,
        mtime=1700000000.0,
        title="Song One",
        artist="Rock Artist",
        album="Album One",
        genre="Rock",
        duration=215.5,
    )
    assert tid > 0

    track = db.get_track_by_path("D:/Music/Rock/song1.mp3")
    assert track is not None
    assert track.title == "Song One"
    assert track.artist == "Rock Artist"
    assert track.duration == 215.5
    assert track.display_duration == "03:35"
    assert track.play_count == 0
    assert track.is_available is True


def test_record_play_and_history(db):
    db.upsert_scanned_track(
        canonical_path="D:/Music/track1.mp3",
        folder_path="D:/Music",
        filename="track1.mp3",
        file_size=1000,
        mtime=1.0,
        title="T1",
        artist="A1",
        album="Alb",
        genre="G",
        duration=120.0,
    )
    t = db.get_track_by_path("D:/Music/track1.mp3")

    db.record_play(t.id, was_skipped=False)
    db.record_play(t.id, was_skipped=True)

    t_after = db.get_track_by_id(t.id)
    assert t_after.play_count == 2
    assert t_after.skip_count == 1
    assert t_after.last_played_at is not None

    history = db.get_recent_history(10)
    assert len(history) == 2
    assert history[0]["track"]["id"] == t.id
    assert history[0]["was_skipped"] is True


def test_search_tracks(db):
    db.upsert_scanned_track(
        canonical_path="D:/Music/bohemian.mp3",
        folder_path="D:/Music",
        filename="bohemian.mp3",
        file_size=1000,
        mtime=1.0,
        title="Bohemian Rhapsody",
        artist="Queen",
        album="A Night at the Opera",
        genre="Rock",
        duration=354.0,
    )
    db.upsert_scanned_track(
        canonical_path="D:/Music/stairway.mp3",
        folder_path="D:/Music",
        filename="stairway.mp3",
        file_size=1000,
        mtime=1.0,
        title="Stairway to Heaven",
        artist="Led Zeppelin",
        album="Led Zeppelin IV",
        genre="Rock",
        duration=482.0,
    )

    matches_queen = db.search_tracks("queen")
    assert len(matches_queen) == 1
    assert matches_queen[0].title == "Bohemian Rhapsody"

    matches_rock = db.search_tracks("Led Zeppelin")
    assert len(matches_rock) == 1
    assert matches_rock[0].artist == "Led Zeppelin"


def test_playlists_db_operations(db):
    # Create playlist
    pl = db.create_playlist("Roadtrip", "Songs for driving")
    assert pl.id is not None
    assert pl.name == "Roadtrip"

    # Add tracks
    t1_id = db.upsert_scanned_track(
        canonical_path="D:/Music/song1.mp3",
        folder_path="D:/Music",
        filename="song1.mp3",
        file_size=1000,
        mtime=1.0,
        title="Song 1",
        artist="Artist 1",
        album="Alb",
        genre="Rock",
        duration=180.0,
    )
    t2_id = db.upsert_scanned_track(
        canonical_path="D:/Music/song2.mp3",
        folder_path="D:/Music",
        filename="song2.mp3",
        file_size=1000,
        mtime=1.0,
        title="Song 2",
        artist="Artist 2",
        album="Alb",
        genre="Rock",
        duration=200.0,
    )

    added = db.add_tracks_to_playlist(pl.id, [t1_id, t2_id])
    assert added == 2

    entries = db.get_playlist_entries(pl.id)
    assert len(entries) == 2
    assert entries[0].position == 1
    assert entries[0].track_id == t1_id
    assert entries[1].position == 2
    assert entries[1].track_id == t2_id

    # Reorder
    db.reorder_playlist_tracks(pl.id, [entries[1].id, entries[0].id])
    reordered_entries = db.get_playlist_entries(pl.id)
    assert reordered_entries[0].track_id == t2_id
    assert reordered_entries[1].track_id == t1_id

    # Remove single entry
    db.remove_playlist_entry(pl.id, reordered_entries[0].id)
    after_removal = db.get_playlist_entries(pl.id)
    assert len(after_removal) == 1
    assert after_removal[0].track_id == t1_id
    assert after_removal[0].position == 1

    # Rename
    db.rename_playlist(pl.id, "Roadtrip 2026")
    updated_pl = db.get_playlist(pl.id)
    assert updated_pl.name == "Roadtrip 2026"

    # Delete
    deleted = db.delete_playlist(pl.id)
    assert deleted is True
    assert db.get_playlist(pl.id) is None

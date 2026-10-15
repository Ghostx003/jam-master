"""Tests for playlist management service.
"""

import pytest
from pathlib import Path
from backend.database import Database
from backend.playlists import PlaylistService


@pytest.fixture
def playlist_service(tmp_path):
    db = Database(tmp_path / "playlists_test.db")
    # Insert 5 sample tracks
    for i in range(1, 6):
        db.upsert_scanned_track(
            canonical_path=f"D:/Music/track_{i}.mp3",
            folder_path="D:/Music",
            filename=f"track_{i}.mp3",
            file_size=1000,
            mtime=1.0,
            title=f"Track {i}",
            artist=f"Artist {i}",
            album="Album",
            genre="Rock",
            duration=180.0,
        )
    return PlaylistService(db)


def test_create_and_list_playlists(playlist_service):
    p1 = playlist_service.create_playlist("Workout", "High energy tracks")
    assert p1["name"] == "Workout"
    assert p1["description"] == "High energy tracks"

    p2 = playlist_service.create_playlist("Chill", "Relaxing tracks")
    assert p2["name"] == "Chill"

    all_pl = playlist_service.list_playlists()
    assert len(all_pl) == 2
    names = [p["name"] for p in all_pl]
    assert "Workout" in names
    assert "Chill" in names


def test_duplicate_playlist_name_rejected(playlist_service):
    playlist_service.create_playlist("UniqueName")
    with pytest.raises(ValueError, match="already exists"):
        playlist_service.create_playlist("UniqueName")


def test_add_and_remove_tracks(playlist_service):
    pl = playlist_service.create_playlist("Mix")
    db = playlist_service.db
    all_tracks = db.get_all_tracks()
    track_ids = [t.id for t in all_tracks[:3]]

    added = playlist_service.add_tracks(pl["id"], track_ids)
    assert added == 3

    details = playlist_service.get_playlist_details(pl["id"])
    assert details["track_count"] == 3
    assert len(details["entries"]) == 3
    assert details["total_duration"] == 3 * 180.0

    # Remove the second track entry
    entry_to_remove = details["entries"][1]["id"]
    removed = playlist_service.remove_entry(pl["id"], entry_to_remove)
    assert removed is True

    details_after = playlist_service.get_playlist_details(pl["id"])
    assert details_after["track_count"] == 2
    # Ensure positions were recompacted to 1, 2
    assert details_after["entries"][0]["position"] == 1
    assert details_after["entries"][1]["position"] == 2


def test_reorder_tracks(playlist_service):
    pl = playlist_service.create_playlist("OrderTest")
    db = playlist_service.db
    all_tracks = db.get_all_tracks()
    track_ids = [t.id for t in all_tracks[:3]]

    playlist_service.add_tracks(pl["id"], track_ids)
    details = playlist_service.get_playlist_details(pl["id"])
    entries = details["entries"]
    e1, e2, e3 = entries[0]["id"], entries[1]["id"], entries[2]["id"]

    # Reorder to [e3, e1, e2]
    playlist_service.reorder_entries(pl["id"], [e3, e1, e2])

    reordered = playlist_service.get_playlist_details(pl["id"])
    reordered_entries = reordered["entries"]
    assert reordered_entries[0]["id"] == e3
    assert reordered_entries[0]["position"] == 1
    assert reordered_entries[1]["id"] == e1
    assert reordered_entries[1]["position"] == 2
    assert reordered_entries[2]["id"] == e2
    assert reordered_entries[2]["position"] == 3


def test_rename_and_delete_playlist(playlist_service):
    pl = playlist_service.create_playlist("Temporary")
    assert playlist_service.rename_playlist(pl["id"], "Permanent") is True

    details = playlist_service.get_playlist_details(pl["id"])
    assert details["name"] == "Permanent"

    assert playlist_service.delete_playlist(pl["id"]) is True
    assert playlist_service.get_playlist_details(pl["id"]) is None

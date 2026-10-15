"""Tests for ZIP import and export service.
"""

import io
import json
import zipfile
import pytest
from pathlib import Path
from backend.database import Database
from backend.import_export import ImportExportService
from backend.playlists import PlaylistService


@pytest.fixture
def test_setup(tmp_path):
    db = Database(tmp_path / "impexp.db")
    pl_service = PlaylistService(db)
    impexp_service = ImportExportService(db)

    # Insert tracks
    t1_id = db.upsert_scanned_track(
        canonical_path="D:/Music/Rock/song1.mp3",
        folder_path="D:/Music/Rock",
        filename="song1.mp3",
        file_size=5000,
        mtime=1.0,
        title="Song 1",
        artist="Artist A",
        album="Album X",
        genre="Rock",
        duration=200.0,
    )
    t2_id = db.upsert_scanned_track(
        canonical_path="D:/Music/Rock/song2.mp3",
        folder_path="D:/Music/Rock",
        filename="song2.mp3",
        file_size=6000,
        mtime=1.0,
        title="Song 2",
        artist="Artist B",
        album="Album Y",
        genre="Rock",
        duration=240.0,
    )

    pl = pl_service.create_playlist("Classic Rock", "Best of Rock")
    pl_service.add_tracks(pl["id"], [t1_id, t2_id])

    return {
        "db": db,
        "pl_service": pl_service,
        "impexp_service": impexp_service,
        "playlist_id": pl["id"],
        "t1_id": t1_id,
        "t2_id": t2_id,
    }


def test_export_playlists_to_zip(test_setup):
    impexp = test_setup["impexp_service"]
    pl_id = test_setup["playlist_id"]

    zip_buf = impexp.export_playlists_to_zip([pl_id])
    assert zip_buf is not None

    # Inspect zip contents
    with zipfile.ZipFile(zip_buf, "r") as zf:
        names = zf.namelist()
        assert "manifest.json" in names

        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        assert manifest["app"] == "ShuffleMaster"
        assert manifest["playlist_count"] == 1
        assert manifest["playlists"][0]["name"] == "Classic Rock"

        data_file = manifest["playlists"][0]["data_file"]
        assert data_file in names

        pl_data = json.loads(zf.read(data_file).decode("utf-8"))
        assert pl_data["name"] == "Classic Rock"
        assert pl_data["track_count"] == 2
        assert len(pl_data["tracks"]) == 2
        assert pl_data["tracks"][0]["title"] == "Song 1"
        assert pl_data["tracks"][1]["title"] == "Song 2"


def test_preview_import_zip(test_setup):
    impexp = test_setup["impexp_service"]
    pl_id = test_setup["playlist_id"]

    zip_buf = impexp.export_playlists_to_zip([pl_id])

    preview = impexp.preview_import_zip(zip_buf)
    assert preview["playlist_count"] == 1
    assert preview["total_tracks"] == 2
    assert preview["matched_tracks"] == 2
    assert preview["playlists"][0]["name"] == "Classic Rock"
    assert preview["playlists"][0]["has_name_conflict"] is True


def test_commit_import_rename_conflict(test_setup, tmp_path):
    impexp = test_setup["impexp_service"]
    pl_id = test_setup["playlist_id"]
    db = test_setup["db"]

    zip_buf = impexp.export_playlists_to_zip([pl_id])

    # Import with default policy "rename"
    result = impexp.commit_import_zip(zip_buf, conflict_policy="rename")
    assert result["imported_playlists"] == 1
    assert result["playlists"][0]["name"] == "Classic Rock (1)"

    # Verify both playlists exist in database
    p_orig = db.get_playlist(pl_id)
    p_imported = db.get_playlist_by_name("Classic Rock (1)")
    assert p_orig is not None
    assert p_imported is not None
    assert p_imported.id != p_orig.id


def test_commit_import_replace_conflict(test_setup):
    impexp = test_setup["impexp_service"]
    pl_id = test_setup["playlist_id"]
    db = test_setup["db"]

    zip_buf = impexp.export_playlists_to_zip([pl_id])

    # Import with policy "replace"
    result = impexp.commit_import_zip(zip_buf, conflict_policy="replace")
    assert result["imported_playlists"] == 1

    # Only one playlist named Classic Rock should exist
    playlists = db.list_playlists()
    names = [p.name for p in playlists]
    assert names.count("Classic Rock") == 1


def test_commit_import_skip_conflict(test_setup):
    impexp = test_setup["impexp_service"]
    pl_id = test_setup["playlist_id"]

    zip_buf = impexp.export_playlists_to_zip([pl_id])

    result = impexp.commit_import_zip(zip_buf, conflict_policy="skip")
    assert result["imported_playlists"] == 0
    assert result["skipped_playlists"] == 1


def test_relink_missing_tracks(tmp_path):
    # Setup fresh DB
    db = Database(tmp_path / "relink.db")
    impexp = ImportExportService(db)

    # Create dummy relocated music folder
    music_dir = tmp_path / "RelocatedMusic"
    music_dir.mkdir(parents=True)
    relocated_file = music_dir / "target_song.mp3"
    relocated_file.write_bytes(b"audio_bytes")

    # Construct in-memory zip where canonical_path was on D:/OldDrive/target_song.mp3
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        manifest = {
            "format_version": "1.0",
            "app": "ShuffleMaster",
            "exported_at": 1.0,
            "playlist_count": 1,
            "playlists": [{
                "id": 1,
                "name": "Relink Test",
                "description": "",
                "track_count": 1,
                "total_duration": 180.0,
                "data_file": "playlists/relink_test_1.json",
            }],
        }
        zf.writestr("manifest.json", json.dumps(manifest))

        playlist_data = {
            "format_version": "1.0",
            "id": 1,
            "name": "Relink Test",
            "description": "",
            "tracks": [{
                "position": 1,
                "title": "Target Song",
                "artist": "Artist",
                "album": "Album",
                "duration": 180.0,
                "filename": "target_song.mp3",
                "canonical_path": "D:/OldDrive/target_song.mp3",
                "relative_path": "target_song.mp3",
                "file_size": 1000,
            }],
        }
        zf.writestr("playlists/relink_test_1.json", json.dumps(playlist_data))

    zip_buf.seek(0)
    # Commit import with relink_root pointing to music_dir
    res = impexp.commit_import_zip(zip_buf, relink_root=str(music_dir))
    assert res["imported_playlists"] == 1

    imported_pl = db.get_playlist_by_name("Relink Test")
    entries = db.get_playlist_entries(imported_pl.id)
    assert len(entries) == 1
    assert entries[0].track is not None
    # Track path should now point to relocated file
    assert entries[0].track.canonical_path == str(relocated_file.resolve())
    assert entries[0].track.is_available is True

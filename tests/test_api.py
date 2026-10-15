"""Integration tests for FastAPI REST API endpoints.
"""

import io
import pytest
from fastapi.testclient import TestClient
from pathlib import Path

from backend.api import create_api_router
from backend.database import Database
from backend.import_export import ImportExportService
from backend.player import AudioPlayer
from backend.playlists import PlaylistService
from backend.scanner import LibraryScanner
from backend.shuffle_engine import ShuffleEngine
from fastapi import FastAPI


@pytest.fixture
def api_client(tmp_path):
    db_path = tmp_path / "api_test.db"
    db = Database(db_path)

    # Insert sample tracks
    for i in range(1, 11):
        db.upsert_scanned_track(
            canonical_path=f"D:/ApiMusic/track_{i:02d}.mp3",
            folder_path="D:/ApiMusic",
            filename=f"track_{i:02d}.mp3",
            file_size=5000,
            mtime=1.0,
            title=f"API Track {i}",
            artist="API Artist",
            album="API Album",
            genre="Pop",
            duration=190.0,
        )

    player = AudioPlayer()
    engine = ShuffleEngine(db)
    scanner = LibraryScanner(db)
    pl_service = PlaylistService(db)
    impexp_service = ImportExportService(db)

    app = FastAPI()
    router = create_api_router(
        db=db,
        player=player,
        engine=engine,
        scanner=scanner,
        playlist_service=pl_service,
        import_export_service=impexp_service,
    )
    app.include_router(router)
    return TestClient(app)


def test_api_health(api_client):
    res = api_client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"


def test_api_playback_flow(api_client):
    # Initial state
    res = api_client.get("/api/playback/state")
    assert res.status_code == 200

    # Play folders
    res = api_client.post("/api/playback/play-folders", json={"folder_paths": ["D:/ApiMusic"]})
    assert res.status_code == 200
    state = res.json()
    assert state["current_track"] is not None
    assert state["pool_size"] == 10

    # Next track
    res = api_client.post("/api/playback/next")
    assert res.status_code == 200
    state_after = res.json()
    assert state_after["current_track"] is not None

    # Repeat
    res = api_client.post("/api/playback/repeat", json={"repeats": 2})
    assert res.status_code == 200
    assert res.json()["repeats_remaining"] == 2


def test_api_playlists_crud(api_client):
    # 1. Create playlist
    res = api_client.post("/api/playlists", json={"name": "API Playlist", "description": "Testing API"})
    assert res.status_code == 200
    pl = res.json()
    pl_id = pl["id"]
    assert pl["name"] == "API Playlist"

    # 2. Add tracks
    tracks_res = api_client.get("/api/library/tracks")
    track_ids = [t["id"] for t in tracks_res.json()[:3]]
    add_res = api_client.post(f"/api/playlists/{pl_id}/tracks", json={"track_ids": track_ids})
    assert add_res.status_code == 200
    assert add_res.json()["added_count"] == 3

    # 3. Get playlist details
    get_res = api_client.get(f"/api/playlists/{pl_id}")
    assert get_res.status_code == 200
    details = get_res.json()
    assert len(details["entries"]) == 3

    # 4. Rename playlist
    rename_res = api_client.put(f"/api/playlists/{pl_id}", json={"name": "Renamed Playlist"})
    assert rename_res.status_code == 200

    # 5. Delete playlist
    del_res = api_client.delete(f"/api/playlists/{pl_id}")
    assert del_res.status_code == 200


def test_api_settings(api_client):
    res = api_client.get("/api/settings")
    assert res.status_code == 200
    data = res.json()
    assert "shuffle_config" in data
    assert "player" in data

    # Update settings
    up_res = api_client.post("/api/settings", json={"history_ratio": 0.35})
    assert up_res.status_code == 200
    assert up_res.json()["shuffle_config"]["history_ratio"] == 0.35


def test_api_up_next_queue(api_client):
    # Up next default capacity
    res = api_client.get("/api/playback/up-next")
    assert res.status_code == 200
    data = res.json()
    assert "up_next" in data
    # 10 sample tracks inserted
    assert len(data["up_next"]) <= 50

    # Reshuffle up next
    reshuf_res = api_client.post("/api/playback/reshuffle-up-next")
    assert reshuf_res.status_code == 200
    assert "up_next" in reshuf_res.json()


def test_player_no_startfile_fallback(tmp_path):
    p = AudioPlayer(custom_aimp_path="nonexistent_path/aimp.exe")
    # Missing file returns False with specific error
    assert p.play("nonexistent_audio.mp3") is False
    assert "Audio file not found" in (p.last_error or "")

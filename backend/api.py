"""FastAPI route handlers for playback, library, playlists, and settings.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, Query, Response, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from backend.database import Database
from backend.folder_picker import open_windows_folder_dialog
from backend.import_export import ImportExportService
from backend.metadata import get_or_create_artwork_thumbnail
from backend.player import AudioPlayer
from backend.playlists import PlaylistService
from backend.scanner import LibraryScanner
from backend.shuffle_engine import ShuffleEngine


# Request / Response Schemas
class PlayFoldersRequest(BaseModel):
    folder_paths: List[str]


class RepeatRequest(BaseModel):
    repeats: int


class CreatePlaylistRequest(BaseModel):
    name: str
    description: Optional[str] = ""


class RenamePlaylistRequest(BaseModel):
    name: str


class AddTracksRequest(BaseModel):
    track_ids: List[int]


class ReorderEntriesRequest(BaseModel):
    entry_ids: List[int]


class AddRootRequest(BaseModel):
    path: str
    display_name: Optional[str] = None


class ExportRequest(BaseModel):
    playlist_ids: List[int]


class UpdateSettingsRequest(BaseModel):
    history_ratio: Optional[float] = None
    min_history_window: Optional[int] = None
    max_history_window: Optional[int] = None
    randomness_factor: Optional[float] = None
    custom_aimp_path: Optional[str] = None


class TrackRatingRequest(BaseModel):
    rating: int


class ToggleWholeDeckRequest(BaseModel):
    enable: Optional[bool] = None


class GenerateRandomPlaylistRequest(BaseModel):
    name: str = ""
    limit: int = 50
    folder_paths: Optional[List[str]] = None


class RefillPlaylistRequest(BaseModel):
    folder_paths: Optional[List[str]] = None


class CopyPlaylistPhysicalRequest(BaseModel):
    playlist_id: int
    destination_folder: str


class ExportRarRequest(BaseModel):
    playlist_id: int
    destination_folder: str


class SeekRequest(BaseModel):
    position: float  # Target position in seconds


class VolumeRequest(BaseModel):
    volume: int  # 0 to 100


def create_api_router(
    db: Database,
    player: AudioPlayer,
    engine: ShuffleEngine,
    scanner: LibraryScanner,
    playlist_service: PlaylistService,
    import_export_service: ImportExportService,
) -> APIRouter:
    """Builds and returns the configured FastAPI APIRouter."""
    router = APIRouter(prefix="/api")

    # -------------------------------------------------------------------------
    # Health & Diagnostics
    # -------------------------------------------------------------------------

    @router.get("/health")
    def get_health() -> Dict[str, Any]:
        return {"status": "ok", "app": "Shuffle Master", "version": "2.0.0"}

    # -------------------------------------------------------------------------
    # Playback Controls
    # -------------------------------------------------------------------------

    @router.get("/playback/state")
    def get_playback_state() -> Dict[str, Any]:
        state = engine.get_playback_state().to_dict()
        p_status = player.get_status().to_dict()
        state["player"] = p_status

        # Synchronize live AIMP playback timing and controls
        curr_track = state.get("current_track")
        fallback_dur = float(curr_track["duration"]) if curr_track and curr_track.get("duration") else 0.0
        aimp_dur = float(p_status.get("duration", 0.0))

        state["position_seconds"] = float(p_status.get("position", 0.0))
        state["duration_seconds"] = aimp_dur if aimp_dur > 0 else fallback_dur
        state["is_playing"] = p_status.get("state") == "playing"
        state["volume"] = int(p_status.get("volume", 100))
        state["aimp_connected"] = bool(p_status.get("aimp_connected", False))
        return state

    @router.post("/playback/next")
    def playback_next(was_skipped: bool = False) -> Dict[str, Any]:
        try:
            track = engine.next_track(was_skipped=was_skipped)
            player.play(track.canonical_path)
            state = engine.get_playback_state().to_dict()
            state["player"] = player.get_status().to_dict()
            return state
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/playback/prev")
    def playback_prev() -> Dict[str, Any]:
        prev_t = engine.previous_track()
        if not prev_t:
            raise HTTPException(status_code=400, detail="No previous track available in history.")
        player.play(prev_t.canonical_path)
        state = engine.get_playback_state().to_dict()
        state["player"] = player.get_status().to_dict()
        return state

    @router.post("/playback/shuffle-more")
    def playback_shuffle_more() -> Dict[str, Any]:
        try:
            track = engine.fresh_shuffle()
            player.play(track.canonical_path)
            state = engine.get_playback_state().to_dict()
            state["player"] = player.get_status().to_dict()
            return state
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/playback/pause")
    def playback_pause() -> Dict[str, Any]:
        curr = engine.get_playback_state().current_track
        curr_path = curr.canonical_path if curr else None
        success = player.pause(current_track_path=curr_path)
        return {"success": success}

    @router.post("/playback/resume")
    def playback_resume() -> Dict[str, Any]:
        curr = engine.get_playback_state().current_track
        curr_path = curr.canonical_path if curr else None
        success = player.resume(current_track_path=curr_path)
        return {"success": success}

    @router.post("/playback/seek")
    def playback_seek(req: SeekRequest) -> Dict[str, Any]:
        success = player.seek(req.position)
        return {
            "success": success,
            "position": player.get_position(),
            "duration": player.get_duration(),
        }

    @router.post("/playback/volume")
    def playback_volume(req: VolumeRequest) -> Dict[str, Any]:
        success = player.set_volume(req.volume)
        return {
            "success": success,
            "volume": player.get_volume(),
        }

    @router.post("/playback/toggle-whole-deck")
    def toggle_whole_deck(req: Optional[ToggleWholeDeckRequest] = None) -> Dict[str, Any]:
        enable = req.enable if req else None
        engine.toggle_shuffle_whole_deck(enable)
        state = engine.get_playback_state().to_dict()
        state["player"] = player.get_status().to_dict()
        return state

    @router.post("/playback/repeat")
    def playback_repeat(req: RepeatRequest) -> Dict[str, Any]:
        try:
            repeats = engine.set_repeat(req.repeats)
            curr = engine.get_playback_state().current_track
            if curr:
                player.play(curr.canonical_path)
            state = engine.get_playback_state().to_dict()
            state["player"] = player.get_status().to_dict()
            return state
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/playback/play-track/{track_id}")
    def play_track(track_id: int) -> Dict[str, Any]:
        try:
            track = engine.play_specific_track(track_id)
            player.play(track.canonical_path)
            state = engine.get_playback_state().to_dict()
            state["player"] = player.get_status().to_dict()
            return state
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/playback/play-library")
    def play_library(req: Optional[PlayFoldersRequest] = None) -> Dict[str, Any]:
        """Activates and plays library folder pool, returning playback state."""
        try:
            folders = req.folder_paths if req and req.folder_paths else None
            if not folders:
                saved = db.get_setting("selected_folders")
                if saved:
                    import json
                    try:
                        folders = json.loads(saved)
                    except Exception:
                        folders = None
            if not folders:
                eligible = scanner.get_eligible_folders()
                folders = [f.folder_path for f in eligible]
            
            if folders:
                pool_size = engine.set_folder_pool(folders)
                if pool_size > 0:
                    track = engine.next_track()
                    player.play(track.canonical_path)
                    state = engine.get_playback_state().to_dict()
                    state["player"] = player.get_status().to_dict()
                    return state

            # Fallback to full library pool if tracks exist in database
            all_tracks = db.get_all_tracks(only_available=True)
            if all_tracks:
                engine.set_full_library_pool()
                track = engine.next_track()
                player.play(track.canonical_path)
                state = engine.get_playback_state().to_dict()
                state["player"] = player.get_status().to_dict()
                return state

            raise HTTPException(status_code=400, detail="No eligible music folders or playable audio tracks found in library.")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.api_route("/playback/up-next", methods=["GET", "POST"])
    def get_up_next(limit: Optional[int] = None) -> Dict[str, Any]:
        tracks = engine.get_up_next(limit=limit)
        return {"up_next": [t.to_dict() for t in tracks]}

    @router.api_route("/playback/reshuffle-up-next", methods=["GET", "POST"])
    def reshuffle_up_next(limit: Optional[int] = None) -> Dict[str, Any]:
        tracks = engine.reshuffle_up_next(limit=limit)
        return {"up_next": [t.to_dict() for t in tracks]}

    @router.api_route("/lyrics", methods=["GET", "POST"])
    def fetch_lyrics(artist: str = "", title: str = "") -> Dict[str, Any]:
        from backend.lyrics import get_lyrics
        return get_lyrics(artist, title)

    @router.post("/playback/play-folders")
    def play_folders(req: PlayFoldersRequest) -> Dict[str, Any]:
        if not req.folder_paths:
            raise HTTPException(status_code=400, detail="No folders specified.")
        try:
            pool_size = engine.set_folder_pool(req.folder_paths)
            if pool_size == 0:
                raise HTTPException(status_code=400, detail="Selected folders contain no playable tracks.")
            track = engine.next_track()
            player.play(track.canonical_path)
            state = engine.get_playback_state().to_dict()
            state["player"] = player.get_status().to_dict()
            return state
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/playback/play-playlist/{playlist_id}")
    def play_playlist(playlist_id: int) -> Dict[str, Any]:
        try:
            pool_size = engine.set_playlist_pool(playlist_id)
            if pool_size == 0:
                raise HTTPException(status_code=400, detail="Playlist is empty or has no available tracks.")
            track = engine.next_track()
            player.play(track.canonical_path)
            state = engine.get_playback_state().to_dict()
            state["player"] = player.get_status().to_dict()
            return state
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    # -------------------------------------------------------------------------
    # Music Roots & Scanning
    # -------------------------------------------------------------------------

    @router.get("/library/roots")
    def get_roots() -> List[Dict[str, Any]]:
        roots = db.get_all_roots()
        return [r.to_dict() for r in roots]

    @router.post("/library/roots")
    def add_root(req: AddRootRequest) -> Dict[str, Any]:
        p = Path(req.path).resolve()
        if not p.exists() or not p.is_dir():
            raise HTTPException(status_code=400, detail="Directory not found or not a folder.")
        root = db.add_music_root(str(p), req.display_name)
        # Scan newly added root
        scanner.scan_directory(p)
        return root.to_dict()

    @router.delete("/library/roots/{root_id}")
    def delete_root(root_id: int) -> Dict[str, Any]:
        success = db.remove_music_root(root_id)
        return {"success": success}

    @router.post("/library/pick-folder")
    def pick_folder() -> Dict[str, Any]:
        """Launches native Windows folder picker dialog."""
        folder = open_windows_folder_dialog(title="Select Music Folder")
        return {"folder_path": folder}

    @router.post("/library/scan")
    def scan_library(root_id: Optional[int] = None) -> Dict[str, Any]:
        try:
            if root_id:
                roots = db.get_all_roots()
                match = next((r for r in roots if r.id == root_id), None)
                if not match:
                    raise HTTPException(status_code=404, detail="Root not found.")
                found, new_or_up, missing = scanner.scan_directory(match.path)
            else:
                found, new_or_up, missing = scanner.scan_all_roots()
            return {
                "total_found": found,
                "new_or_updated": new_or_up,
                "unavailable_marked": missing,
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/library/folders")
    def get_eligible_folders() -> List[Dict[str, Any]]:
        folders = scanner.get_eligible_folders()
        return [f.to_dict() for f in folders]

    @router.get("/library/tracks")
    def get_tracks(
        q: Optional[str] = None,
        folder: Optional[str] = None,
        limit: int = Query(default=100, le=500),
    ) -> List[Dict[str, Any]]:
        if q and q.strip():
            tracks = db.search_tracks(q.strip(), limit=limit, only_available=True)
        elif folder:
            tracks = db.get_tracks_in_folders([folder], only_available=True)
            if len(tracks) > limit:
                tracks = tracks[:limit]
        else:
            tracks = db.get_all_tracks(only_available=True)
            if len(tracks) > limit:
                tracks = tracks[:limit]
        return [t.to_dict() for t in tracks]

    @router.get("/library/track/{track_id}/artwork")
    def get_track_artwork(track_id: int) -> Response:
        track = db.get_track_by_id(track_id)
        if not track:
            raise HTTPException(status_code=404, detail="Track not found.")

        thumb_path = get_or_create_artwork_thumbnail(track_id, track.canonical_path)
        if not thumb_path or not thumb_path.exists():
            raise HTTPException(status_code=404, detail="No artwork found for track.")

        mime = "image/png" if thumb_path.suffix.lower() == ".png" else "image/jpeg"
        return FileResponse(path=str(thumb_path), media_type=mime)

    @router.post("/tracks/{track_id}/rating")
    def set_track_rating(track_id: int, req: TrackRatingRequest) -> Dict[str, Any]:
        success = db.set_track_rating(track_id, req.rating)
        if not success:
            raise HTTPException(status_code=404, detail="Track not found.")
        engine.update_track_rating(track_id, req.rating)
        return {"success": True, "track_id": track_id, "rating": req.rating}

    # -------------------------------------------------------------------------
    # Playlists
    # -------------------------------------------------------------------------

    @router.get("/playlists")
    def list_playlists() -> List[Dict[str, Any]]:
        return playlist_service.list_playlists()

    @router.post("/playlists")
    def create_playlist(req: CreatePlaylistRequest) -> Dict[str, Any]:
        try:
            return playlist_service.create_playlist(req.name, req.description or "")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.get("/playlists/{playlist_id}")
    def get_playlist(playlist_id: int) -> Dict[str, Any]:
        pl = playlist_service.get_playlist_details(playlist_id)
        if not pl:
            raise HTTPException(status_code=404, detail="Playlist not found.")
        return pl

    @router.put("/playlists/{playlist_id}")
    def rename_playlist(playlist_id: int, req: RenamePlaylistRequest) -> Dict[str, Any]:
        try:
            success = playlist_service.rename_playlist(playlist_id, req.name)
            return {"success": success}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.delete("/playlists/{playlist_id}")
    def delete_playlist(playlist_id: int) -> Dict[str, Any]:
        success = playlist_service.delete_playlist(playlist_id)
        return {"success": success}

    @router.post("/playlists/{playlist_id}/tracks")
    def add_tracks_to_playlist(playlist_id: int, req: AddTracksRequest) -> Dict[str, Any]:
        try:
            added = playlist_service.add_tracks(playlist_id, req.track_ids)
            return {"added_count": added}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.delete("/playlists/{playlist_id}/entries/{entry_id}")
    def remove_playlist_entry(playlist_id: int, entry_id: int) -> Dict[str, Any]:
        success = playlist_service.remove_entry(playlist_id, entry_id)
        return {"success": success}

    @router.put("/playlists/{playlist_id}/reorder")
    def reorder_playlist_entries(playlist_id: int, req: ReorderEntriesRequest) -> Dict[str, Any]:
        success = playlist_service.reorder_entries(playlist_id, req.entry_ids)
        return {"success": success}

    @router.post("/playlists/generate-random")
    def generate_random_playlist(req: GenerateRandomPlaylistRequest) -> Dict[str, Any]:
        try:
            return playlist_service.generate_random_playlist(
                name=req.name,
                limit=req.limit,
                folder_paths=req.folder_paths,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/playlists/{playlist_id}/refill")
    def refill_playlist(playlist_id: int, req: Optional[RefillPlaylistRequest] = None) -> Dict[str, Any]:
        try:
            folders = req.folder_paths if req else None
            return playlist_service.refill_random_playlist(
                playlist_id=playlist_id,
                folder_paths=folders,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # -------------------------------------------------------------------------
    # Listening History
    # -------------------------------------------------------------------------

    @router.get("/history")
    def get_history(limit: int = Query(default=50, le=200)) -> List[Dict[str, Any]]:
        return db.get_recent_history(limit=limit)

    # -------------------------------------------------------------------------
    # Import / Export
    # -------------------------------------------------------------------------

    @router.post("/export")
    def export_playlists(req: ExportRequest) -> StreamingResponse:
        if not req.playlist_ids:
            raise HTTPException(status_code=400, detail="No playlists selected for export.")
        zip_buf = import_export_service.export_playlists_to_zip(req.playlist_ids)
        return StreamingResponse(
            zip_buf,
            media_type="application/zip",
            headers={"Content-Disposition": 'attachment; filename="playlists_export.zip"'},
        )

    @router.post("/export/playlist/copy-folder")
    def copy_playlist_folder(req: CopyPlaylistPhysicalRequest) -> Dict[str, Any]:
        try:
            return import_export_service.copy_playlist_physically(
                playlist_id=req.playlist_id,
                target_directory=req.destination_folder,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/export/playlist/rar")
    def export_playlist_rar(req: ExportRarRequest) -> Dict[str, Any]:
        try:
            return import_export_service.export_playlist_as_rar(
                playlist_id=req.playlist_id,
                target_directory=req.destination_folder,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/import/preview")
    async def import_preview(file: UploadFile = File(...)) -> Dict[str, Any]:
        contents = await file.read()
        try:
            return import_export_service.preview_import_zip(contents)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/import/commit")
    async def import_commit(
        file: UploadFile = File(...),
        conflict_policy: str = Query(default="rename"),
        relink_root: Optional[str] = Query(default=None),
    ) -> Dict[str, Any]:
        contents = await file.read()
        try:
            return import_export_service.commit_import_zip(
                contents,
                conflict_policy=conflict_policy,
                relink_root=relink_root,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # -------------------------------------------------------------------------
    # Settings & Diagnostics
    # -------------------------------------------------------------------------

    @router.get("/settings")
    def get_settings() -> Dict[str, Any]:
        from backend.config import get_app_data_dir, get_db_path
        all_settings = db.get_all_settings()
        player_status = player.get_status().to_dict()
        roots = [r.to_dict() for r in db.get_all_roots()]
        all_tracks = db.get_all_tracks(only_available=True)

        return {
            "settings": all_settings,
            "shuffle_config": engine.config,
            "player": player_status,
            "roots": roots,
            "app_data_dir": str(get_app_data_dir()),
            "db_path": str(get_db_path()),
            "total_tracks": len(all_tracks),
            "total_playlists": len(db.list_playlists()),
        }

    @router.post("/settings")
    def update_settings(req: UpdateSettingsRequest) -> Dict[str, Any]:
        should_rebuild = False
        if req.history_ratio is not None:
            engine.config["history_ratio"] = max(0.05, min(0.90, req.history_ratio))
            db.set_setting("history_ratio", str(engine.config["history_ratio"]))
            should_rebuild = True
        if req.min_history_window is not None:
            engine.config["min_history_window"] = max(1, req.min_history_window)
            db.set_setting("min_history_window", str(engine.config["min_history_window"]))
            should_rebuild = True
        if req.max_history_window is not None:
            engine.config["max_history_window"] = max(5, req.max_history_window)
            db.set_setting("max_history_window", str(engine.config["max_history_window"]))
            should_rebuild = True
        if req.randomness_factor is not None:
            clamped = max(0.0, min(1.0, float(req.randomness_factor)))
            engine.config["randomness_factor"] = clamped
            db.set_setting("randomness_factor", str(clamped))
            should_rebuild = True
        if req.custom_aimp_path is not None:
            db.set_setting("custom_aimp_path", req.custom_aimp_path)
            player.aimp_path = Path(req.custom_aimp_path).resolve() if req.custom_aimp_path else player._discover_aimp()

        if should_rebuild and engine.eligible_tracks:
            engine._rebuild_deck(force=True)

        return {"status": "updated", "shuffle_config": engine.config}

    return router

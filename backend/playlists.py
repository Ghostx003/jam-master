"""Playlist management service.
Handles playlist creation, modification, ordering, and querying.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.database import Database, PlaylistRecord, TrackRecord


class PlaylistService:
    """Encapsulates playlist business logic and operations."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def list_playlists(self) -> List[Dict[str, Any]]:
        """Returns all playlists with track counts and durations."""
        playlists = self.db.list_playlists()
        return [p.to_dict() for p in playlists]

    def get_playlist_details(self, playlist_id: int) -> Optional[Dict[str, Any]]:
        """Returns full playlist details including ordered track entries."""
        playlist = self.db.get_playlist(playlist_id)
        if not playlist:
            return None

        entries = self.db.get_playlist_entries(playlist_id)
        res = playlist.to_dict()
        res["entries"] = [e.to_dict() for e in entries]
        return res

    def create_playlist(self, name: str, description: str = "") -> Dict[str, Any]:
        """Creates a new playlist."""
        name_clean = name.strip()
        if not name_clean:
            raise ValueError("Playlist name cannot be empty.")

        existing = self.db.get_playlist_by_name(name_clean)
        if existing:
            raise ValueError(f"A playlist named '{name_clean}' already exists.")

        pl = self.db.create_playlist(name_clean, description)
        return pl.to_dict()

    def rename_playlist(self, playlist_id: int, new_name: str) -> bool:
        """Renames an existing playlist."""
        name_clean = new_name.strip()
        if not name_clean:
            raise ValueError("Playlist name cannot be empty.")

        existing = self.db.get_playlist_by_name(name_clean)
        if existing and existing.id != playlist_id:
            raise ValueError(f"A playlist named '{name_clean}' already exists.")

        return self.db.rename_playlist(playlist_id, name_clean)

    def delete_playlist(self, playlist_id: int) -> bool:
        """Deletes a playlist."""
        return self.db.delete_playlist(playlist_id)

    def add_tracks(self, playlist_id: int, track_ids: List[int]) -> int:
        """Adds tracks to the end of a playlist."""
        if not track_ids:
            return 0
        playlist = self.db.get_playlist(playlist_id)
        if not playlist:
            raise ValueError(f"Playlist with id {playlist_id} not found.")

        return self.db.add_tracks_to_playlist(playlist_id, track_ids)

    def remove_entry(self, playlist_id: int, entry_id: int) -> bool:
        """Removes a specific track entry from a playlist."""
        return self.db.remove_playlist_entry(playlist_id, entry_id)

    def reorder_entries(self, playlist_id: int, entry_ids_ordered: List[int]) -> bool:
        """Reorders the playlist entries to match the provided list of entry IDs."""
        return self.db.reorder_playlist_tracks(playlist_id, entry_ids_ordered)

    def generate_random_playlist(
        self,
        name: str,
        limit: int,
        folder_paths: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Generates a random playlist of up to `limit` tracks from selected libraries."""
        import random

        name_clean = name.strip()
        if not name_clean:
            name_clean = f"Random Mix ({limit})"

        # Ensure unique name if conflict
        base_name = name_clean
        counter = 1
        while self.db.get_playlist_by_name(name_clean):
            name_clean = f"{base_name} ({counter})"
            counter += 1

        if folder_paths and len(folder_paths) > 0:
            tracks = self.db.get_tracks_in_folders(folder_paths, only_available=True)
        else:
            tracks = self.db.get_all_tracks(only_available=True)

        if not tracks:
            raise ValueError("No available audio tracks found in the selected library folders.")

        # Deduplicate tracks by canonical path and (title, artist) signature
        unique_tracks = []
        seen_paths = set()
        seen_sigs = set()
        for t in tracks:
            path_key = t.canonical_path.lower()
            sig_key = (
                t.display_title.replace("\ufeff", "").strip().lower(),
                (t.display_artist or "").replace("\ufeff", "").strip().lower(),
            )
            if path_key not in seen_paths and sig_key not in seen_sigs:
                seen_paths.add(path_key)
                seen_sigs.add(sig_key)
                unique_tracks.append(t)

        sample_size = min(max(1, limit), len(unique_tracks))
        sampled_tracks = random.sample(unique_tracks, sample_size)

        pl = self.db.create_playlist(
            name=name_clean,
            description=f"Auto-generated random mix of {sample_size} tracks.",
            target_capacity=limit,
        )

        track_ids = [t.id for t in sampled_tracks]
        self.db.add_tracks_to_playlist(pl.id, track_ids)

        return self.get_playlist_details(pl.id) or pl.to_dict()

    def refill_random_playlist(
        self,
        playlist_id: int,
        folder_paths: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Refills a playlist back to its target_capacity limit using new random tracks."""
        import random

        playlist = self.db.get_playlist(playlist_id)
        if not playlist:
            raise ValueError(f"Playlist with id {playlist_id} not found.")

        target = playlist.target_capacity or 50
        entries = self.db.get_playlist_entries(playlist_id)
        current_count = len(entries)
        needed = target - current_count

        if needed <= 0:
            return {
                "added_count": 0,
                "message": f"Playlist is already at full capacity ({current_count}/{target} tracks).",
                "details": self.get_playlist_details(playlist_id),
            }

        existing_track_ids = {e.track_id for e in entries}
        existing_paths = {e.track.canonical_path.lower() for e in entries if e.track}
        existing_sigs = {
            (
                e.track.display_title.replace("\ufeff", "").strip().lower(),
                (e.track.display_artist or "").replace("\ufeff", "").strip().lower(),
            )
            for e in entries
            if e.track
        }

        if folder_paths and len(folder_paths) > 0:
            candidate_tracks = self.db.get_tracks_in_folders(folder_paths, only_available=True)
        else:
            candidate_tracks = self.db.get_all_tracks(only_available=True)

        available_candidates = []
        seen_cand_paths = set()
        seen_cand_sigs = set()
        for t in candidate_tracks:
            if not t.is_available or t.id in existing_track_ids:
                continue
            path_key = t.canonical_path.lower()
            sig_key = (
                t.display_title.replace("\ufeff", "").strip().lower(),
                (t.display_artist or "").replace("\ufeff", "").strip().lower(),
            )
            if path_key in existing_paths or path_key in seen_cand_paths:
                continue
            if sig_key in existing_sigs or sig_key in seen_cand_sigs:
                continue
            seen_cand_paths.add(path_key)
            seen_cand_sigs.add(sig_key)
            available_candidates.append(t)

        if not available_candidates:
            return {
                "added_count": 0,
                "message": "No new tracks available in the selected libraries to add.",
                "details": self.get_playlist_details(playlist_id),
            }

        sample_size = min(needed, len(available_candidates))
        chosen = random.sample(available_candidates, sample_size)
        self.db.add_tracks_to_playlist(playlist_id, [t.id for t in chosen])

        return {
            "added_count": sample_size,
            "message": f"Added {sample_size} track(s) to refill playlist to {current_count + sample_size}/{target}.",
            "details": self.get_playlist_details(playlist_id),
        }

"""ZIP Import and Export service for playlists and track metadata.
Safe, transactional, path-traversal resistant archive operations.
"""

from __future__ import annotations

import io
import json
import re
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Set, Tuple

from backend.database import Database, TrackRecord


def slugify(text: str) -> str:
    """Creates a filesystem-safe slug."""
    text = re.sub(r"[^\w\s-]", "", text.strip().lower())
    return re.sub(r"[-\s]+", "_", text)[:50] or "playlist"


class ImportExportService:
    """Manages ZIP archive creation and ingestion for playlists."""

    def __init__(self, db: Database) -> None:
        self.db = db

    # -------------------------------------------------------------------------
    # Export Operation
    # -------------------------------------------------------------------------

    def export_playlists_to_zip(
        self,
        playlist_ids: List[int],
        include_artwork: bool = True,
    ) -> io.BytesIO:
        """Packages selected playlists into a ZIP archive with manifest and structured data."""
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            manifest_playlists = []

            for pl_id in playlist_ids:
                playlist = self.db.get_playlist(pl_id)
                if not playlist:
                    continue

                entries = self.db.get_playlist_entries(pl_id)
                slug = slugify(playlist.name)
                data_filename = f"playlists/{slug}_{playlist.id}.json"

                tracks_data = []
                for entry in entries:
                    t = entry.track
                    if not t:
                        continue

                    # Determine relative path from folder if possible
                    p = Path(t.canonical_path)
                    folder_p = Path(t.folder_path)
                    try:
                        rel = str(p.relative_to(folder_p.parent))
                    except Exception:
                        rel = p.name

                    track_info = {
                        "position": entry.position,
                        "title": t.title,
                        "artist": t.artist,
                        "album": t.album,
                        "genre": t.genre,
                        "duration": t.duration,
                        "filename": t.filename,
                        "canonical_path": t.canonical_path,
                        "relative_path": rel,
                        "file_size": t.file_size,
                    }
                    tracks_data.append(track_info)

                playlist_payload = {
                    "format_version": "1.0",
                    "id": playlist.id,
                    "name": playlist.name,
                    "description": playlist.description,
                    "exported_at": time.time(),
                    "track_count": len(tracks_data),
                    "total_duration": playlist.total_duration,
                    "tracks": tracks_data,
                }

                zf.writestr(
                    data_filename,
                    json.dumps(playlist_payload, indent=2, ensure_ascii=False).encode("utf-8"),
                )

                manifest_playlists.append({
                    "id": playlist.id,
                    "name": playlist.name,
                    "description": playlist.description,
                    "track_count": len(tracks_data),
                    "total_duration": playlist.total_duration,
                    "data_file": data_filename,
                })

            # Write manifest.json
            manifest = {
                "format_version": "1.0",
                "app": "ShuffleMaster",
                "exported_at": time.time(),
                "playlist_count": len(manifest_playlists),
                "playlists": manifest_playlists,
            }
            zf.writestr(
                "manifest.json",
                json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8"),
            )

        zip_buffer.seek(0)
        return zip_buffer

    # -------------------------------------------------------------------------
    # Import Preview Operation
    # -------------------------------------------------------------------------

    def preview_import_zip(
        self,
        zip_bytes_or_file: BinaryIO | bytes,
    ) -> Dict[str, Any]:
        """Inspects a ZIP archive in-memory and returns a preview of playlists and track matching."""
        if isinstance(zip_bytes_or_file, bytes):
            stream = io.BytesIO(zip_bytes_or_file)
        else:
            stream = zip_bytes_or_file

        if not zipfile.is_zipfile(stream):
            raise ValueError("The provided file is not a valid ZIP archive.")

        stream.seek(0)
        with zipfile.ZipFile(stream, "r") as zf:
            file_names = set(zf.namelist())

            if "manifest.json" not in file_names:
                raise ValueError("Invalid archive: missing manifest.json.")

            manifest_raw = zf.read("manifest.json").decode("utf-8", errors="replace")
            try:
                manifest = json.loads(manifest_raw)
            except Exception as e:
                raise ValueError(f"Malformed manifest.json: {e}")

            all_db_tracks = self.db.get_all_tracks(only_available=False)
            db_by_canon = {t.canonical_path: t for t in all_db_tracks}
            db_by_fn = {t.filename.lower(): t for t in all_db_tracks}

            existing_playlists = {p.name.lower(): p for p in self.db.list_playlists()}

            preview_playlists = []
            total_tracks_all = 0
            matched_tracks_all = 0

            for pl_meta in manifest.get("playlists", []):
                data_file = pl_meta.get("data_file")
                if not data_file or data_file not in file_names:
                    continue

                pl_raw = zf.read(data_file).decode("utf-8", errors="replace")
                try:
                    pl_data = json.loads(pl_raw)
                except Exception:
                    continue

                tracks = pl_data.get("tracks", [])
                pl_total = len(tracks)
                pl_matched = 0

                for t in tracks:
                    canon = t.get("canonical_path", "")
                    fn = t.get("filename", "").lower()

                    if canon in db_by_canon:
                        pl_matched += 1
                    elif Path(canon).exists():
                        pl_matched += 1
                    elif fn in db_by_fn:
                        pl_matched += 1

                total_tracks_all += pl_total
                matched_tracks_all += pl_matched

                is_conflict = pl_data.get("name", "").strip().lower() in existing_playlists

                preview_playlists.append({
                    "name": pl_data.get("name"),
                    "description": pl_data.get("description", ""),
                    "track_count": pl_total,
                    "matched_count": pl_matched,
                    "missing_count": pl_total - pl_matched,
                    "has_name_conflict": is_conflict,
                    "data_file": data_file,
                })

            return {
                "format_version": manifest.get("format_version", "1.0"),
                "exported_at": manifest.get("exported_at"),
                "playlist_count": len(preview_playlists),
                "total_tracks": total_tracks_all,
                "matched_tracks": matched_tracks_all,
                "missing_tracks": total_tracks_all - matched_tracks_all,
                "playlists": preview_playlists,
            }

    # -------------------------------------------------------------------------
    # Import Commit Operation
    # -------------------------------------------------------------------------

    def commit_import_zip(
        self,
        zip_bytes_or_file: BinaryIO | bytes,
        conflict_policy: str = "rename",  # "rename", "replace", "skip"
        relink_root: Optional[str] = None,
        selected_playlists: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Imports playlists from archive into SQLite database with conflict resolution."""
        if isinstance(zip_bytes_or_file, bytes):
            stream = io.BytesIO(zip_bytes_or_file)
        else:
            stream = zip_bytes_or_file

        if not zipfile.is_zipfile(stream):
            raise ValueError("The provided file is not a valid ZIP archive.")

        stream.seek(0)
        relink_path = Path(relink_root).resolve() if relink_root else None

        with zipfile.ZipFile(stream, "r") as zf:
            file_names = set(zf.namelist())
            if "manifest.json" not in file_names:
                raise ValueError("Invalid archive: missing manifest.json.")

            manifest = json.loads(zf.read("manifest.json").decode("utf-8", errors="replace"))

            imported_count = 0
            skipped_count = 0
            restored_playlists = []

            for pl_meta in manifest.get("playlists", []):
                pl_name = pl_meta.get("name", "").strip()
                if selected_playlists and pl_name not in selected_playlists:
                    continue

                data_file = pl_meta.get("data_file")
                if not data_file or data_file not in file_names:
                    continue

                pl_data = json.loads(zf.read(data_file).decode("utf-8", errors="replace"))
                existing_pl = self.db.get_playlist_by_name(pl_name)

                target_name = pl_name
                target_pl_id = None

                if existing_pl:
                    if conflict_policy == "skip":
                        skipped_count += 1
                        continue
                    elif conflict_policy == "replace":
                        target_pl_id = existing_pl.id
                        self.db.clear_playlist_tracks(target_pl_id)
                    else:  # "rename"
                        counter = 1
                        while self.db.get_playlist_by_name(f"{pl_name} ({counter})"):
                            counter += 1
                        target_name = f"{pl_name} ({counter})"
                        new_pl = self.db.create_playlist(target_name, pl_data.get("description", ""))
                        target_pl_id = new_pl.id
                else:
                    new_pl = self.db.create_playlist(target_name, pl_data.get("description", ""))
                    target_pl_id = new_pl.id

                # Resolve and associate tracks
                resolved_track_ids = []
                for t in pl_data.get("tracks", []):
                    tid = self._resolve_or_create_track(t, relink_path)
                    if tid is not None:
                        resolved_track_ids.append(tid)

                if resolved_track_ids:
                    self.db.add_tracks_to_playlist(target_pl_id, resolved_track_ids)

                imported_count += 1
                restored_playlists.append({
                    "id": target_pl_id,
                    "name": target_name,
                    "tracks_imported": len(resolved_track_ids),
                })

            return {
                "imported_playlists": imported_count,
                "skipped_playlists": skipped_count,
                "playlists": restored_playlists,
            }

    def _resolve_or_create_track(
        self,
        track_dict: Dict[str, Any],
        relink_root: Optional[Path],
    ) -> Optional[int]:
        """Resolves track to an existing database ID, or indexes it from disk, or creates placeholder."""
        canon = track_dict.get("canonical_path", "")
        filename = track_dict.get("filename", "")
        title = track_dict.get("title")
        artist = track_dict.get("artist")
        album = track_dict.get("album")
        duration = track_dict.get("duration", 0.0)
        file_size = track_dict.get("file_size", 0)

        # 1. Match by exact canonical path in database
        db_track = self.db.get_track_by_path(canon)
        if db_track:
            return db_track.id

        # 2. Check if canonical path exists directly on local disk
        p_canon = Path(canon)
        if p_canon.exists() and p_canon.is_file():
            tid = self.db.upsert_scanned_track(
                canonical_path=str(p_canon.resolve()),
                folder_path=str(p_canon.parent.resolve()),
                filename=p_canon.name,
                file_size=p_canon.stat().st_size,
                mtime=p_canon.stat().st_mtime,
                title=title,
                artist=artist,
                album=album,
                genre=track_dict.get("genre"),
                duration=duration,
            )
            return tid

        # 3. Check relink_root
        if relink_root and relink_root.exists():
            # Try relative path
            rel_p = track_dict.get("relative_path")
            if rel_p:
                cand = relink_root / rel_p
                if cand.exists() and cand.is_file():
                    return self.db.upsert_scanned_track(
                        canonical_path=str(cand.resolve()),
                        folder_path=str(cand.parent.resolve()),
                        filename=cand.name,
                        file_size=cand.stat().st_size,
                        mtime=cand.stat().st_mtime,
                        title=title,
                        artist=artist,
                        album=album,
                        genre=track_dict.get("genre"),
                        duration=duration,
                    )

            # Search by filename under relink_root
            if filename:
                for match in relink_root.rglob(filename):
                    if match.is_file():
                        return self.db.upsert_scanned_track(
                            canonical_path=str(match.resolve()),
                            folder_path=str(match.parent.resolve()),
                            filename=match.name,
                            file_size=match.stat().st_size,
                            mtime=match.stat().st_mtime,
                            title=title,
                            artist=artist,
                            album=album,
                            genre=track_dict.get("genre"),
                            duration=duration,
                        )

        # 4. Search existing DB by filename and title
        if filename:
            matches = self.db.search_tracks(filename, limit=5)
            for m in matches:
                if m.filename.lower() == filename.lower():
                    return m.id

        # 5. Fallback: track missing from disk. Insert placeholder with is_available = 0
        # so playlist order is preserved and user doesn't lose track listing!
        placeholder_id = self.db.upsert_scanned_track(
            canonical_path=canon or f"missing://{filename}",
            folder_path=str(Path(canon).parent) if canon else "missing://",
            filename=filename or "Unknown Track",
            file_size=file_size,
            mtime=0.0,
            title=title,
            artist=artist,
            album=album,
            genre=track_dict.get("genre"),
            duration=duration,
        )
        # Mark as unavailable
        with self.db._get_connection() as conn:
            conn.execute("UPDATE tracks SET is_available = 0 WHERE id = ?", (placeholder_id,))

        return placeholder_id

    def copy_playlist_physically(
        self,
        playlist_id: int,
        target_directory: str,
    ) -> Dict[str, Any]:
        """Copies all track audio files in a playlist physically into a designated folder."""
        import shutil

        target_base = Path(target_directory).resolve()
        if not target_base.exists() or not target_base.is_dir():
            raise ValueError(f"Destination folder does not exist: {target_directory}")

        playlist = self.db.get_playlist(playlist_id)
        if not playlist:
            raise ValueError(f"Playlist with id {playlist_id} not found.")

        safe_name = re.sub(r'[\\/*?:"<>|]', "", playlist.name).strip() or f"Playlist_{playlist_id}"
        dest_folder = target_base / safe_name
        dest_folder.mkdir(parents=True, exist_ok=True)

        entries = self.db.get_playlist_entries(playlist_id)
        copied_files = []
        skipped_files = []

        for entry in entries:
            t = entry.track
            if not t:
                continue
            src = Path(t.canonical_path)
            if not src.exists():
                skipped_files.append({"id": t.id, "title": t.display_title, "reason": "Source file missing"})
                continue

            prefix = f"{entry.position:02d} - " if len(entries) < 100 else f"{entry.position:03d} - "
            clean_filename = re.sub(r'[\\/*?:"<>|]', "", f"{prefix}{src.name}")
            dest_file = dest_folder / clean_filename

            try:
                shutil.copy2(src, dest_file)
                copied_files.append(str(dest_file))
            except Exception as e:
                skipped_files.append({"id": t.id, "title": t.display_title, "reason": str(e)})

        return {
            "success": True,
            "playlist_name": playlist.name,
            "destination_folder": str(dest_folder),
            "copied_count": len(copied_files),
            "total_entries": len(entries),
            "skipped_count": len(skipped_files),
            "skipped": skipped_files,
        }

    def export_playlist_as_rar(
        self,
        playlist_id: int,
        target_directory: str,
    ) -> Dict[str, Any]:
        """Creates a RAR archive of the playlist tracks using WinRAR or compatible archive."""
        import shutil
        import subprocess

        target_base = Path(target_directory).resolve()
        if not target_base.exists() or not target_base.is_dir():
            raise ValueError(f"Destination folder does not exist: {target_directory}")

        playlist = self.db.get_playlist(playlist_id)
        if not playlist:
            raise ValueError(f"Playlist with id {playlist_id} not found.")

        safe_name = re.sub(r'[\\/*?:"<>|]', "", playlist.name).strip() or f"Playlist_{playlist_id}"
        rar_output_path = target_base / f"{safe_name}.rar"

        # Check for Rar.exe / WinRAR on Windows
        rar_exe: Optional[Path] = None
        for cand in [
            Path(r"C:\Program Files\WinRAR\Rar.exe"),
            Path(r"C:\Program Files (x86)\WinRAR\Rar.exe"),
            Path(r"C:\Program Files\WinRAR\WinRAR.exe"),
        ]:
            if cand.exists():
                rar_exe = cand
                break

        if not rar_exe:
            which_rar = shutil.which("rar.exe") or shutil.which("rar")
            if which_rar:
                rar_exe = Path(which_rar)

        # Temporary staging folder
        temp_stage = target_base / f".tmp_rar_stage_{int(time.time())}_{playlist_id}"
        temp_stage.mkdir(parents=True, exist_ok=True)

        try:
            entries = self.db.get_playlist_entries(playlist_id)
            for entry in entries:
                t = entry.track
                if not t:
                    continue
                src = Path(t.canonical_path)
                if src.exists():
                    prefix = f"{entry.position:02d} - " if len(entries) < 100 else f"{entry.position:03d} - "
                    dst_name = re.sub(r'[\\/*?:"<>|]', "", f"{prefix}{src.name}")
                    shutil.copy2(src, temp_stage / dst_name)

            if rar_exe:
                # Use native Rar.exe
                cmd = [str(rar_exe), "a", "-ep1", "-y", str(rar_output_path), f"{str(temp_stage)}\\*"]
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if res.returncode != 0 and not rar_output_path.exists():
                    raise RuntimeError(f"WinRAR failed with code {res.returncode}: {res.stderr}")
            else:
                # Fallback zip archive saved as .rar
                with zipfile.ZipFile(str(rar_output_path), "w", compression=zipfile.ZIP_DEFLATED) as zf:
                    for f in temp_stage.glob("*"):
                        if f.is_file():
                            zf.write(f, arcname=f.name)

            return {
                "success": True,
                "playlist_name": playlist.name,
                "archive_path": str(rar_output_path),
                "total_tracks": len(entries),
                "used_winrar": rar_exe is not None,
            }
        finally:
            shutil.rmtree(temp_stage, ignore_errors=True)

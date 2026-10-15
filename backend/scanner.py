"""Filesystem scanner and incremental audio library indexer.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Tuple

from backend.config import get_supported_extensions
from backend.database import Database
from backend.metadata import extract_audio_metadata


@dataclass
class FolderSummary:
    """Summary of a folder containing valid audio tracks."""
    folder_path: str
    display_name: str
    track_count: int
    total_duration: float

    @property
    def formatted_duration(self) -> str:
        """Formats total duration into hours/minutes/seconds."""
        total_secs = int(self.total_duration)
        hrs = total_secs // 3600
        mins = (total_secs % 3600) // 60
        secs = total_secs % 60
        if hrs > 0:
            return f"{hrs}h {mins:02d}m"
        if mins > 0:
            return f"{mins}m {secs:02d}s"
        return f"{secs}s"

    def to_dict(self) -> Dict:
        return {
            "folder_path": self.folder_path,
            "display_name": self.display_name,
            "track_count": self.track_count,
            "total_duration": self.total_duration,
            "formatted_duration": self.formatted_duration,
        }


class LibraryScanner:
    """Discovers audio files dynamically and synchronizes them with the SQLite library."""

    def __init__(self, db: Database, supported_extensions: Optional[Set[str]] = None) -> None:
        self.db = db
        self.supported_extensions = (
            {ext.lower() for ext in supported_extensions}
            if supported_extensions
            else get_supported_extensions()
        )

    def scan_directory(
        self,
        root_dir: Path | str,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> Tuple[int, int, int]:
        """Recursively scans root_dir, incrementally updating the database.
        
        Args:
            root_dir: The root music directory to scan.
            progress_callback: Optional callback receiving (scanned_count, current_filename).
            
        Returns:
            Tuple of (total_found, new_or_updated, unavailable_marked).
        """
        root_path = Path(root_dir).resolve()
        if not root_path.exists() or not root_path.is_dir():
            raise ValueError(f"Directory does not exist or is not a directory: {root_dir}")

        canonical_root = str(root_path)
        known_meta = self.db.get_known_track_metadata()
        active_paths: Set[str] = set()
        visited_dirs: Set[str] = set()

        total_found = 0
        new_or_updated = 0

        # Walk directory preventing symlink loops
        for dirpath, dirnames, filenames in os.walk(canonical_root, followlinks=True):
            try:
                canonical_dir = str(Path(dirpath).resolve())
            except Exception:
                continue

            # Detect directory symlink recursion loops
            if canonical_dir in visited_dirs:
                dirnames.clear()
                continue
            visited_dirs.add(canonical_dir)

            for filename in filenames:
                ext = os.path.splitext(filename)[1].lower()
                if ext not in self.supported_extensions:
                    continue

                full_path = Path(dirpath) / filename
                try:
                    canonical_file_path = str(full_path.resolve())
                    stat = full_path.stat()
                    file_size = stat.st_size
                    mtime = stat.st_mtime
                except (OSError, PermissionError):
                    # Inaccessible or damaged file
                    continue

                total_found += 1
                active_paths.add(canonical_file_path)

                if progress_callback and total_found % 20 == 0:
                    progress_callback(total_found, filename)

                # Check if file is already indexed with matching size and mtime
                known = known_meta.get(canonical_file_path)
                if known is not None:
                    known_size, known_mtime = known
                    if known_size == file_size and abs(known_mtime - mtime) < 0.001:
                        continue

                # File is new or changed: extract tags and upsert
                meta = extract_audio_metadata(full_path)
                self.db.upsert_scanned_track(
                    canonical_path=canonical_file_path,
                    folder_path=canonical_dir,
                    filename=filename,
                    file_size=file_size,
                    mtime=mtime,
                    title=meta.title,
                    artist=meta.artist,
                    album=meta.album,
                    genre=meta.genre,
                    duration=meta.duration,
                )
                new_or_updated += 1

        # Mark missing files in the scanned hierarchy as unavailable
        unavailable_marked = self.db.mark_missing_tracks(active_paths, canonical_root)

        # Update root last_scanned_at timestamp if present in music_roots
        roots = self.db.get_all_roots()
        for r in roots:
            if Path(r.path).resolve() == root_path:
                self.db.update_root_scanned(r.id)

        return total_found, new_or_updated, unavailable_marked

    def scan_all_roots(
        self,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> Tuple[int, int, int]:
        """Scans all configured music roots."""
        roots = self.db.get_all_roots()
        total_found = 0
        total_new = 0
        total_missing = 0

        for root in roots:
            p = Path(root.path)
            if p.exists() and p.is_dir():
                found, new, missing = self.scan_directory(p, progress_callback)
                total_found += found
                total_new += new
                total_missing += missing

        return total_found, total_new, total_missing

    def get_eligible_folders(self, base_dir: Optional[Path | str] = None) -> List[FolderSummary]:
        """Returns non-empty folders containing supported audio files.
        
        If base_dir is given, display names are formatted relative to base_dir.
        """
        base_path = Path(base_dir).resolve() if base_dir else None
        raw_folders = self.db.get_all_eligible_folders()
        summaries: List[FolderSummary] = []

        for item in raw_folders:
            folder_path = item["folder_path"]
            p = Path(folder_path)

            if base_path:
                try:
                    rel = p.relative_to(base_path)
                    display_name = str(rel) if str(rel) != "." else f"{p.name} (Root)"
                except ValueError:
                    display_name = p.name or str(p)
            else:
                display_name = p.name or str(p)

            summaries.append(
                FolderSummary(
                    folder_path=folder_path,
                    display_name=display_name,
                    track_count=item["track_count"],
                    total_duration=item["total_duration"],
                )
            )

        return summaries

    def discover_folders_fast(self, root_dir: Path | str) -> List[FolderSummary]:
        """Rapidly discovers folders containing supported audio files in under a second.
        
        Uses os.scandir without opening files or extracting mutagen metadata upfront.
        """
        root_path = Path(root_dir).resolve()
        if not root_path.exists() or not root_path.is_dir():
            return []

        folder_counts: Dict[str, int] = {}
        visited_dirs: Set[str] = set()

        def _fast_walk(current_dir: str) -> None:
            try:
                real_dir = str(Path(current_dir).resolve())
            except Exception:
                return

            if real_dir in visited_dirs:
                return
            visited_dirs.add(real_dir)

            audio_count = 0
            subdirs: List[str] = []

            try:
                with os.scandir(real_dir) as entries:
                    for entry in entries:
                        try:
                            if entry.is_dir(follow_symlinks=False):
                                subdirs.append(entry.path)
                            elif entry.is_file():
                                _, ext = os.path.splitext(entry.name)
                                if ext.lower() in self.supported_extensions:
                                    audio_count += 1
                        except OSError:
                            continue
            except (OSError, PermissionError):
                return

            if audio_count > 0:
                folder_counts[real_dir] = audio_count

            for sd in subdirs:
                _fast_walk(sd)

        _fast_walk(str(root_path))

        summaries: List[FolderSummary] = []
        for folder_path, count in sorted(folder_counts.items()):
            p = Path(folder_path)
            try:
                rel = p.relative_to(root_path)
                display_name = str(rel) if str(rel) != "." else f"{p.name} (Root)"
            except ValueError:
                display_name = p.name or str(p)

            summaries.append(
                FolderSummary(
                    folder_path=folder_path,
                    display_name=display_name,
                    track_count=count,
                    total_duration=0.0,
                )
            )

        return summaries

    def scan_selected_folders(
        self,
        folder_paths: List[str],
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> Tuple[int, int]:
        """Indexes only the selected folders with batch database transactions."""
        known_meta = self.db.get_known_track_metadata()
        total_found = 0
        total_new_or_updated = 0

        for folder_path in folder_paths:
            p = Path(folder_path).resolve()
            if not p.exists() or not p.is_dir():
                continue

            canonical_dir = str(p)
            batch_tuples = []

            try:
                with os.scandir(canonical_dir) as entries:
                    for entry in entries:
                        try:
                            if not entry.is_file():
                                continue
                            _, ext = os.path.splitext(entry.name)
                            if ext.lower() not in self.supported_extensions:
                                continue

                            canonical_file_path = str(Path(entry.path).resolve())
                            stat = entry.stat()
                            file_size = stat.st_size
                            mtime = stat.st_mtime
                        except (OSError, PermissionError):
                            continue

                        total_found += 1

                        known = known_meta.get(canonical_file_path)
                        if known is not None:
                            known_size, known_mtime = known
                            if known_size == file_size and abs(known_mtime - mtime) < 0.001:
                                continue

                        meta = extract_audio_metadata(Path(entry.path))
                        batch_tuples.append((
                            canonical_file_path,
                            canonical_dir,
                            entry.name,
                            file_size,
                            mtime,
                            meta.title,
                            meta.artist,
                            meta.album,
                            meta.genre,
                            meta.duration,
                        ))
            except (OSError, PermissionError):
                continue

            if batch_tuples:
                self.db.upsert_scanned_tracks_batch(batch_tuples)
                total_new_or_updated += len(batch_tuples)

        return total_found, total_new_or_updated


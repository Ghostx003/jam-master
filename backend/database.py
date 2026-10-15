"""SQLite database management, schema migration, and persistence layer.
Zero ratings or likes. Strict compliance with local persistence requirements.
"""

from __future__ import annotations

import os
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class TrackRecord:
    """Represents a persisted audio track in the database."""
    id: int
    canonical_path: str
    folder_path: str
    filename: str
    file_size: int
    mtime: float
    title: Optional[str]
    artist: Optional[str]
    album: Optional[str]
    genre: Optional[str]
    duration: float
    play_count: int
    last_played_at: Optional[float]
    skip_count: int
    is_available: bool = True
    rating: int = 0

    @property
    def display_title(self) -> str:
        """Sensible display title: uses tag title if present, otherwise clean filename."""
        if self.title and self.title.strip():
            return self.title.strip()
        p = Path(self.filename)
        return p.stem

    @property
    def display_artist(self) -> str:
        """Display artist or empty string if unknown."""
        return self.artist.strip() if self.artist and self.artist.strip() else ""

    @property
    def display_duration(self) -> str:
        """Formatted mm:ss or hh:mm:ss string."""
        if not self.duration or self.duration <= 0:
            return "--:--"
        total_secs = int(self.duration)
        hrs = total_secs // 3600
        mins = (total_secs % 3600) // 60
        secs = total_secs % 60
        if hrs > 0:
            return f"{hrs:d}:{mins:02d}:{secs:02d}"
        return f"{mins:02d}:{secs:02d}"

    def to_dict(self) -> Dict[str, Any]:
        """Serializes track to dictionary."""
        return {
            "id": self.id,
            "canonical_path": self.canonical_path,
            "folder_path": self.folder_path,
            "filename": self.filename,
            "file_size": self.file_size,
            "mtime": self.mtime,
            "title": self.title,
            "artist": self.artist,
            "album": self.album,
            "genre": self.genre,
            "duration": self.duration,
            "display_title": self.display_title,
            "display_artist": self.display_artist,
            "display_duration": self.display_duration,
            "play_count": self.play_count,
            "last_played_at": self.last_played_at,
            "skip_count": self.skip_count,
            "is_available": self.is_available,
            "rating": self.rating,
        }


@dataclass
class MusicRootRecord:
    """Represents a configured root directory for scanning."""
    id: int
    path: str
    display_name: str
    created_at: float
    last_scanned_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "path": self.path,
            "display_name": self.display_name,
            "created_at": self.created_at,
            "last_scanned_at": self.last_scanned_at,
        }


@dataclass
class PlaylistRecord:
    """Represents a user-curated playlist."""
    id: int
    name: str
    description: str
    created_at: float
    updated_at: float
    track_count: int = 0
    total_duration: float = 0.0
    target_capacity: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "track_count": self.track_count,
            "total_duration": self.total_duration,
            "target_capacity": self.target_capacity,
        }


@dataclass
class PlaylistEntry:
    """Represents an ordered track in a playlist."""
    id: int
    playlist_id: int
    track_id: int
    position: int
    added_at: float
    track: Optional[TrackRecord] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "playlist_id": self.playlist_id,
            "track_id": self.track_id,
            "position": self.position,
            "added_at": self.added_at,
            "track": self.track.to_dict() if self.track else None,
        }


class Database:
    """Thread-safe, transactional SQLite manager."""

    def __init__(self, db_path: Optional[Path | str] = None) -> None:
        from backend.config import get_db_path
        if db_path is None:
            self.db_path = get_db_path()
        elif isinstance(db_path, str) and db_path == ":memory:":
            self.db_path = Path(":memory:")
        else:
            self.db_path = Path(db_path)

        if str(self.db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        """Returns a configured SQLite connection with foreign keys and WAL mode."""
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_schema(self) -> None:
        """Initializes database tables, indices, and runs migrations."""
        with self._get_connection() as conn:
            # 1. Base tables
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS music_roots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT UNIQUE NOT NULL,
                    display_name TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    last_scanned_at REAL
                );

                CREATE TABLE IF NOT EXISTS tracks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    canonical_path TEXT UNIQUE NOT NULL,
                    folder_path TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    mtime REAL NOT NULL,
                    title TEXT,
                    artist TEXT,
                    album TEXT,
                    genre TEXT,
                    duration REAL DEFAULT 0.0,
                    play_count INTEGER DEFAULT 0 NOT NULL,
                    last_played_at REAL,
                    skip_count INTEGER DEFAULT 0 NOT NULL,
                    is_available INTEGER DEFAULT 1 NOT NULL,
                    rating INTEGER DEFAULT 0 NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_tracks_canonical ON tracks(canonical_path);
                CREATE INDEX IF NOT EXISTS idx_tracks_folder ON tracks(folder_path);
                CREATE INDEX IF NOT EXISTS idx_tracks_available ON tracks(is_available);

                CREATE TABLE IF NOT EXISTS play_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    track_id INTEGER NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
                    played_at REAL NOT NULL,
                    was_skipped INTEGER DEFAULT 0 NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_history_track ON play_history(track_id);
                CREATE INDEX IF NOT EXISTS idx_history_played ON play_history(played_at);

                CREATE TABLE IF NOT EXISTS playlists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT DEFAULT '',
                    target_capacity INTEGER,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS playlist_tracks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    playlist_id INTEGER NOT NULL REFERENCES playlists(id) ON DELETE CASCADE,
                    track_id INTEGER NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
                    position INTEGER NOT NULL,
                    added_at REAL NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_playlist_tracks_order ON playlist_tracks(playlist_id, position);
            """)

            # 2. Schema migrations for rating and target_capacity
            cursor = conn.execute("PRAGMA table_info(tracks)")
            columns = [row["name"] for row in cursor.fetchall()]
            if "rating" not in columns:
                try:
                    conn.execute("ALTER TABLE tracks ADD COLUMN rating INTEGER DEFAULT 0 NOT NULL")
                except sqlite3.OperationalError:
                    pass

            cursor_pl = conn.execute("PRAGMA table_info(playlists)")
            columns_pl = [row["name"] for row in cursor_pl.fetchall()]
            if "target_capacity" not in columns_pl:
                try:
                    conn.execute("ALTER TABLE playlists ADD COLUMN target_capacity INTEGER")
                except sqlite3.OperationalError:
                    pass

            # 3. Migrate legacy 'saved_music_dir' setting to music_roots if table is empty
            row = conn.execute("SELECT COUNT(*) as cnt FROM music_roots").fetchone()
            if row and row["cnt"] == 0:
                saved_dir = conn.execute("SELECT value FROM settings WHERE key = 'saved_music_dir'").fetchone()
                if saved_dir and saved_dir["value"]:
                    dir_path = saved_dir["value"]
                    p = Path(dir_path)
                    conn.execute(
                        "INSERT OR IGNORE INTO music_roots (path, display_name, created_at) VALUES (?, ?, ?)",
                        (str(p.resolve()), p.name or str(p), time.time()),
                    )

    # -------------------------------------------------------------------------
    # Settings Management
    # -------------------------------------------------------------------------

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Retrieves a configuration value from the settings table."""
        with self._get_connection() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
            return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        """Upserts a setting value."""
        now = time.time()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO settings (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
                """,
                (key, value, now),
            )

    def delete_setting(self, key: str) -> None:
        """Removes a setting."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM settings WHERE key = ?", (key,))

    def get_all_settings(self) -> Dict[str, str]:
        """Returns all persisted settings."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT key, value FROM settings")
            return {row["key"]: row["value"] for row in cursor}

    # -------------------------------------------------------------------------
    # Music Roots Management
    # -------------------------------------------------------------------------

    def get_all_roots(self) -> List[MusicRootRecord]:
        """Returns all configured music root directories."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM music_roots ORDER BY created_at ASC")
            return [
                MusicRootRecord(
                    id=row["id"],
                    path=row["path"],
                    display_name=row["display_name"],
                    created_at=row["created_at"],
                    last_scanned_at=row["last_scanned_at"],
                )
                for row in cursor
            ]

    def add_music_root(self, root_path: str, display_name: Optional[str] = None) -> MusicRootRecord:
        """Adds a new music root directory."""
        p = Path(root_path).resolve()
        canon = str(p)
        name = display_name or p.name or canon
        now = time.time()
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO music_roots (path, display_name, created_at)
                VALUES (?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET display_name = excluded.display_name
                """,
                (canon, name, now),
            )
            # Retrieve record
            row = conn.execute("SELECT * FROM music_roots WHERE path = ?", (canon,)).fetchone()
            return MusicRootRecord(
                id=row["id"],
                path=row["path"],
                display_name=row["display_name"],
                created_at=row["created_at"],
                last_scanned_at=row["last_scanned_at"],
            )

    def remove_music_root(self, root_id: int) -> bool:
        """Removes a music root. Does NOT delete user playlists or listening history."""
        with self._get_connection() as conn:
            res = conn.execute("DELETE FROM music_roots WHERE id = ?", (root_id,))
            return res.rowcount > 0

    def update_root_scanned(self, root_id: int) -> None:
        """Updates the last_scanned_at timestamp for a root."""
        now = time.time()
        with self._get_connection() as conn:
            conn.execute("UPDATE music_roots SET last_scanned_at = ? WHERE id = ?", (now, root_id))

    # -------------------------------------------------------------------------
    # Track Synchronization & Persistence
    # -------------------------------------------------------------------------

    def get_known_track_metadata(self) -> Dict[str, Tuple[int, float]]:
        """Returns a mapping of canonical_path -> (file_size, mtime) for existing tracks."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT canonical_path, file_size, mtime FROM tracks")
            return {row["canonical_path"]: (row["file_size"], row["mtime"]) for row in cursor}

    def upsert_scanned_track(
        self,
        canonical_path: str,
        folder_path: str,
        filename: str,
        file_size: int,
        mtime: float,
        title: Optional[str],
        artist: Optional[str],
        album: Optional[str],
        genre: Optional[str],
        duration: float,
    ) -> int:
        """Inserts or updates audio metadata without resetting play counts."""
        now = time.time()
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO tracks (
                    canonical_path, folder_path, filename, file_size, mtime,
                    title, artist, album, genre, duration, is_available,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                ON CONFLICT(canonical_path) DO UPDATE SET
                    folder_path = excluded.folder_path,
                    filename = excluded.filename,
                    file_size = excluded.file_size,
                    mtime = excluded.mtime,
                    title = excluded.title,
                    artist = excluded.artist,
                    album = excluded.album,
                    genre = excluded.genre,
                    duration = excluded.duration,
                    is_available = 1,
                    updated_at = excluded.updated_at
                RETURNING id
                """,
                (
                    canonical_path,
                    folder_path,
                    filename,
                    file_size,
                    mtime,
                    title,
                    artist,
                    album,
                    genre,
                    duration,
                    now,
                    now,
                ),
            )
            row = cursor.fetchone()
            return row["id"] if row else 0

    def upsert_scanned_tracks_batch(
        self,
        track_tuples: List[Tuple[str, str, str, int, float, Optional[str], Optional[str], Optional[str], Optional[str], float]],
    ) -> int:
        """Batch inserts or updates audio metadata inside a single transaction."""
        if not track_tuples:
            return 0
        now = time.time()
        rows = [
            (
                t[0], t[1], t[2], t[3], t[4],
                t[5], t[6], t[7], t[8], t[9],
                1, now, now
            )
            for t in track_tuples
        ]
        with self._get_connection() as conn:
            conn.executemany(
                """
                INSERT INTO tracks (
                    canonical_path, folder_path, filename, file_size, mtime,
                    title, artist, album, genre, duration, is_available,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(canonical_path) DO UPDATE SET
                    folder_path = excluded.folder_path,
                    filename = excluded.filename,
                    file_size = excluded.file_size,
                    mtime = excluded.mtime,
                    title = excluded.title,
                    artist = excluded.artist,
                    album = excluded.album,
                    genre = excluded.genre,
                    duration = excluded.duration,
                    is_available = 1,
                    updated_at = excluded.updated_at
                """,
                rows,
            )
        return len(rows)

    def mark_missing_tracks(self, active_canonical_paths: Set[str], base_dir: str) -> int:
        """Marks tracks under base_dir not found in current scan as unavailable."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, canonical_path FROM tracks WHERE canonical_path LIKE ? AND is_available = 1",
                (f"{base_dir}%",),
            )
            to_mark = [row["id"] for row in cursor if row["canonical_path"] not in active_canonical_paths]
            if to_mark:
                conn.executemany(
                    "UPDATE tracks SET is_available = 0, updated_at = ? WHERE id = ?",
                    [(time.time(), track_id) for track_id in to_mark],
                )
            return len(to_mark)

    # -------------------------------------------------------------------------
    # Track Retrieval
    # -------------------------------------------------------------------------

    def get_track_by_id(self, track_id: int) -> Optional[TrackRecord]:
        """Fetches a single track by ID."""
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM tracks WHERE id = ?", (track_id,)).fetchone()
            return self._row_to_track(row) if row else None

    def get_track_by_path(self, canonical_path: str) -> Optional[TrackRecord]:
        """Fetches a track by canonical path."""
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM tracks WHERE canonical_path = ?", (canonical_path,)).fetchone()
            return self._row_to_track(row) if row else None

    def get_tracks_in_folders(self, folder_paths: List[str], only_available: bool = True) -> List[TrackRecord]:
        """Retrieves all tracks belonging to any of the specified folder paths."""
        if not folder_paths:
            return []

        placeholders = ",".join("?" for _ in folder_paths)
        query = f"SELECT * FROM tracks WHERE folder_path IN ({placeholders})"
        params: List[Any] = list(folder_paths)

        if only_available:
            query += " AND is_available = 1"

        query += " ORDER BY folder_path, filename"

        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            return [self._row_to_track(r) for r in cursor]

    def get_all_tracks(self, only_available: bool = True) -> List[TrackRecord]:
        """Returns all tracks in the database."""
        query = "SELECT * FROM tracks"
        if only_available:
            query += " WHERE is_available = 1"
        query += " ORDER BY title ASC, filename ASC"

        with self._get_connection() as conn:
            cursor = conn.execute(query)
            return [self._row_to_track(r) for r in cursor]

    def search_tracks(self, query: str, limit: int = 100, only_available: bool = True) -> List[TrackRecord]:
        """Searches tracks across title, artist, album, and filename."""
        pattern = f"%{query}%"
        sql = """
            SELECT * FROM tracks
            WHERE (title LIKE ? OR artist LIKE ? OR album LIKE ? OR filename LIKE ?)
        """
        params: List[Any] = [pattern, pattern, pattern, pattern]
        if only_available:
            sql += " AND is_available = 1"
        sql += " ORDER BY title ASC, filename ASC LIMIT ?"
        params.append(limit)

        with self._get_connection() as conn:
            cursor = conn.execute(sql, params)
            return [self._row_to_track(r) for r in cursor]

    def get_all_eligible_folders(self) -> List[Dict[str, Any]]:
        """Returns folder summaries for all folders containing at least one available track."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT folder_path, COUNT(*) as track_count, SUM(duration) as total_duration
                FROM tracks
                WHERE is_available = 1
                GROUP BY folder_path
                HAVING COUNT(*) > 0
                ORDER BY folder_path ASC
                """
            )
            return [
                {
                    "folder_path": row["folder_path"],
                    "track_count": row["track_count"],
                    "total_duration": row["total_duration"] or 0.0,
                }
                for row in cursor
            ]

    # -------------------------------------------------------------------------
    # History Mutation & Retrieval
    # -------------------------------------------------------------------------

    def record_play(self, track_id: int, was_skipped: bool = False) -> None:
        """Records a track play event, increments play counter, updates last_played_at."""
        now = time.time()
        with self._get_connection() as conn:
            if was_skipped:
                conn.execute(
                    """
                    UPDATE tracks
                    SET play_count = play_count + 1,
                        skip_count = skip_count + 1,
                        last_played_at = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (now, now, track_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE tracks
                    SET play_count = play_count + 1,
                        last_played_at = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (now, now, track_id),
                )
            conn.execute(
                "INSERT INTO play_history (track_id, played_at, was_skipped) VALUES (?, ?, ?)",
                (track_id, now, 1 if was_skipped else 0),
            )

    def record_skip(self, track_id: int) -> None:
        """Records a skip event for track."""
        now = time.time()
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE tracks SET skip_count = skip_count + 1, updated_at = ? WHERE id = ?",
                (now, track_id),
            )
            conn.execute(
                """
                UPDATE play_history
                SET was_skipped = 1
                WHERE id = (
                    SELECT id FROM play_history
                    WHERE track_id = ?
                    ORDER BY played_at DESC LIMIT 1
                )
                """,
                (track_id,),
            )

    def get_recent_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns recent play history in reverse chronological order with track details."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT h.id as history_id, h.played_at, h.was_skipped, t.*
                FROM play_history h
                JOIN tracks t ON h.track_id = t.id
                ORDER BY h.played_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            results = []
            for row in cursor:
                track = self._row_to_track(row)
                results.append({
                    "history_id": row["history_id"],
                    "played_at": row["played_at"],
                    "was_skipped": bool(row["was_skipped"]),
                    "track": track.to_dict(),
                })
            return results

    # -------------------------------------------------------------------------
    # Playlist Management
    # -------------------------------------------------------------------------

    def create_playlist(
        self,
        name: str,
        description: str = "",
        target_capacity: Optional[int] = None,
    ) -> PlaylistRecord:
        """Creates a new playlist with optional target capacity."""
        name_clean = name.strip()
        if not name_clean:
            raise ValueError("Playlist name cannot be empty.")

        now = time.time()
        with self._get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO playlists (name, description, target_capacity, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (name_clean, description.strip(), target_capacity, now, now),
            )
            return PlaylistRecord(
                id=cursor.lastrowid,
                name=name_clean,
                description=description.strip(),
                created_at=now,
                updated_at=now,
                track_count=0,
                total_duration=0.0,
                target_capacity=target_capacity,
            )

    def set_playlist_capacity(self, playlist_id: int, target_capacity: Optional[int]) -> bool:
        """Updates the target capacity limit for a playlist."""
        now = time.time()
        with self._get_connection() as conn:
            res = conn.execute(
                "UPDATE playlists SET target_capacity = ?, updated_at = ? WHERE id = ?",
                (target_capacity, now, playlist_id),
            )
            return res.rowcount > 0

    def set_track_rating(self, track_id: int, rating: int) -> bool:
        """Sets a 0-5 star rating on a track."""
        val = max(0, min(5, int(rating)))
        now = time.time()
        with self._get_connection() as conn:
            res = conn.execute(
                "UPDATE tracks SET rating = ?, updated_at = ? WHERE id = ?",
                (val, now, track_id),
            )
            conn.commit()
            return res.rowcount > 0

    def rename_playlist(self, playlist_id: int, new_name: str) -> bool:
        """Renames a playlist."""
        clean_name = new_name.strip()
        if not clean_name:
            raise ValueError("Playlist name cannot be empty.")
        now = time.time()
        with self._get_connection() as conn:
            res = conn.execute(
                "UPDATE playlists SET name = ?, updated_at = ? WHERE id = ?",
                (clean_name, now, playlist_id),
            )
            return res.rowcount > 0

    def delete_playlist(self, playlist_id: int) -> bool:
        """Deletes a playlist and its track references."""
        with self._get_connection() as conn:
            res = conn.execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))
            return res.rowcount > 0

    def get_playlist(self, playlist_id: int) -> Optional[PlaylistRecord]:
        """Fetches a playlist by ID with track count and duration."""
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT p.*,
                       COUNT(pt.id) as track_count,
                       COALESCE(SUM(t.duration), 0.0) as total_duration
                FROM playlists p
                LEFT JOIN playlist_tracks pt ON p.id = pt.playlist_id
                LEFT JOIN tracks t ON pt.track_id = t.id
                WHERE p.id = ?
                GROUP BY p.id
                """,
                (playlist_id,),
            ).fetchone()
            if not row:
                return None
            return PlaylistRecord(
                id=row["id"],
                name=row["name"],
                description=row["description"] or "",
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                track_count=row["track_count"],
                total_duration=row["total_duration"],
                target_capacity=row["target_capacity"] if "target_capacity" in row.keys() else None,
            )

    def get_playlist_by_name(self, name: str) -> Optional[PlaylistRecord]:
        """Fetches a playlist by name."""
        with self._get_connection() as conn:
            row = conn.execute("SELECT id FROM playlists WHERE name = ?", (name.strip(),)).fetchone()
            if not row:
                return None
            return self.get_playlist(row["id"])

    def list_playlists(self) -> List[PlaylistRecord]:
        """Lists all playlists with track counts and total durations."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT p.*,
                       COUNT(pt.id) as track_count,
                       COALESCE(SUM(t.duration), 0.0) as total_duration
                FROM playlists p
                LEFT JOIN playlist_tracks pt ON p.id = pt.playlist_id
                LEFT JOIN tracks t ON pt.track_id = t.id
                GROUP BY p.id
                ORDER BY p.name ASC
                """
            )
            return [
                PlaylistRecord(
                    id=row["id"],
                    name=row["name"],
                    description=row["description"] or "",
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    track_count=row["track_count"],
                    total_duration=row["total_duration"],
                    target_capacity=row["target_capacity"] if "target_capacity" in row.keys() else None,
                )
                for row in cursor
            ]

    def get_playlist_entries(self, playlist_id: int) -> List[PlaylistEntry]:
        """Returns the ordered track entries in a playlist."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT pt.id as entry_id, pt.playlist_id, pt.track_id, pt.position, pt.added_at,
                       t.*
                FROM playlist_tracks pt
                JOIN tracks t ON pt.track_id = t.id
                WHERE pt.playlist_id = ?
                ORDER BY pt.position ASC, pt.id ASC
                """,
                (playlist_id,),
            )
            entries = []
            for row in cursor:
                track = self._row_to_track(row)
                entries.append(
                    PlaylistEntry(
                        id=row["entry_id"],
                        playlist_id=row["playlist_id"],
                        track_id=row["track_id"],
                        position=row["position"],
                        added_at=row["added_at"],
                        track=track,
                    )
                )
            return entries

    def add_tracks_to_playlist(self, playlist_id: int, track_ids: List[int]) -> int:
        """Appends tracks to the end of a playlist, preventing duplicates."""
        if not track_ids:
            return 0

        now = time.time()
        with self._get_connection() as conn:
            # Check existing tracks in this playlist to prevent duplicates
            cursor = conn.execute(
                """
                SELECT pt.track_id, t.canonical_path, t.title, t.artist
                FROM playlist_tracks pt
                JOIN tracks t ON pt.track_id = t.id
                WHERE pt.playlist_id = ?
                """,
                (playlist_id,),
            )
            existing_tids = set()
            existing_paths = set()
            existing_sigs = set()
            for r in cursor:
                existing_tids.add(r["track_id"])
                existing_paths.add(r["canonical_path"].lower())
                existing_sigs.add((
                    (r["title"] or "").replace("\ufeff", "").strip().lower(),
                    (r["artist"] or "").replace("\ufeff", "").strip().lower(),
                ))

            unique_new_tids: List[int] = []
            for tid in track_ids:
                if tid in existing_tids or tid in unique_new_tids:
                    continue
                t_row = conn.execute(
                    "SELECT canonical_path, title, artist FROM tracks WHERE id = ?",
                    (tid,),
                ).fetchone()
                if not t_row:
                    continue
                path_key = t_row["canonical_path"].lower()
                sig_key = (
                    (t_row["title"] or "").replace("\ufeff", "").strip().lower(),
                    (t_row["artist"] or "").replace("\ufeff", "").strip().lower(),
                )
                if path_key in existing_paths or sig_key in existing_sigs:
                    continue
                existing_paths.add(path_key)
                existing_sigs.add(sig_key)
                unique_new_tids.append(tid)

            if not unique_new_tids:
                raise ValueError("Song already exists in playlist.")

            # Find current max position
            row = conn.execute(
                "SELECT COALESCE(MAX(position), 0) as max_pos FROM playlist_tracks WHERE playlist_id = ?",
                (playlist_id,),
            ).fetchone()
            start_pos = row["max_pos"] if row else 0

            inserts = [
                (playlist_id, tid, start_pos + idx + 1, now)
                for idx, tid in enumerate(unique_new_tids)
            ]
            conn.executemany(
                "INSERT INTO playlist_tracks (playlist_id, track_id, position, added_at) VALUES (?, ?, ?, ?)",
                inserts,
            )
            conn.execute("UPDATE playlists SET updated_at = ? WHERE id = ?", (now, playlist_id))
            return len(inserts)

    def remove_playlist_entry(self, playlist_id: int, entry_id: int) -> bool:
        """Removes a single entry by entry_id and recompacts positions."""
        now = time.time()
        with self._get_connection() as conn:
            res = conn.execute(
                "DELETE FROM playlist_tracks WHERE playlist_id = ? AND id = ?",
                (playlist_id, entry_id),
            )
            if res.rowcount > 0:
                self._recompact_playlist_positions(conn, playlist_id)
                conn.execute("UPDATE playlists SET updated_at = ? WHERE id = ?", (now, playlist_id))
                return True
            return False

    def reorder_playlist_tracks(self, playlist_id: int, entry_ids_ordered: List[int]) -> bool:
        """Updates positions to match the given ordered list of entry IDs."""
        now = time.time()
        with self._get_connection() as conn:
            for new_pos, eid in enumerate(entry_ids_ordered, start=1):
                conn.execute(
                    "UPDATE playlist_tracks SET position = ? WHERE id = ? AND playlist_id = ?",
                    (new_pos, eid, playlist_id),
                )
            conn.execute("UPDATE playlists SET updated_at = ? WHERE id = ?", (now, playlist_id))
            return True

    def clear_playlist_tracks(self, playlist_id: int) -> None:
        """Clears all tracks from a playlist."""
        now = time.time()
        with self._get_connection() as conn:
            conn.execute("DELETE FROM playlist_tracks WHERE playlist_id = ?", (playlist_id,))
            conn.execute("UPDATE playlists SET updated_at = ? WHERE id = ?", (now, playlist_id))

    def _recompact_playlist_positions(self, conn: sqlite3.Connection, playlist_id: int) -> None:
        """Internal helper to ensure positions are contiguous integers starting from 1."""
        cursor = conn.execute(
            "SELECT id FROM playlist_tracks WHERE playlist_id = ? ORDER BY position ASC, id ASC",
            (playlist_id,),
        )
        for idx, row in enumerate(cursor.fetchall(), start=1):
            conn.execute("UPDATE playlist_tracks SET position = ? WHERE id = ?", (idx, row["id"]))

    def _row_to_track(self, row: sqlite3.Row) -> TrackRecord:
        """Converts an SQLite row to a TrackRecord object."""
        return TrackRecord(
            id=row["id"],
            canonical_path=row["canonical_path"],
            folder_path=row["folder_path"],
            filename=row["filename"],
            file_size=row["file_size"],
            mtime=row["mtime"],
            title=row["title"],
            artist=row["artist"],
            album=row["album"],
            genre=row["genre"],
            duration=row["duration"] if row["duration"] is not None else 0.0,
            play_count=row["play_count"],
            last_played_at=row["last_played_at"],
            skip_count=row["skip_count"],
            is_available=bool(row["is_available"]),
            rating=int(row["rating"]) if "rating" in row.keys() and row["rating"] is not None else 0,
        )

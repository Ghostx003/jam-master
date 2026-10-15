"""Intelligent, preference-aware, anti-repeat music shuffling engine.
Purely statistical, variety-maximizing, zero-rating shuffle algorithm.
"""

from __future__ import annotations

import math
from pathlib import Path
import random
from collections import deque
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from backend.config import DEFAULT_SHUFFLE_CONFIG
from backend.database import Database, TrackRecord


class EmptyPoolError(Exception):
    """Raised when the active track pool has zero eligible tracks."""
    pass


@dataclass
class PlaybackState:
    """Represents the current engine playback status."""
    current_track: Optional[TrackRecord]
    mode: str  # e.g. "Normal Shuffle", "Playlist: Mix", "Repeat (2 left)"
    repeats_remaining: int
    pool_size: int
    deck_remaining: int
    recent_history_size: int
    context_name: str = "Library"
    shuffle_whole_deck: bool = False
    active_playlist_id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_track": self.current_track.to_dict() if self.current_track else None,
            "mode": self.mode,
            "repeats_remaining": self.repeats_remaining,
            "pool_size": self.pool_size,
            "deck_remaining": self.deck_remaining,
            "recent_history_size": self.recent_history_size,
            "context_name": self.context_name,
            "shuffle_whole_deck": self.shuffle_whole_deck,
            "active_playlist_id": self.active_playlist_id,
        }


class ShuffleEngine:
    """High-performance, anti-repeat hybrid shuffle engine."""

    def __init__(
        self,
        db: Database,
        config: Optional[Dict] = None,
        rng: Optional[random.Random] = None,
    ) -> None:
        self.db = db
        self.config = dict(DEFAULT_SHUFFLE_CONFIG)
        if config:
            self.config.update(config)

        self.rng = rng or random.Random()

        # Active pool and mode
        self._all_tracks: Dict[int, TrackRecord] = {}
        self._selected_folder_paths: List[str] = []
        self._active_playlist_id: Optional[int] = None
        self._context_name: str = "Library"

        # Current playback tracking
        self._current_track: Optional[TrackRecord] = None
        self._priority_queue: deque[TrackRecord] = deque()
        self._repeats_remaining: int = 0

        # Back stack for "Previous Song"
        self._playback_history_stack: deque[TrackRecord] = deque(maxlen=100)

        # Shuffled deck and bounded recent history
        self._deck: deque[TrackRecord] = deque()
        self._recent_history_ids: deque[int] = deque()
        self._recent_skips: Dict[int, int] = {}  # track_id -> decay counter
        self._total_session_plays: int = 0
        self.shuffle_whole_deck: bool = False
        self._current_track_start_time: float = 0.0

    # -------------------------------------------------------------------------
    # Pool Setup: Folders, Playlists, or Full Library
    # -------------------------------------------------------------------------

    def set_folder_pool(self, folder_paths: Sequence[str]) -> int:
        """Sets the active folder pool and rebuilds the deck.
        
        Returns the number of eligible tracks in the pool.
        """
        seen = set()
        deduped = []
        for fp in folder_paths:
            if fp not in seen:
                seen.add(fp)
                deduped.append(fp)

        self._selected_folder_paths = deduped
        self._active_playlist_id = None
        self._context_name = f"Folders ({len(deduped)})" if len(deduped) > 1 else (Path(deduped[0]).name if deduped else "Folders")

        self._refresh_tracks_from_db()
        self._rebuild_deck(force=True)
        return len(self.eligible_tracks)

    def add_folder_to_pool(self, folder_path: str) -> int:
        """Adds another folder to the active pool without discarding existing selections."""
        if folder_path not in self._selected_folder_paths:
            self._selected_folder_paths.append(folder_path)
            self._active_playlist_id = None
            self._context_name = f"Folders ({len(self._selected_folder_paths)})"
            self._refresh_tracks_from_db()
            self._augment_deck_with_new_pool()
        return len(self.eligible_tracks)

    def set_playlist_pool(self, playlist_id: int) -> int:
        """Loads a user-curated playlist as the active music pool."""
        playlist = self.db.get_playlist(playlist_id)
        if not playlist:
            raise ValueError(f"Playlist with id {playlist_id} not found.")

        entries = self.db.get_playlist_entries(playlist_id)
        tracks_dict: Dict[int, TrackRecord] = {}
        for e in entries:
            if e.track and e.track.is_available:
                tracks_dict[e.track.id] = e.track

        self._active_playlist_id = playlist_id
        self._selected_folder_paths = []
        self._context_name = f"Playlist: {playlist.name}"
        self._all_tracks = tracks_dict

        self._rebuild_deck(force=True)
        return len(self.eligible_tracks)

    def set_full_library_pool(self) -> int:
        """Sets all available library tracks as the active pool."""
        self._selected_folder_paths = []
        self._active_playlist_id = None
        self._context_name = "Full Library"

        tracks = self.db.get_all_tracks(only_available=True)
        self._all_tracks = {t.id: t for t in tracks}

        self._rebuild_deck(force=True)
        return len(self.eligible_tracks)

    @property
    def selected_folder_paths(self) -> List[str]:
        return list(self._selected_folder_paths)

    @property
    def eligible_tracks(self) -> List[TrackRecord]:
        """Returns currently available tracks in active pool."""
        return [t for t in self._all_tracks.values() if t.is_available]

    def _refresh_tracks_from_db(self) -> None:
        """Reloads tracks from database for active folder selection."""
        if not self._selected_folder_paths:
            tracks = self.db.get_all_tracks(only_available=True)
            self._all_tracks = {t.id: t for t in tracks}
            return

        tracks = self.db.get_tracks_in_folders(self._selected_folder_paths, only_available=True)
        seen_paths: Set[str] = set()
        deduped: Dict[int, TrackRecord] = {}
        for t in tracks:
            if t.canonical_path not in seen_paths:
                seen_paths.add(t.canonical_path)
                deduped[t.id] = t

        self._all_tracks = deduped

    # -------------------------------------------------------------------------
    # Mathematical Weighting Function (ZERO RATINGS)
    # -------------------------------------------------------------------------

    def calculate_track_weight(self, track: TrackRecord) -> float:
        """Computes multi-factor variety weight for a track.
        
        W = DiscoveryBonus * FrequencyDampening * RecencyComeback * SkipPenalty
        Always strictly > 0.
        """
        weight = 1.0

        # 1. Discovery boost for tracks never played
        if track.play_count == 0:
            weight *= self.config.get("discovery_boost", 1.40)

        # 2. Logarithmic frequency dampening for heavily played tracks
        freq_rate = self.config.get("frequency_dampening", 0.15)
        freq_factor = 1.0 / (1.0 + freq_rate * math.log(1.0 + max(0, track.play_count)))
        weight *= freq_factor

        # 3. Recency comeback bonus for tracks that haven't been heard in a while
        if track.last_played_at is not None:
            plays_since = max(1, self._total_session_plays - getattr(track, "_last_session_play_idx", 0))
            half_life = self.config.get("recency_half_life", 40)
            max_boost = self.config.get("max_recency_boost", 1.50)
            recency_bonus = 1.0 + (max_boost - 1.0) * (1.0 - math.exp(-plays_since / half_life))
            weight *= recency_bonus

        # 4. Decaying skip penalty for recently skipped tracks
        recent_skip_val = self._recent_skips.get(track.id, 0)
        if recent_skip_val > 0:
            penalty = max(
                self.config.get("min_skip_factor", 0.20),
                math.pow(self.config.get("skip_penalty", 0.50), min(3, recent_skip_val)),
            )
            weight *= penalty

        # 5. Algorithm randomness factor: 0.0 = smart weighted, 1.0 = pure uniform random
        randomness = float(self.config.get("randomness_factor", 0.0))
        if randomness > 0.0:
            weight = math.pow(weight, max(0.0, 1.0 - min(1.0, randomness)))

        return max(0.001, min(100.0, weight))

    # -------------------------------------------------------------------------
    # Shuffled Deck Generation & Boundary Stitching
    # -------------------------------------------------------------------------

    def _generate_weighted_deck(
        self,
        tracks: List[TrackRecord],
        target_size: Optional[int] = None,
    ) -> List[TrackRecord]:
        """Generates a randomized permutation using Efraimidis-Spirakis weighted reservoir keys.
        
        For each item with weight w > 0, key = u^(1/w) where u ~ Uniform(0, 1).
        Sorting descending by key produces an exact weighted permutation without replacement.
        Every track in the returned deck cycle is unique.
        """
        if not tracks:
            return []

        weighted_items: List[Tuple[float, TrackRecord]] = []
        for t in tracks:
            w = self.calculate_track_weight(t)
            u = max(1e-9, self.rng.random())
            key = math.pow(u, 1.0 / w)
            weighted_items.append((key, t))

        # Sort descending by key
        weighted_items.sort(key=lambda item: item[0], reverse=True)
        if target_size is not None and target_size < len(weighted_items):
            return [item[1] for item in weighted_items[:target_size]]
        return [item[1] for item in weighted_items]

    def _stitch_deck_boundary(
        self,
        new_deck: List[TrackRecord],
        last_played_id: Optional[int],
    ) -> List[TrackRecord]:
        """Ensures the head of a newly generated deck does not immediately repeat the last played track."""
        n = len(new_deck)
        if n <= 1 or last_played_id is None:
            return new_deck

        if new_deck[0].id == last_played_id:
            swap_idx = min(3, n - 1)
            new_deck[0], new_deck[swap_idx] = new_deck[swap_idx], new_deck[0]

        if n >= 4 and len(self._recent_history_ids) >= 2:
            second_last_id = self._recent_history_ids[-2] if len(self._recent_history_ids) >= 2 else None
            if second_last_id and new_deck[0].id == second_last_id:
                swap_idx = min(4, n - 1)
                new_deck[0], new_deck[swap_idx] = new_deck[swap_idx], new_deck[0]

        return new_deck

    def _rebuild_deck(self, force: bool = False) -> None:
        """Rebuilds the shuffled deck from currently eligible tracks with anti-repeat protection."""
        eligible = self.eligible_tracks
        if not eligible:
            self._deck.clear()
            return

        pool_size = len(eligible)
        window_size = self._get_active_history_window_size(pool_size)
        recent_blocked = set(list(self._recent_history_ids)[-window_size:]) if window_size > 0 else set()

        if self._current_track:
            recent_blocked.add(self._current_track.id)

        # Candidates not in recent blocked window
        candidates = [t for t in eligible if t.id not in recent_blocked]
        if not candidates:
            # Fallback relaxation tier 1: block only current track
            candidates = [t for t in eligible if not self._current_track or t.id != self._current_track.id]
        if not candidates:
            # Fallback relaxation tier 2: allow all eligible
            candidates = list(eligible)

        new_deck = self._generate_weighted_deck(candidates)
        last_played_id = self._current_track.id if self._current_track else None
        new_deck = self._stitch_deck_boundary(new_deck, last_played_id)

        self._deck = deque(new_deck)

    def _augment_deck_with_new_pool(self) -> None:
        """Integrates newly added tracks into the remaining deck without duplicates."""
        eligible = self.eligible_tracks
        current_deck_ids = {t.id for t in self._deck}
        new_tracks = [t for t in eligible if t.id not in current_deck_ids]

        if not new_tracks:
            return

        weighted_new = self._generate_weighted_deck(new_tracks)
        merged = list(self._deck) + weighted_new
        self._deck = deque(merged)

    # -------------------------------------------------------------------------
    # Recent-History Exclusion & Fallback Hierarchy
    # -------------------------------------------------------------------------

    def _get_active_history_window_size(self, pool_size: int) -> int:
        """Calculates adaptive recent-history exclusion window based on pool size."""
        if pool_size <= 1:
            return 0
        if pool_size == 2:
            return 1

        ratio = self.config.get("history_ratio", 0.25)
        calculated = int(math.floor(pool_size * ratio))
        max_bound = self.config.get("max_history_window", 50)
        min_bound = self.config.get("min_history_window", 1)

        upper_limit = pool_size - 1
        return max(min_bound, min(calculated, max_bound, upper_limit))

    def _select_next_from_deck(self, avoid_current: bool = True) -> TrackRecord:
        """Pulls the next track directly from the head of the deck (matching Up Next bar exactly)."""
        eligible = self.eligible_tracks
        pool_size = len(eligible)
        if pool_size == 0:
            raise EmptyPoolError("No eligible tracks available to shuffle.")

        if pool_size == 1:
            self._deck = deque(eligible)
            return eligible[0]

        if not self._deck:
            self._rebuild_deck(force=True)

        if not self._deck:
            return eligible[0]

        # The head of the deck is the exact track visible as #1 in the Up Next queue
        track = self._deck.popleft()

        # If avoid_current is True and popped track happens to be current track, swap with next
        if avoid_current and self._current_track and track.id == self._current_track.id and self._deck:
            next_t = self._deck.popleft()
            self._deck.append(track)
            track = next_t

        return track

    # -------------------------------------------------------------------------
    # Core Public Playback Actions
    # -------------------------------------------------------------------------

    def next_track(self, was_skipped: bool = False) -> TrackRecord:
        """Selects and transitions to the next track."""
        import time
        if self._current_track and was_skipped:
            # If user listened for at least 30 seconds before skipping, do not treat as skipped
            if self._current_track_start_time > 0 and (time.time() - self._current_track_start_time >= 30.0):
                was_skipped = False

        if self._current_track and was_skipped:
            self.db.record_skip(self._current_track.id)
            self._recent_skips[self._current_track.id] = self.config.get("skip_decay_plays", 8)

        if self._recent_skips:
            for tid in list(self._recent_skips.keys()):
                if not (self._current_track and tid == self._current_track.id and was_skipped):
                    self._recent_skips[tid] -= 1
                    if self._recent_skips[tid] <= 0:
                        del self._recent_skips[tid]

        # Check priority queue (repeat mode)
        if self._priority_queue:
            track = self._priority_queue.popleft()
            self._repeats_remaining = len(self._priority_queue)
            self._finalize_track_transition(track, was_repeat=True)
            return track

        self._repeats_remaining = 0
        track = self._select_next_from_deck(avoid_current=True)
        self._finalize_track_transition(track, was_repeat=False)
        return track

    def previous_track(self) -> Optional[TrackRecord]:
        """Returns the previous track from history stack."""
        if len(self._playback_history_stack) < 2:
            return None

        # Pop current track from stack
        self._playback_history_stack.pop()
        # Peek / pop previous track
        prev_track = self._playback_history_stack.pop()
        self._finalize_track_transition(prev_track, was_repeat=False, is_backtrack=True)
        return prev_track

    def play_specific_track(self, track_id: int) -> TrackRecord:
        """Plays a specific track directly (e.g. from library or history)."""
        track = self.db.get_track_by_id(track_id)
        if not track or not track.is_available:
            raise ValueError(f"Track with id {track_id} not found or unavailable.")

        self._priority_queue.clear()
        self._repeats_remaining = 0
        self._finalize_track_transition(track, was_repeat=False)
        return track

    def set_repeat(self, additional_repeats: int) -> int:
        """Sets the current track to repeat N additional times."""
        if not self._current_track:
            raise ValueError("Cannot repeat: no track is currently playing.")

        if additional_repeats < 0:
            raise ValueError("Repeat count cannot be negative.")

        self._priority_queue.clear()
        for _ in range(additional_repeats):
            self._priority_queue.append(self._current_track)

        self._repeats_remaining = additional_repeats
        return self._repeats_remaining

    def fresh_shuffle(self) -> TrackRecord:
        """Executes 'Shuffle more': builds a fresh randomized selection."""
        self._priority_queue.clear()
        self._repeats_remaining = 0
        self._rebuild_deck(force=True)

        track = self._select_next_from_deck(avoid_current=True)
        self._finalize_track_transition(track, was_repeat=False)
        return track

    def _finalize_track_transition(
        self,
        track: TrackRecord,
        was_repeat: bool,
        is_backtrack: bool = False,
    ) -> None:
        """Updates internal state and database records for a chosen track."""
        self._current_track = track
        self._total_session_plays += 1

        if not is_backtrack:
            self._playback_history_stack.append(track)

        setattr(track, "_last_session_play_idx", self._total_session_plays)

        self._recent_history_ids.append(track.id)
        max_hist = self.config.get("max_history_window", 50)
        if len(self._recent_history_ids) > max_hist:
            self._recent_history_ids.popleft()

        import time
        self._current_track_start_time = time.time()
        self.db.record_play(track.id, was_skipped=False)
        track.play_count += 1
        track.last_played_at = float(self._total_session_plays)

        # If deck is now depleted, rebuild upcoming deck so Up Next bar remains full
        if not self._deck and self.eligible_tracks:
            self._rebuild_deck(force=True)

    def toggle_shuffle_whole_deck(self, enable: Optional[bool] = None) -> bool:
        """Toggles or sets whole deck shuffling (including already played songs)."""
        if enable is None:
            self.shuffle_whole_deck = not self.shuffle_whole_deck
        else:
            self.shuffle_whole_deck = bool(enable)
        if self.shuffle_whole_deck:
            self._rebuild_deck(force=True)
        return self.shuffle_whole_deck

    def update_track_rating(self, track_id: int, rating: int) -> None:
        """Updates in-memory track rating across active state, deck, and history."""
        if self._current_track and self._current_track.id == track_id:
            self._current_track.rating = rating
        if track_id in self._all_tracks:
            self._all_tracks[track_id].rating = rating
        for t in self._deck:
            if t.id == track_id:
                t.rating = rating
        for t in self._priority_queue:
            if t.id == track_id:
                t.rating = rating
        for t in self._playback_history_stack:
            if t.id == track_id:
                t.rating = rating

    # -------------------------------------------------------------------------
    # State Inspection
    # -------------------------------------------------------------------------

    def get_playback_state(self) -> PlaybackState:
        """Returns snapshot of current playback status."""
        if self._repeats_remaining > 0:
            mode = f"Repeat ({self._repeats_remaining} left)"
        elif self.shuffle_whole_deck:
            mode = "Shuffle (Whole Deck)"
        else:
            mode = "Shuffle"

        return PlaybackState(
            current_track=self._current_track,
            mode=mode,
            repeats_remaining=self._repeats_remaining,
            pool_size=len(self.eligible_tracks),
            deck_remaining=len(self._deck),
            recent_history_size=len(self._recent_history_ids),
            context_name=self._context_name,
            shuffle_whole_deck=self.shuffle_whole_deck,
            active_playlist_id=self._active_playlist_id,
        )

    def get_up_next(self, limit: Optional[int] = None) -> List[TrackRecord]:
        """Returns the upcoming tracks in the current shuffle deck.
        When playing from a playlist pool, returns all tracks in the playlist (up to 1,000).
        For the default music library pool, returns 50 tracks unless explicitly specified.
        """
        if not self._deck and self.eligible_tracks:
            self._rebuild_deck(force=True)
        eff_limit = (1000 if self._active_playlist_id is not None else 50) if limit is None else limit
        return list(self._deck)[:eff_limit]

    def reshuffle_up_next(self, limit: Optional[int] = None) -> List[TrackRecord]:
        """Reshuffles the remaining upcoming deck and returns the new queue."""
        self._rebuild_deck(force=True)
        eff_limit = (1000 if self._active_playlist_id is not None else 50) if limit is None else limit
        return list(self._deck)[:eff_limit]

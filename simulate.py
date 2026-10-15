"""Standalone simulation and visualization script for Shuffle Master's anti-repeat engine.
Zero ratings or likes. Verifies statistical coverage and spacing.
"""

from __future__ import annotations

import random
import sys
import tempfile
from collections import Counter
from pathlib import Path

from rich.box import ROUNDED, SIMPLE_HEAVY
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from backend.database import Database
from backend.shuffle_engine import ShuffleEngine

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

console = Console()


def run_simulation(num_tracks: int = 100, num_plays: int = 2500) -> None:
    """Simulates a large listening session and prints statistical distributions."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        temp_db_path = Path(tmp_dir) / "sim.db"
        db = Database(temp_db_path)

        folder = "D:/SimMusic/Library"
        for i in range(1, num_tracks + 1):
            db.upsert_scanned_track(
                canonical_path=f"{folder}/track_{i:04d}.mp3",
                folder_path=folder,
                filename=f"track_{i:04d}.mp3",
                file_size=4000,
                mtime=1.0,
                title=f"Synthetic Track {i}",
                artist=f"Artist {i % 10}",
                album="Sim Album",
                genre="Simulation",
                duration=180.0,
            )

        engine = ShuffleEngine(db, rng=random.Random(42))
        engine.set_folder_pool([folder])

        console.print(Panel(
            f"[bold cyan]Simulating {num_plays} plays across {num_tracks} tracks (No Ratings)...[/bold cyan]",
            box=ROUNDED,
        ))

        # Run simulation
        play_seq = []
        play_counts = Counter()

        for _ in range(num_plays):
            t = engine.next_track()
            play_seq.append(t.id)
            play_counts[t.id] += 1

        # Analyze anti-repeat spacing
        last_seen = {}
        min_spacing = 999999
        consecutive_repeats = 0
        window_size = int(num_tracks * 0.25)
        violations_of_window = 0

        for idx, tid in enumerate(play_seq):
            if tid in last_seen:
                spacing = idx - last_seen[tid]
                if spacing == 1:
                    consecutive_repeats += 1
                if spacing <= window_size:
                    violations_of_window += 1
                min_spacing = min(min_spacing, spacing)
            last_seen[tid] = idx

        # Print summary
        summary_table = Table(box=SIMPLE_HEAVY, header_style="bold cyan", title="Simulation Summary")
        summary_table.add_column("Metric", style="white")
        summary_table.add_column("Value", justify="right", style="green")

        unique_tracks_played = len(play_counts)
        coverage_pct = (unique_tracks_played / num_tracks) * 100.0
        avg_plays = num_plays / num_tracks

        summary_table.add_row("Total Session Plays", str(num_plays))
        summary_table.add_row("Total Unique Tracks in Pool", str(num_tracks))
        summary_table.add_row("Unique Tracks Played (Coverage)", f"{unique_tracks_played} ({coverage_pct:.1f}%)")
        summary_table.add_row("Consecutive Immediate Repeats", str(consecutive_repeats))
        summary_table.add_row("Minimum Observed Spacing", str(min_spacing))
        summary_table.add_row(f"History Window Violations (<= {window_size} tracks)", str(violations_of_window))
        summary_table.add_row("Expected Plays per Track", f"{avg_plays:.1f}")
        summary_table.add_row("Min Plays Observed for Any Track", str(min(play_counts.values())))
        summary_table.add_row("Max Plays Observed for Any Track", str(max(play_counts.values())))

        console.print()
        console.print(summary_table)
        console.print()


if __name__ == "__main__":
    run_simulation()

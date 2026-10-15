"""Large-scale Monte Carlo statistical simulations and performance benchmarks.
Zero ratings or likes. Verifies coverage, anti-repeat spacing, and performance with large libraries.
"""

import random
import time
from collections import Counter
from pathlib import Path
import pytest
from backend.database import Database
from backend.shuffle_engine import ShuffleEngine


def test_monte_carlo_distribution_and_coverage(tmp_path):
    """Simulates 2,000 plays across a 100-track library.
    
    Verifies:
    1. 100% library coverage (no starvation).
    2. Zero consecutive identical plays.
    3. Strict anti-repeat minimum spacing respecting the recent-history window.
    """
    db = Database(tmp_path / "sim.db")

    for i in range(1, 101):
        db.upsert_scanned_track(
            canonical_path=f"D:/Sim/track_{i:03d}.mp3",
            folder_path="D:/Sim",
            filename=f"track_{i:03d}.mp3",
            file_size=5000,
            mtime=1.0,
            title=f"Simulation Track {i}",
            artist=f"Artist {i % 10}",
            album="Sim Album",
            genre="Electronic",
            duration=180.0,
        )

    engine = ShuffleEngine(db, rng=random.Random(42))
    engine.set_folder_pool(["D:/Sim"])

    num_simulated_plays = 2000
    play_sequence = []
    play_counts = Counter()

    for _ in range(num_simulated_plays):
        track = engine.next_track()
        play_sequence.append(track.id)
        play_counts[track.id] += 1

    # 1. 100% Coverage Verification
    unique_played = set(play_sequence)
    assert len(unique_played) == 100, f"Expected all 100 tracks to be played, but only {len(unique_played)} were!"

    # 2. Anti-Repeat Window Verification
    # Pool size = 100 -> window size = min(50, 100 * 0.25) = 25
    window_size = 25
    last_seen_index = {}
    for idx, tid in enumerate(play_sequence):
        if tid in last_seen_index:
            spacing = idx - last_seen_index[tid]
            assert spacing > window_size, (
                f"Track {tid} repeated too soon! Spacing={spacing}, minimum allowed window={window_size + 1}"
            )
        last_seen_index[tid] = idx

    # 3. Frequency balance
    for tid, count in play_counts.items():
        assert count >= 10, f"Track {tid} was starved with only {count} plays in 2000 plays!"


def test_large_library_performance(tmp_path):
    """Benchmarks shuffle performance with 10,000 tracks."""
    db = Database(tmp_path / "large_lib.db")

    with db._get_connection() as conn:
        inserts = [
            (
                f"D:/LargeMusic/track_{i:05d}.mp3",
                "D:/LargeMusic",
                f"track_{i:05d}.mp3",
                5000,
                1.0,
                f"Big Track {i}",
                f"Artist {i % 50}",
                "Big Album",
                "Various",
                200.0,
                1,
                time.time(),
                time.time(),
            )
            for i in range(1, 10001)
        ]
        conn.executemany(
            """
            INSERT INTO tracks (
                canonical_path, folder_path, filename, file_size, mtime,
                title, artist, album, genre, duration, is_available,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            inserts,
        )

    engine = ShuffleEngine(db, rng=random.Random(42))

    start_pool = time.perf_counter()
    pool_size = engine.set_folder_pool(["D:/LargeMusic"])
    pool_time = time.perf_counter() - start_pool

    assert pool_size == 10000
    assert pool_time < 2.0, f"Setting 10k pool should be fast, took {pool_time:.2f}s"

    # Play 50 tracks and measure selection latency
    latencies = []
    for _ in range(50):
        t0 = time.perf_counter()
        track = engine.next_track()
        latencies.append(time.perf_counter() - t0)

    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)

    assert avg_latency < 0.05, f"Average selection latency in 10k tracks should be < 50ms, got {avg_latency*1000:.2f}ms"
    assert max_latency < 0.20, f"Max selection latency in 10k tracks should be < 200ms, got {max_latency*1000:.2f}ms"

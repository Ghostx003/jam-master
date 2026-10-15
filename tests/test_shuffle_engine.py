"""Comprehensive tests for Shuffle Master's anti-repeat shuffle engine.
Zero ratings or likes. Strict verification of statistical fairness and anti-repeat.
"""

import random
import pytest
from pathlib import Path
from backend.database import Database
from backend.shuffle_engine import EmptyPoolError, ShuffleEngine


@pytest.fixture
def test_db(tmp_path):
    db = Database(tmp_path / "shuffle_test.db")
    # Insert 20 sample tracks across 2 folders
    for i in range(1, 21):
        folder = "D:/Music/Rock" if i <= 10 else "D:/Music/Electronic"
        db.upsert_scanned_track(
            canonical_path=f"{folder}/track_{i:02d}.mp3",
            folder_path=folder,
            filename=f"track_{i:02d}.mp3",
            file_size=5000,
            mtime=1.0,
            title=f"Track {i}",
            artist="Artist X" if i % 2 == 0 else "Artist Y",
            album="Album Z",
            genre="Rock" if i <= 10 else "Electronic",
            duration=200.0,
        )
    return db


def test_empty_pool_raises():
    db = Database(":memory:")
    engine = ShuffleEngine(db)
    with pytest.raises(EmptyPoolError):
        engine.next_track()


def test_single_track_pool(tmp_path):
    db = Database(tmp_path / "single.db")
    db.upsert_scanned_track(
        canonical_path="D:/Solo/only_song.mp3",
        folder_path="D:/Solo",
        filename="only_song.mp3",
        file_size=1000,
        mtime=1.0,
        title="Solo",
        artist="Solo Artist",
        album="Solo",
        genre="Acoustic",
        duration=150.0,
    )
    engine = ShuffleEngine(db)
    engine.set_folder_pool(["D:/Solo"])

    # Multiple plays of single track should succeed without hanging
    for _ in range(5):
        t = engine.next_track()
        assert t.title == "Solo"


def test_two_track_pool_alternates(tmp_path):
    db = Database(tmp_path / "duo.db")
    for i in (1, 2):
        db.upsert_scanned_track(
            canonical_path=f"D:/Duo/song_{i}.mp3",
            folder_path="D:/Duo",
            filename=f"song_{i}.mp3",
            file_size=1000,
            mtime=1.0,
            title=f"Song {i}",
            artist="Duo",
            album="Duo",
            genre="Pop",
            duration=120.0,
        )
    engine = ShuffleEngine(db)
    engine.set_folder_pool(["D:/Duo"])

    t1 = engine.next_track()
    t2 = engine.next_track()
    t3 = engine.next_track()
    t4 = engine.next_track()

    # In a 2-track pool, it must alternate between song 1 and song 2
    assert t1.id != t2.id
    assert t2.id != t3.id
    assert t3.id != t4.id


def test_shuffled_deck_coverage_and_uniqueness(test_db):
    engine = ShuffleEngine(test_db, rng=random.Random(12345))
    engine.set_folder_pool(["D:/Music/Rock"])  # 10 tracks

    # Consume exactly one full deck of 10 tracks
    deck_tracks = [engine.next_track() for _ in range(10)]
    ids = [t.id for t in deck_tracks]

    # Verify zero duplicates within the deck
    assert len(ids) == len(set(ids)), "Every track in a deck must be unique!"
    assert len(ids) == 10, "Deck must cover 100% of eligible tracks before depleting!"


def test_boundary_stitcher_prevents_deck_boundary_collision(test_db):
    # Over 5 deck cycles (50 plays on 10 tracks), no two consecutive plays should be identical
    engine = ShuffleEngine(test_db, rng=random.Random(999))
    engine.set_folder_pool(["D:/Music/Rock"])

    last_track_id = None
    for play_idx in range(50):
        t = engine.next_track()
        if last_track_id is not None:
            assert t.id != last_track_id, f"Consecutive repeat detected at play {play_idx}!"
        last_track_id = t.id


def test_recent_history_exclusion_window(test_db):
    engine = ShuffleEngine(test_db, rng=random.Random(42))
    engine.set_folder_pool(["D:/Music/Rock", "D:/Music/Electronic"])  # 20 tracks

    # Pool size = 20. history_ratio = 0.25 -> window size = 5 tracks.
    played = []
    for _ in range(40):
        t = engine.next_track()
        played.append(t.id)
        if len(played) > 6:
            recent_5 = played[-6:-1]
            assert t.id not in recent_5, f"Track {t.id} repeated within exclusion window: {recent_5}"


def test_discovery_and_frequency_weighting(test_db):
    engine = ShuffleEngine(test_db)
    engine.set_folder_pool(["D:/Music/Rock"])

    t1 = test_db.get_track_by_path("D:/Music/Rock/track_01.mp3")
    t2 = test_db.get_track_by_path("D:/Music/Rock/track_02.mp3")

    # t1 is unplayed (play_count = 0)
    t1.play_count = 0
    # t2 has been played 15 times
    t2.play_count = 15

    w1 = engine.calculate_track_weight(t1)
    w2 = engine.calculate_track_weight(t2)

    # Unplayed track with discovery boost must have higher weight than heavily played track
    assert w1 > w2


def test_skip_penalty(test_db):
    engine = ShuffleEngine(test_db)
    engine.set_folder_pool(["D:/Music/Rock"])

    t = engine.next_track()
    # Normal weight
    normal_weight = engine.calculate_track_weight(t)

    # Mark as skipped
    engine.next_track(was_skipped=True)
    penalized_weight = engine.calculate_track_weight(t)

    # Weight after skip should be lower
    assert penalized_weight < normal_weight


def test_repeat_mode(test_db):
    engine = ShuffleEngine(test_db)
    engine.set_folder_pool(["D:/Music/Rock"])

    initial = engine.next_track()
    # Queue 3 additional repeats
    engine.set_repeat(3)

    r1 = engine.next_track()
    r2 = engine.next_track()
    r3 = engine.next_track()

    assert r1.id == initial.id
    assert r2.id == initial.id
    assert r3.id == initial.id

    # 4th next_track should return to normal shuffle and pick another track
    after_repeat = engine.next_track()
    assert after_repeat.id != initial.id


def test_previous_track_from_history(test_db):
    engine = ShuffleEngine(test_db)
    engine.set_folder_pool(["D:/Music/Rock"])

    t1 = engine.next_track()
    t2 = engine.next_track()
    t3 = engine.next_track()

    # Previous track should return t2
    prev = engine.previous_track()
    assert prev is not None
    assert prev.id == t2.id


def test_playlist_shuffle(test_db):
    pl = test_db.create_playlist("Chill Mix")
    t1 = test_db.get_track_by_path("D:/Music/Rock/track_01.mp3")
    t2 = test_db.get_track_by_path("D:/Music/Rock/track_02.mp3")
    t3 = test_db.get_track_by_path("D:/Music/Rock/track_03.mp3")
    test_db.add_tracks_to_playlist(pl.id, [t1.id, t2.id, t3.id])

    engine = ShuffleEngine(test_db)
    pool_sz = engine.set_playlist_pool(pl.id)
    assert pool_sz == 3

    # All tracks returned should be from the playlist
    played_ids = set()
    for _ in range(6):
        t = engine.next_track()
        assert t.id in (t1.id, t2.id, t3.id)
        played_ids.add(t.id)

    assert played_ids == {t1.id, t2.id, t3.id}


def test_add_folder_to_pool(test_db):
    engine = ShuffleEngine(test_db)
    pool1 = engine.set_folder_pool(["D:/Music/Rock"])
    assert pool1 == 10

    pool2 = engine.add_folder_to_pool("D:/Music/Electronic")
    assert pool2 == 20
    assert len(engine.selected_folder_paths) == 2


def test_fresh_shuffle_avoids_current(test_db):
    engine = ShuffleEngine(test_db, rng=random.Random(123))
    engine.set_folder_pool(["D:/Music/Rock"])

    cur = engine.next_track()
    fresh = engine.fresh_shuffle()
    assert fresh.id != cur.id


def test_seed_reproducibility(tmp_path):
    def build_test_db(name):
        d = Database(tmp_path / name)
        for i in range(1, 11):
            d.upsert_scanned_track(
                canonical_path=f"D:/Music/Rock/track_{i:02d}.mp3",
                folder_path="D:/Music/Rock",
                filename=f"track_{i:02d}.mp3",
                file_size=5000,
                mtime=1.0,
                title=f"Track {i}",
                artist="Artist X",
                album="Album Z",
                genre="Rock",
                duration=200.0,
            )
        return d

    db1 = build_test_db("seed1.db")
    db2 = build_test_db("seed2.db")

    engine1 = ShuffleEngine(db1, rng=random.Random(42))
    engine1.set_folder_pool(["D:/Music/Rock"])
    seq1 = [engine1.next_track().id for _ in range(25)]

    engine2 = ShuffleEngine(db2, rng=random.Random(42))
    engine2.set_folder_pool(["D:/Music/Rock"])
    seq2 = [engine2.next_track().id for _ in range(25)]

    assert seq1 == seq2, "Deterministic seed with identical initial DB must produce identical track sequence!"

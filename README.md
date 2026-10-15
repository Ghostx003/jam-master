# 🎵 Jam Master (v1.0)

> **High-Fidelity Local Music Shuffler & AIMP Remote Audio Engine**  
> *A local-first music management system with genuine Win32 AIMP DSP preservation, an intelligent anti-repeat shuffle engine, online lyrics with Indic romanization, and dual web & terminal interfaces.*

---

## 🌟 Key Features

### 🎧 1. Native AIMP Playback & DSP Preservation
* **Direct Win32 IPC Messaging**: Dispatches tracks directly into AIMP via memory-level Windows messages (`WM_COPYDATA` / `IPC_PLAYFILE` with 8.3 ANSI path normalization). Zero child-process overhead and zero command-line hangs.
* **100% DSP & Audio Effects Preserved**: Leverages AIMP's native 32-bit audio processing engine (equalizers, reverb, bass boost, pitch, sound effects, and volume normalization).
* **Real-Time Bidirectional Telemetry**: Real-time track position, duration, playback state (playing, paused, stopped), and master volume synced live between AIMP and the web controller.
* **Smart Auto-Advance & Queue Isolation**: Automatically clears AIMP's internal queue on each dispatch so AIMP never autoplays random tracks from old playlists. As each song completes, Jam Master instantly queues and plays the exact next song from your deck.

### 🎲 2. Intelligent Anti-Repeat Shuffle Engine
* **Mathematical Cycle Guarantee**: Implements a weighted non-repeating cycle deck that guarantees 100% library coverage before tracks repeat.
* **Configurable Randomness & Anti-Repeat Window**:
  * **Randomness Factor Slider (0.0 – 1.0)**: Adjusts how much track ratings and play frequencies weight the queue vs purely random selection.
  * **Anti-Repeat Timeout Window**: Prevents newly played tracks from appearing again until a percentage of the library has been heard.
  * **Immediate Deck Regeneration**: Changing algorithm settings automatically rebuilds the upcoming queue instantly.
* **Dual Playback Pools**:
  * **Main Music Library Pool**: Shuffles across all selected folders (previews top 50 upcoming tracks in Up Next).
  * **Custom Playlist Pool**: Plays directly from any curated playlist with full queue visibility (shows all 150–500+ tracks in Up Next).
* **Whole Deck Shuffling & Smart Reshuffling**: Toggle between strict non-repeat deck depletion and whole-library weighted shuffling.

### 🎨 3. Modern Responsive Web Interface & Themes
* **7 Hand-Crafted Themes**:
  1. **Midnight Obsidian** (Default sleek navy & deep slate)
  2. **Pitch Black OLED Minimalist** (True #000000 black with crisp borders)
  3. **Cyberpunk Neon** (Vibrant electric yellow, cyan, and deep purple)
  4. **Emerald Matrix** (Terminal hacker green accents on dark charcoal)
  5. **Sunset Velvet** (Warm rose, crimson, and amber gradients)
  6. **Nordic Frost** (Clean arctic ice blue and slate)
  7. **Royal Amethyst** (Deep velvet purple and lavender)
* **Fluid Full-Width Layout**: Zero horizontal scrolling across Custom Playlists and Recently Played History. Tables adapt dynamically to 100% of your screen width.
* **Persistent Bottom Player Bar**: Complete control with volume slider, progress scrubber, star ratings, and quick add-to-playlist.
* **Keyboard Hotkeys**:
  * `Space`: Play / Pause
  * `Right Arrow`: Next track
  * `Left Arrow`: Previous track
  * `Up Arrow`: Reshuffle upcoming deck & change song

### 📜 4. Online Lyrics & Indic Romanization
* **Real-Time Lyrics Scraper**: Automatically fetches synchronized or plain-text lyrics from online sources.
* **Automatic Hindi & Punjabi Romanization**: Transliterates Devanagari and Gurmukhi lyrics into clean Latin script for easy singing along.
* **Fine-Tuning Query Search**: Includes a small inline search box to quickly override song title queries if metadata tags differ online.

### 📦 5. Curation, Portability & Archiving
* **Custom & Random Playlists**: Create playlists manually or generate random mixes up to 500 songs with one-click capacity refills.
* **ZIP Import / Export**: Export playlists with structured JSON manifests for cross-machine portability.
* **Physical File Copy**: Physically copy all audio files from a playlist into any folder.
* **RAR Archive Generation**: Archive entire playlists directly into RAR files.

---

## 🚀 Quick Start

### Prerequisites
* **Windows 10 / 11 (64-bit)**
* **Python 3.10+** (with Python added to system PATH)
* **[AIMP Audio Player](https://www.aimp.ru/)** (recommended installed at `C:\Program Files\AIMP\AIMP.exe`)

### Instant Launchers

1. **Launch Web Player**:
   Double-click `run web.bat` or run:
   ```powershell
   python -m backend.server --open-browser
   ```
   *Opens the modern web interface at `http://127.0.0.1:8765` in your default browser.*

2. **Launch Terminal Console**:
   Double-click `run script.bat` or run:
   ```powershell
   python -m terminal.main
   ```
   *Opens the interactive Rich-powered terminal interface.*

---

## 📁 Project Structure

```
jam master/
├── run web.bat              # One-click web application launcher
├── run script.bat           # One-click terminal application launcher
├── requirements.txt         # Python dependencies
├── README.md                # Project documentation
├── backend/                 # Python backend service & APIs
│   ├── aimp_ipc.py          # Native Win32 IPC controller (AIMP Remote API & Winamp emulation)
│   ├── api.py               # FastAPI REST endpoints
│   ├── config.py            # Configuration defaults & path constants
│   ├── database.py          # SQLite database schema, ratings & history
│   ├── folder_picker.py     # Windows native folder browser dialog integration
│   ├── import_export.py     # ZIP manifest & RAR export services
│   ├── lyrics.py            # Online lyrics scraper with fallback providers
│   ├── metadata.py          # Mutagen audio metadata & embedded artwork extractor
│   ├── player.py            # Audio player dispatch abstraction
│   ├── playlists.py         # Playlist management & entry reordering
│   ├── romanizer.py         # Hindi & Punjabi Devanagari/Gurmukhi transliterator
│   ├── scanner.py           # Multi-threaded filesystem scanner
│   ├── server.py            # Uvicorn HTTP server & auto-advance monitor
│   └── shuffle_engine.py    # Weighted cycle-based anti-repeat shuffle engine
├── frontend/                # React 19 + TypeScript + Tailwind CSS web interface
│   ├── src/
│   │   ├── components/      # PlayerBar, Navigation, Modals, Sliders, Ratings
│   │   ├── views/           # NowPlaying, Library, Playlists, History, Settings
│   │   ├── api.ts           # Typed API client
│   │   └── types.ts         # Shared TypeScript interfaces
│   └── dist/                # Pre-compiled static assets served by backend
└── tests/                   # Automated pytest verification test suite
    ├── test_api.py
    ├── test_database.py
    ├── test_player.py
    ├── test_shuffle_engine.py
    └── test_simulations.py  # Monte Carlo statistical shuffle simulations
```

---

## 🛠️ Verification & Testing

Jam Master includes a full test suite verifying IPC messaging, database migrations, anti-repeat mathematics, and playlist exports:

```powershell
pytest
```

---

## 📄 License
Jam Master is open-source software built for music lovers who demand genuine audio quality and true random playback.

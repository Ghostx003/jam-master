"""HTTP API server and static frontend host for Shuffle Master.
Binds to 127.0.0.1 for local security.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.api import create_api_router
from backend.config import SERVER_HOST, SERVER_PORT, get_app_data_dir, get_db_path
from backend.database import Database
from backend.import_export import ImportExportService
from backend.player import AudioPlayer
from backend.playlists import PlaylistService
from backend.scanner import LibraryScanner
from backend.shuffle_engine import ShuffleEngine


def create_app() -> FastAPI:
    """Builds and configures the FastAPI application instance."""
    app = FastAPI(
        title="Shuffle Master API",
        version="2.0.0",
        docs_url="/docs",
        redoc_url=None,
    )

    # Local security: allow requests from localhost / 127.0.0.1
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:8765",
            "http://127.0.0.1:8765",
            "http://localhost:5173",  # Vite dev server
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Initialize shared singletons
    db = Database()
    saved_aimp = db.get_setting("custom_aimp_path")
    player = AudioPlayer(custom_aimp_path=saved_aimp)
    if not saved_aimp and player.aimp_path:
        db.set_setting("custom_aimp_path", str(player.aimp_path))
    engine = ShuffleEngine(db)

    # Restore persistent engine configuration
    saved_rand = db.get_setting("randomness_factor")
    if saved_rand is not None:
        try:
            engine.config["randomness_factor"] = float(saved_rand)
        except ValueError:
            pass

    saved_ratio = db.get_setting("history_ratio")
    if saved_ratio is not None:
        try:
            engine.config["history_ratio"] = float(saved_ratio)
        except ValueError:
            pass

    scanner = LibraryScanner(db)
    playlist_service = PlaylistService(db)
    import_export_service = ImportExportService(db)

    # Register API routes
    api_router = create_api_router(
        db=db,
        player=player,
        engine=engine,
        scanner=scanner,
        playlist_service=playlist_service,
        import_export_service=import_export_service,
    )
    app.include_router(api_router)

    # Start auto-advance background monitor to ensure AIMP never plays random external tracks
    import threading
    import time

    def _auto_advance_monitor() -> None:
        last_track_id = None
        was_playing = False
        last_switch_time = 0.0

        while True:
            try:
                time.sleep(0.25)
                now = time.time()
                state = engine.get_playback_state()
                curr = state.current_track
                if not curr:
                    last_track_id = None
                    was_playing = False
                    continue

                if curr.id != last_track_id:
                    last_track_id = curr.id
                    was_playing = False

                status = player.get_status()
                pos = status.position
                dur = status.duration if status.duration > 0 else float(curr.duration)
                is_playing = status.state == "playing"

                if is_playing:
                    was_playing = True

                if was_playing and dur > 5.0 and (now - last_switch_time > 2.5):
                    # Track reached completion (within 1.2s of end, or stopped after having played)
                    reached_end = pos >= (dur - 1.2)
                    stopped_at_end = status.state == "stopped" and (pos >= (dur - 4.0) or pos == 0)

                    if reached_end or stopped_at_end:
                        try:
                            last_switch_time = now
                            next_t = engine.next_track(was_skipped=False)
                            player.play(next_t.canonical_path)
                            last_track_id = next_t.id
                            was_playing = True
                        except Exception:
                            pass
            except Exception:
                pass

    monitor_thread = threading.Thread(target=_auto_advance_monitor, daemon=True)
    monitor_thread.start()

    # Mount static frontend if frontend/dist exists
    frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
    if frontend_dist.exists() and (frontend_dist / "index.html").exists():
        app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str, request: Request):
            if full_path.startswith("api/") or full_path == "api":
                from fastapi import HTTPException
                raise HTTPException(status_code=404, detail="API endpoint not found.")
            # If path points to an actual existing file in frontend_dist, return it
            potential_file = frontend_dist / full_path
            if full_path and potential_file.exists() and potential_file.is_file():
                return FileResponse(str(potential_file))
            # Fallback to SPA index.html
            return FileResponse(str(frontend_dist / "index.html"))

    return app


app = create_app()


def main() -> None:
    """Runs the backend server on 127.0.0.1:8765."""
    port = SERVER_PORT
    host = SERVER_HOST

    if "--open-browser" in sys.argv or os.environ.get("OPEN_BROWSER") == "1":
        import threading
        import time
        import webbrowser

        def _launch_browser():
            time.sleep(1.0)
            url = f"http://{host}:{port}"
            print(f"[INFO] Opening web application in default browser: {url}")
            try:
                webbrowser.open(url)
            except Exception as e:
                print(f"[WARNING] Could not open browser automatically: {e}")

        threading.Thread(target=_launch_browser, daemon=True).start()

    print(f"Starting Shuffle Master backend on http://{host}:{port} ...")
    loop_arg = "asyncio:SelectorEventLoop" if sys.platform == "win32" else "auto"
    uvicorn.run(
        "backend.server:app",
        host=host,
        port=port,
        log_level="warning",
        access_log=False,
        reload=False,
        loop=loop_arg,
    )


if __name__ == "__main__":
    main()

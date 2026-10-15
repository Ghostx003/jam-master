"""Terminal-based music shuffler entry point and interactive control loop.
Zero ratings or likes. Fully compliant with modern CLI guidelines.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from rich.panel import Panel

from backend import __version__
from backend.config import get_app_data_dir, get_db_path, get_supported_extensions
from backend.database import Database
from backend.import_export import ImportExportService
from backend.player import AudioPlayer
from backend.playlists import PlaylistService
from backend.scanner import FolderSummary, LibraryScanner
from backend.shuffle_engine import EmptyPoolError, ShuffleEngine
from terminal.interface import (
    console,
    display_folders_table,
    display_main_menu,
    display_now_playing,
    display_playlists_table,
    display_recent_history_table,
    print_banner,
    prompt_directory,
    prompt_folder_selection,
    prompt_numbered_choice,
    prompt_repeat_count,
)


def run_diagnostics(db: Database, player: AudioPlayer) -> None:
    """Displays diagnostic status for troubleshooting."""
    console.print("[bold cyan]Shuffle Master System Diagnostics[/bold cyan]")
    console.print(f"Version: {__version__}")
    console.print(f"App Data Directory: {get_app_data_dir()}")
    console.print(f"SQLite Database: {db.db_path} (exists: {db.db_path.exists()})")

    exts = sorted(get_supported_extensions())
    console.print(f"Supported Extensions ({len(exts)}): {', '.join(exts)}")

    status = player.get_status()
    console.print(f"Player Type: {status.player_type}")
    console.print(f"AIMP Executable: {status.executable_path} (installed: {status.is_installed})")
    console.print(f"AIMP Running: {status.is_running}")
    if status.last_error:
        console.print(f"[yellow]Last Player Note:[/] {status.last_error}")

    folders = db.get_all_eligible_folders()
    total_tracks = sum(f["track_count"] for f in folders)
    console.print(f"Indexed Folders: {len(folders)}")
    console.print(f"Total Available Tracks: {total_tracks}")
    console.print()


def setup_music_directory(db: Database) -> Path:
    """Configures the root music directory per requirements."""
    roots = db.get_all_roots()
    if roots:
        first_root = roots[0]
        saved_path = Path(first_root.path).resolve()
        if saved_path.exists() and saved_path.is_dir():
            console.print(f"[cyan]Saved music directory found:[/] [bold white]{saved_path}[/]")
            console.print("Is the music still at that location?")
            console.print("  [bold yellow]1[/] — Continue with saved location")
            console.print("  [bold yellow]2[/] — Request updated directory")
            choice = prompt_numbered_choice("Choice", ["1", "2"])
            if choice == "1":
                return saved_path
        else:
            console.print(f"[red]The saved music location is missing or inaccessible:[/red] {first_root.path}")
            console.print("[yellow]Please provide a replacement directory.[/yellow]")

    # First launch or updating location
    print_banner()
    music_dir = prompt_directory("Where's the music at?")

    console.print("\n[cyan]Save this location for future use?[/cyan]")
    console.print("  [bold yellow]1[/] — Yes")
    console.print("  [bold yellow]2[/] — No")
    save_choice = prompt_numbered_choice("Choice", ["1", "2"])

    if save_choice == "1":
        db.add_music_root(str(music_dir))
        db.set_setting("saved_music_dir", str(music_dir))
    else:
        db.delete_setting("saved_music_dir")

    return music_dir


def initial_folder_selection(
    scanner: LibraryScanner,
    base_dir: Path,
) -> List[str]:
    """Guides the user through instant folder discovery and selection in under 1 second."""
    with console.status("[bold cyan]Discovering music folders...[/bold cyan]", spinner="dots"):
        eligible_folders = scanner.discover_folders_fast(base_dir)

    if not eligible_folders:
        console.print(f"[red]No folders with supported audio files were found inside:[/] {base_dir}")
        console.print("[yellow]Please verify your files are in supported formats (e.g., MP3, FLAC, WAV, M4A, OGG).[/yellow]")
        sys.exit(1)

    while True:
        selected_paths = prompt_folder_selection(eligible_folders, allow_back=False)
        if not selected_paths:
            console.print("[red]You must select at least one folder to continue.[/red]")
            continue

        with console.status("[bold cyan]Loading selected music...[/bold cyan]", spinner="dots"):
            scanner.scan_selected_folders(selected_paths)

        tracks_in_selection = scanner.db.get_tracks_in_folders(selected_paths, only_available=True)
        console.print(f"\n[green]Selected pool contains [bold]{len(tracks_in_selection)}[/bold] eligible tracks.[/green]")
        console.print("[bold cyan]Are you ready to start jamming?[/bold cyan]")
        console.print("  [bold yellow]1[/] — Yes")
        console.print("  [bold yellow]2[/] — No")
        ready_choice = prompt_numbered_choice("Choice", ["1", "2"])

        if ready_choice == "1":
            return selected_paths


def manage_playlists_cli(db: Database, playlist_service: PlaylistService, engine: ShuffleEngine, player: AudioPlayer) -> None:
    """Submenu for playlist management in the terminal."""
    while True:
        console.print("\n[bold cyan]Playlist Management[/bold cyan]")
        console.print("  [bold yellow]1[/] — View available playlists")
        console.print("  [bold yellow]2[/] — View playlist tracks")
        console.print("  [bold yellow]3[/] — Create a new playlist")
        console.print("  [bold yellow]4[/] — Add tracks from library to playlist")
        console.print("  [bold yellow]5[/] — Shuffle & play a playlist")
        console.print("  [bold yellow]6[/] — Delete a playlist")
        console.print("  [bold yellow]0[/] — Return to main menu")

        choice = prompt_numbered_choice("Choice", ["0", "1", "2", "3", "4", "5", "6"])
        if choice == "0":
            break

        playlists = playlist_service.list_playlists()

        if choice == "1":
            display_playlists_table(playlists)

        elif choice == "2":
            if not playlists:
                console.print("[yellow]No playlists exist yet.[/yellow]")
                continue
            display_playlists_table(playlists)
            idx_str = console.input("[bold yellow]>[/] [white]Enter playlist number:[/] ").strip()
            try:
                num = int(idx_str)
                if 1 <= num <= len(playlists):
                    pl_id = playlists[num - 1]["id"]
                    details = playlist_service.get_playlist_details(pl_id)
                    entries = details.get("entries", [])
                    console.print(f"\n[bold]{details['name']}[/bold] ({len(entries)} tracks):")
                    for e in entries:
                        t = e["track"]
                        console.print(f"  {e['position']}. [white]{t['display_title']}[/] - [dim]{t['display_artist'] or 'Unknown'}[/] ({t['display_duration']})")
                else:
                    console.print("[red]Invalid playlist number.[/red]")
            except ValueError:
                console.print("[red]Invalid number.[/red]")

        elif choice == "3":
            name = console.input("[bold yellow]>[/] [white]Enter new playlist name:[/] ").strip()
            desc = console.input("[bold yellow]>[/] [white]Enter description (optional):[/] ").strip()
            try:
                created = playlist_service.create_playlist(name, desc)
                console.print(f"[green]Created playlist '{created['name']}'.[/green]")
            except ValueError as e:
                console.print(f"[red]Error:[/] {e}")

        elif choice == "4":
            if not playlists:
                console.print("[yellow]Create a playlist first.[/yellow]")
                continue
            display_playlists_table(playlists)
            idx_str = console.input("[bold yellow]>[/] [white]Enter playlist number:[/] ").strip()
            try:
                num = int(idx_str)
                if 1 <= num <= len(playlists):
                    pl_id = playlists[num - 1]["id"]
                    search_q = console.input("[bold yellow]>[/] [white]Search tracks to add (keyword):[/] ").strip()
                    tracks = db.search_tracks(search_q, limit=20, only_available=True)
                    if not tracks:
                        console.print("[yellow]No matching tracks found.[/yellow]")
                        continue

                    for i, t in enumerate(tracks, start=1):
                        console.print(f"  {i}. [white]{t.display_title}[/] - [dim]{t.display_artist}[/]")

                    sel = console.input("[bold yellow]>[/] [white]Enter track numbers to add (e.g. 1 2 4):[/] ").strip()
                    parts = sel.split()
                    ids_to_add = []
                    for p in parts:
                        try:
                            t_idx = int(p)
                            if 1 <= t_idx <= len(tracks):
                                ids_to_add.append(tracks[t_idx - 1].id)
                        except ValueError:
                            pass

                    if ids_to_add:
                        added = playlist_service.add_tracks(pl_id, ids_to_add)
                        console.print(f"[green]Added {added} track(s) to playlist.[/green]")
            except ValueError:
                console.print("[red]Invalid number.[/red]")

        elif choice == "5":
            if not playlists:
                console.print("[yellow]No playlists exist yet.[/yellow]")
                continue
            display_playlists_table(playlists)
            idx_str = console.input("[bold yellow]>[/] [white]Enter playlist number to play:[/] ").strip()
            try:
                num = int(idx_str)
                if 1 <= num <= len(playlists):
                    pl_id = playlists[num - 1]["id"]
                    pool_sz = engine.set_playlist_pool(pl_id)
                    if pool_sz > 0:
                        t = engine.next_track()
                        player.play(t.canonical_path)
                        console.print(f"[green]Now playing playlist '{playlists[num - 1]['name']}' ({pool_sz} tracks).[/green]")
                        break
                    else:
                        console.print("[yellow]Selected playlist has no playable tracks.[/yellow]")
            except ValueError:
                console.print("[red]Invalid number.[/red]")

        elif choice == "6":
            if not playlists:
                console.print("[yellow]No playlists exist yet.[/yellow]")
                continue
            display_playlists_table(playlists)
            idx_str = console.input("[bold yellow]>[/] [white]Enter playlist number to delete:[/] ").strip()
            try:
                num = int(idx_str)
                if 1 <= num <= len(playlists):
                    pl_name = playlists[num - 1]["name"]
                    confirm = console.input(f"[bold red]Are you sure you want to delete '{pl_name}'? (y/n):[/] ").strip().lower()
                    if confirm == "y":
                        playlist_service.delete_playlist(playlists[num - 1]["id"])
                        console.print(f"[green]Deleted playlist '{pl_name}'.[/green]")
            except ValueError:
                console.print("[red]Invalid number.[/red]")


def manage_import_export_cli(db: Database, import_export_service: ImportExportService) -> None:
    """Submenu for ZIP import/export in the terminal."""
    while True:
        console.print("\n[bold cyan]ZIP Import / Export Tools[/bold cyan]")
        console.print("  [bold yellow]1[/] — Export playlists to ZIP archive")
        console.print("  [bold yellow]2[/] — Import playlists from ZIP archive")
        console.print("  [bold yellow]0[/] — Return to main menu")

        choice = prompt_numbered_choice("Choice", ["0", "1", "2"])
        if choice == "0":
            break

        playlists = db.list_playlists()

        if choice == "1":
            if not playlists:
                console.print("[yellow]No playlists exist to export.[/yellow]")
                continue
            display_playlists_table([p.to_dict() for p in playlists])
            console.print("[dim]Enter playlist numbers to export separated by spaces (or 'all'):[/dim]")
            sel = console.input("[bold yellow]>[/] [white]Selection:[/] ").strip()

            target_ids = []
            if sel.lower() == "all":
                target_ids = [p.id for p in playlists]
            else:
                for part in sel.split():
                    try:
                        n = int(part)
                        if 1 <= n <= len(playlists):
                            target_ids.append(playlists[n - 1].id)
                    except ValueError:
                        pass

            if not target_ids:
                console.print("[red]No valid playlists selected.[/red]")
                continue

            out_dir = Path.home() / "Desktop"
            if not out_dir.exists():
                out_dir = Path.cwd()
            out_file = out_dir / "playlists_export.zip"

            zip_buf = import_export_service.export_playlists_to_zip(target_ids)
            with open(out_file, "wb") as f:
                f.write(zip_buf.getvalue())

            console.print(f"[bold green]Successfully exported {len(target_ids)} playlist(s) to:[/] {out_file}")

        elif choice == "2":
            zip_path_str = console.input("[bold yellow]>[/] [white]Enter path to ZIP archive:[/] ").strip().strip('"').strip("'")
            zip_path = Path(zip_path_str)
            if not zip_path.exists() or not zip_path.is_file():
                console.print(f"[red]File not found:[/red] {zip_path_str}")
                continue

            try:
                with open(zip_path, "rb") as f:
                    preview = import_export_service.preview_import_zip(f)

                console.print(f"\n[green]Archive Preview:[/green] {preview['playlist_count']} playlist(s), {preview['total_tracks']} tracks ({preview['matched_tracks']} matched locally).")
                for p in preview["playlists"]:
                    conflict = " [bold red](Name Conflict)[/]" if p["has_name_conflict"] else ""
                    console.print(f"  - {p['name']} ({p['track_count']} tracks){conflict}")

                console.print("\nConflict resolution policy:")
                console.print("  [bold yellow]1[/] — Rename duplicate playlists")
                console.print("  [bold yellow]2[/] — Replace existing playlists")
                console.print("  [bold yellow]3[/] — Skip conflicting playlists")
                c_choice = prompt_numbered_choice("Policy", ["1", "2", "3"])
                policy = "rename" if c_choice == "1" else ("replace" if c_choice == "2" else "skip")

                with open(zip_path, "rb") as f:
                    res = import_export_service.commit_import_zip(f, conflict_policy=policy)

                console.print(f"[bold green]Import complete![/] Imported {res['imported_playlists']} playlist(s).")
            except Exception as e:
                console.print(f"[red]Import failed:[/] {e}")


def main() -> None:
    """Main terminal loop."""
    parser = argparse.ArgumentParser(description="Shuffle Master - Terminal Music Shuffler")
    parser.add_argument("--diag", action="store_true", help="Run system diagnostics and exit")
    parser.add_argument("--rescan", action="store_true", help="Force a rescan of all music directories")
    parser.add_argument("--version", action="version", version=f"Shuffle Master v{__version__}")
    args = parser.parse_args()

    db = Database()
    saved_aimp = db.get_setting("custom_aimp_path")
    player = AudioPlayer(custom_aimp_path=saved_aimp)
    playlist_service = PlaylistService(db)
    import_export_service = ImportExportService(db)

    if args.diag:
        run_diagnostics(db, player)
        sys.exit(0)

    # 1. Startup & Music Directory Configuration
    base_dir = setup_music_directory(db)
    scanner = LibraryScanner(db)

    # 2. Scanning & Folder Selection
    selected_folders = initial_folder_selection(scanner, base_dir)

    # 3. Initialize Shuffle Engine
    engine = ShuffleEngine(db)
    pool_size = engine.set_folder_pool(selected_folders)

    if pool_size == 0:
        console.print("[red]Selected folders contain no playable audio tracks.[/red]")
        sys.exit(1)

    # 4. Begin Initial Playback
    current_track = engine.next_track(was_skipped=False)
    player.play(current_track.canonical_path)

    # 5. Main Control Loop
    while True:
        state = engine.get_playback_state()
        display_now_playing(state)

        action = display_main_menu()

        if action == "1":
            # Change song
            next_t = engine.next_track(was_skipped=True)
            player.play(next_t.canonical_path)

        elif action == "2":
            # Repeat the current song
            repeats = prompt_repeat_count()
            if repeats > 0:
                engine.set_repeat(repeats)
                if state.current_track:
                    player.play(state.current_track.canonical_path)
                    console.print(f"[green]Queued '{state.current_track.display_title}' to repeat {repeats} additional time(s).[/green]")
            else:
                console.print("[dim]Repeat cancelled.[/dim]")

        elif action == "3":
            # Shuffle more
            fresh_t = engine.fresh_shuffle()
            player.play(fresh_t.canonical_path)

        elif action == "4":
            # Add another folder
            with console.status("[bold cyan]Scanning folders...[/bold cyan]", spinner="dots"):
                all_folders = scanner.discover_folders_fast(base_dir)
            active_paths = engine.selected_folder_paths
            available_to_add = [f for f in all_folders if f.folder_path not in active_paths]

            if not available_to_add:
                console.print("[yellow]All available audio folders are already included in your pool.[/yellow]")
            else:
                new_selections = prompt_folder_selection(available_to_add, allow_back=True)
                if new_selections:
                    with console.status("[bold cyan]Loading new folders...[/bold cyan]", spinner="dots"):
                        scanner.scan_selected_folders(new_selections)
                    for folder_p in new_selections:
                        engine.add_folder_to_pool(folder_p)
                    new_state = engine.get_playback_state()
                    console.print(f"[green]Added {len(new_selections)} folder(s). New pool size: [bold]{new_state.pool_size}[/bold] tracks.[/green]")

        elif action == "5":
            # Open playlist management
            manage_playlists_cli(db, playlist_service, engine, player)

        elif action == "6":
            # Show recently played
            history = db.get_recent_history(limit=25)
            display_recent_history_table(history)
            if history:
                console.print("\n[dim]Enter a number to replay track, or press Enter to return.[/dim]")
                raw_pick = console.input("[bold yellow]>[/] [white]Replay track #:[/] ").strip()
                if raw_pick:
                    try:
                        n = int(raw_pick)
                        if 1 <= n <= len(history):
                            chosen_tid = history[n - 1]["track"]["id"]
                            replayed = engine.play_specific_track(chosen_tid)
                            player.play(replayed.canonical_path)
                            console.print(f"[green]Now playing '{replayed.display_title}'.[/green]")
                    except ValueError:
                        pass

        elif action == "7":
            # Open import/export tools
            manage_import_export_cli(db, import_export_service)

        elif action == "8":
            # Refresh music library
            with console.status("[bold cyan]Refreshing music library...[/bold cyan]", spinner="dots"):
                found, new_or_up, missing = scanner.scan_directory(base_dir)
            console.print(f"[green]Library refreshed.[/green] {found} tracks indexed ({new_or_up} updated/new, {missing} marked missing).")
            # Refresh engine pool
            engine._refresh_tracks_from_db()
            engine._rebuild_deck(force=True)

        elif action == "9":
            # Exit
            console.print("\n[bold cyan]Thank you for jamming with Shuffle Master. Keep rocking![/bold cyan]")
            break


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        console.print("\n[dim]Session closed cleanly.[/dim]")
        sys.exit(0)

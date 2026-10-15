"""Terminal interface, Rich panels, tables, and interactive prompts.
Zero ratings or likes. Fully compliant with modern CLI guidelines.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from rich.align import Align
from rich.box import ROUNDED, SIMPLE_HEAVY
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from backend.database import TrackRecord
from backend.scanner import FolderSummary
from backend.shuffle_engine import PlaybackState

console = Console()


def print_banner() -> None:
    """Renders the signature header banner."""
    banner_text = Text()
    banner_text.append("S H U F F L E // M A S T E R", style="bold cyan")
    banner_text.append("\nIntelligent Audio Shuffler for AIMP", style="dim italic")

    panel = Panel(
        Align.center(banner_text),
        box=ROUNDED,
        border_style="bright_blue",
        padding=(0, 2),
    )
    console.print()
    console.print(panel)
    console.print()


def prompt_numbered_choice(
    prompt_text: str,
    valid_options: Sequence[str],
    allow_empty: bool = False,
) -> str:
    """Prompts the user for a single numbered choice with validation."""
    valid_set = set(str(opt).strip() for opt in valid_options)

    while True:
        try:
            raw = console.input(f"[bold yellow]>[/] [bold white]{prompt_text}[/] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Operation cancelled.[/dim]")
            return ""

        if not raw and allow_empty:
            return ""

        if raw in valid_set:
            return raw

        console.print(f"[red]Invalid selection.[/red] Please enter one of: {', '.join(sorted(valid_set))}")


def prompt_directory(prompt_text: str = "Where's the music at?") -> Path:
    """Asks for a directory path, validating existence and directory type."""
    console.print(f"[bold cyan]{prompt_text}[/bold cyan]")
    while True:
        try:
            raw = console.input("[bold yellow]>[/] [white]Enter music folder path:[/] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Exiting...[/dim]")
            raise SystemExit(0)

        raw = raw.strip('"').strip("'")
        if not raw:
            console.print("[red]Path cannot be empty.[/red]")
            continue

        path = Path(raw).expanduser()
        try:
            resolved = path.resolve()
            if not resolved.exists():
                console.print(f"[red]Directory not found:[/red] {resolved}")
                continue
            if not resolved.is_dir():
                console.print(f"[red]Path is not a directory:[/red] {resolved}")
                continue

            return resolved
        except Exception as e:
            console.print(f"[red]Error checking path:[/red] {e}")


def display_now_playing(state: PlaybackState) -> None:
    """Renders the Now Playing terminal panel (Zero ratings)."""
    track = state.current_track
    if not track:
        console.print(Panel("[dim]No track is currently playing.[/dim]", box=ROUNDED))
        return

    title_text = Text(track.display_title, style="bold bright_white")
    artist_val = track.display_artist or "[dim]Unknown Artist[/dim]"
    artist_text = Text.from_markup(f"[cyan]Artist:[/] {artist_val}")
    duration_text = Text.from_markup(f"[cyan]Duration:[/] {track.display_duration}")
    mode_text = Text.from_markup(f"[cyan]Mode:[/] [bold magenta]{state.mode}[/]")
    pool_text = Text.from_markup(f"[cyan]Pool:[/] [green]{state.pool_size}[/] tracks ({state.context_name})")
    plays_text = Text.from_markup(f"[cyan]Play Count:[/] [dim]{track.play_count}[/dim]")

    table = Table.grid(padding=(0, 3))
    table.add_column()
    table.add_column()

    table.add_row(title_text, mode_text)
    table.add_row(artist_text, pool_text)
    table.add_row(duration_text, plays_text)

    panel = Panel(
        table,
        title="[bold green]NOW PLAYING[/bold green]",
        subtitle=f"[dim]{track.filename}[/dim]",
        box=ROUNDED,
        border_style="green",
        padding=(0, 1),
    )
    console.print()
    console.print(panel)


def display_main_menu() -> str:
    """Displays the exact 9 action labels specified in the requirements without clutter."""
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="bold yellow", justify="right")
    table.add_column(style="white")

    table.add_row("1", "Change song")
    table.add_row("2", "Repeat the current song")
    table.add_row("3", "Shuffle more")
    table.add_row("4", "Add another folder")
    table.add_row("5", "Open playlist management")
    table.add_row("6", "Show recently played")
    table.add_row("7", "Open import/export tools")
    table.add_row("8", "Refresh music library")
    table.add_row("9", "Exit")

    menu_panel = Panel(
        table,
        title="[bold cyan]ACTIONS[/bold cyan]",
        box=ROUNDED,
        border_style="dim",
        padding=(0, 1),
    )
    console.print(menu_panel)

    return prompt_numbered_choice(
        "Select action",
        ["1", "2", "3", "4", "5", "6", "7", "8", "9"],
    )


def display_folders_table(
    folders: List[FolderSummary],
    already_selected_paths: Optional[Sequence[str]] = None,
) -> None:
    """Displays numbered table of available folders with track counts and durations."""
    selected_set = set(already_selected_paths or [])
    table = Table(
        box=SIMPLE_HEAVY,
        header_style="bold cyan",
        show_lines=False,
    )
    table.add_column("#", justify="right", style="bold yellow")
    table.add_column("Folder Name", style="white")
    table.add_column("Tracks", justify="right", style="green")
    table.add_column("Total Audio", justify="right", style="dim")
    table.add_column("Status", justify="center")

    for idx, folder in enumerate(folders, start=1):
        is_sel = folder.folder_path in selected_set
        status = "[bold green]Selected[/]" if is_sel else "[dim]Available[/]"
        table.add_row(
            str(idx),
            folder.display_name,
            str(folder.track_count),
            folder.formatted_duration,
            status,
        )

    console.print(table)


def prompt_folder_selection(
    folders: List[FolderSummary],
    already_selected_paths: Optional[Sequence[str]] = None,
    allow_back: bool = False,
) -> List[str]:
    """Handles folder selection with support for single and multi-selection modes."""
    if not folders:
        console.print("[red]No eligible audio folders found.[/red]")
        return []

    console.print("[bold cyan]How do you want to select your music?[/bold cyan]")
    console.print("  [bold yellow]1[/] — Select one folder")
    console.print("  [bold yellow]2[/] — Select multiple folders")
    if allow_back:
        console.print("  [bold yellow]0[/] — Return to previous menu")

    options = ["1", "2"]
    if allow_back:
        options.append("0")

    choice = prompt_numbered_choice("Choice", options)
    if choice == "0":
        return []

    console.print()
    display_folders_table(folders, already_selected_paths)
    console.print()

    total_folders = len(folders)

    if choice == "1":
        while True:
            sel = console.input(f"[bold yellow]>[/] [white]Enter folder number (1-{total_folders}):[/] ").strip()
            if not sel and allow_back:
                return []
            try:
                num = int(sel)
                if 1 <= num <= total_folders:
                    chosen = folders[num - 1].folder_path
                    return [chosen]
                console.print(f"[red]Please enter a number between 1 and {total_folders}.[/red]")
            except ValueError:
                console.print("[red]Invalid number.[/red]")
    else:
        console.print("[dim]Enter folder numbers separated by spaces (e.g. 1 2 4 7):[/dim]")
        while True:
            raw = console.input("[bold yellow]>[/] [white]Folders to include:[/] ").strip()
            if not raw:
                console.print("[red]Please enter at least one folder number.[/red]")
                continue

            parts = raw.split()
            valid_indexes: List[int] = []
            has_error = False

            for part in parts:
                try:
                    num = int(part)
                    if 1 <= num <= total_folders:
                        if num not in valid_indexes:
                            valid_indexes.append(num)
                    else:
                        console.print(f"[red]Index {num} is out of bounds (1-{total_folders}).[/red]")
                        has_error = True
                except ValueError:
                    console.print(f"[red]'{part}' is not a valid number.[/red]")
                    has_error = True

            if has_error:
                continue

            if not valid_indexes:
                console.print("[red]No valid folders were selected.[/red]")
                continue

            chosen_paths = [folders[i - 1].folder_path for i in valid_indexes]
            return chosen_paths


def prompt_repeat_count() -> int:
    """Asks for additional repeats count."""
    console.print("[cyan]How many additional times would you like to repeat this song?[/cyan]")
    while True:
        raw = console.input("[bold yellow]>[/] [white]Enter repeat count (e.g. 1, 2, 3...):[/] ").strip()
        try:
            count = int(raw)
            if count >= 0:
                return count
            console.print("[red]Repeat count cannot be negative.[/red]")
        except ValueError:
            console.print("[red]Please enter a valid positive integer.[/red]")


def display_playlists_table(playlists: List[Dict[str, Any]]) -> None:
    """Displays table of available playlists."""
    if not playlists:
        console.print(Panel("[dim]No playlists exist yet.[/dim]", box=ROUNDED))
        return

    table = Table(box=SIMPLE_HEAVY, header_style="bold cyan", title="Playlists")
    table.add_column("#", justify="right", style="bold yellow")
    table.add_column("Playlist Name", style="white")
    table.add_column("Tracks", justify="right", style="green")
    table.add_column("Description", style="dim")

    for idx, p in enumerate(playlists, start=1):
        table.add_row(str(idx), p["name"], str(p["track_count"]), p.get("description", ""))

    console.print(table)


def display_recent_history_table(history: List[Dict[str, Any]]) -> None:
    """Displays table of recently played tracks."""
    if not history:
        console.print(Panel("[dim]No tracks have been played yet.[/dim]", box=ROUNDED))
        return

    table = Table(box=SIMPLE_HEAVY, header_style="bold cyan", title="Recently Played Tracks")
    table.add_column("#", justify="right", style="bold yellow")
    table.add_column("Title", style="white")
    table.add_column("Artist", style="dim")
    table.add_column("Duration", justify="right", style="cyan")
    table.add_column("Plays", justify="right", style="green")

    for idx, item in enumerate(history, start=1):
        t = item["track"]
        table.add_row(
            str(idx),
            t["display_title"],
            t["display_artist"] or "--",
            t["display_duration"],
            str(t["play_count"]),
        )

    console.print(table)

"""AIMP audio playback controller and Windows file-association fallback.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import winreg
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.aimp_ipc import AimpIpcController


@dataclass
class PlayerStatus:
    """Diagnostic status for the audio player."""
    player_type: str  # "AIMP" or "Windows Association Fallback"
    executable_path: Optional[str]
    is_installed: bool
    is_running: bool
    last_error: Optional[str] = None
    aimp_connected: bool = False
    position: float = 0.0
    duration: float = 0.0
    volume: int = 100
    state: str = "stopped"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "player_type": self.player_type,
            "executable_path": self.executable_path,
            "is_installed": self.is_installed,
            "is_running": self.is_running,
            "last_error": self.last_error,
            "aimp_connected": self.aimp_connected,
            "position": self.position,
            "duration": self.duration,
            "volume": self.volume,
            "state": self.state,
        }


class AudioPlayer:
    """Controls AIMP playback on Windows with automatic executable discovery and safe fallbacks."""

    def __init__(self, custom_aimp_path: Optional[str] = None) -> None:
        self.aimp_path: Optional[Path] = None
        self.last_error: Optional[str] = None
        self.ipc = AimpIpcController()

        if custom_aimp_path:
            p = Path(custom_aimp_path)
            if p.exists() and p.is_file():
                self.aimp_path = p.resolve()

        if not self.aimp_path:
            self.aimp_path = self._discover_aimp()

    def _discover_aimp(self) -> Optional[Path]:
        """Locates the AIMP executable via standard paths, registry, and PATH."""
        # 1. Common 64-bit and 32-bit install paths
        candidates: List[Path] = [
            Path("C:/Program Files/AIMP/AIMP.exe"),
            Path("C:/Program Files (x86)/AIMP/AIMP.exe"),
            Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "AIMP" / "AIMP.exe",
            Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "AIMP" / "AIMP.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "AIMP" / "AIMP.exe",
        ]

        for cand in candidates:
            if cand.exists() and cand.is_file():
                return cand.resolve()

        # 2. Check PATH environment variable
        which_path = shutil.which("aimp.exe") or shutil.which("aimp")
        if which_path:
            return Path(which_path).resolve()

        # 3. Windows Registry lookup
        reg_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]

        for hkey, subkey in reg_paths:
            try:
                with winreg.OpenKey(hkey, subkey) as root_key:
                    for i in range(winreg.QueryInfoKey(root_key)[0]):
                        try:
                            key_name = winreg.EnumKey(root_key, i)
                            with winreg.OpenKey(root_key, key_name) as app_key:
                                display_name, _ = winreg.QueryValueEx(app_key, "DisplayName")
                                if "AIMP" in str(display_name):
                                    try:
                                        install_dir, _ = winreg.QueryValueEx(app_key, "InstallLocation")
                                        if install_dir:
                                            exe = Path(install_dir) / "AIMP.exe"
                                            if exe.exists():
                                                return exe.resolve()
                                    except OSError:
                                        pass

                                    try:
                                        icon_path, _ = winreg.QueryValueEx(app_key, "DisplayIcon")
                                        if icon_path:
                                            parent_dir = Path(icon_path).parent
                                            exe = parent_dir / "AIMP.exe"
                                            if exe.exists():
                                                return exe.resolve()
                                    except OSError:
                                        pass
                        except OSError:
                            continue
            except OSError:
                continue

        return None

    def is_aimp_running(self) -> bool:
        """Checks if an AIMP process is currently active."""
        if sys.platform != "win32":
            return False

        try:
            output = subprocess.check_output(
                ["tasklist", "/FI", "IMAGENAME eq AIMP.exe", "/NH"],
                text=True,
                stderr=subprocess.DEVNULL,
            )
            return "AIMP.exe" in output
        except Exception:
            return False

    def play(self, audio_path: Path | str) -> bool:
        """Sends track directly to AIMP to load and play immediately with full DSP preservation."""
        path_obj = Path(audio_path).resolve()
        if not path_obj.exists():
            self.last_error = f"Audio file not found: {audio_path}"
            return False

        path_str = str(path_obj)

        # 1. Prefer native Win32 IPC (WM_COPYDATA) when AIMP is detected or running
        if self.ipc.is_connected() or self.is_aimp_running():
            if self.ipc.play_file(path_str):
                self.last_error = None
                return True

        # 2. If AIMP is not currently running, launch AIMP executable
        if not self.aimp_path or not self.aimp_path.exists():
            self.aimp_path = self._discover_aimp()

        if self.aimp_path and self.aimp_path.exists():
            try:
                flags = 0x00000008 if sys.platform == "win32" else 0
                subprocess.Popen(
                    [str(self.aimp_path), path_str],
                    creationflags=flags,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                import time
                for _ in range(15):
                    time.sleep(0.1)
                    if self.ipc.is_connected():
                        self.ipc.disable_internal_shuffle_and_repeat()
                        if self.ipc.get_playback_state() != 2:
                            self.ipc.play_file(path_str)
                        break
                self.last_error = None
                return True
            except Exception as e:
                self.last_error = f"Failed to launch AIMP: {e}"

        self.last_error = "AIMP executable not found. Please verify AIMP is installed at 'C:\\Program Files\\AIMP\\AIMP.exe' or configure its path in Settings."
        return False

    def pause(self, current_track_path: Optional[str] = None) -> bool:
        """Toggles play/pause in AIMP using native Win32 IPC or CLI fallback, starting track if stopped."""
        if self.ipc.is_connected():
            state = self.ipc.get_playback_state()
            if state == 2:  # Currently playing -> pause
                return self.ipc.pause()
            elif state == 1:  # Currently paused -> resume play
                return self.ipc.play()
            elif state == 0:  # Stopped -> start track or send play
                if current_track_path:
                    return self.play(current_track_path)
                return self.ipc.play()
            return self.ipc.toggle_play_pause()

        # If not connected via IPC and track path is provided, start playing track
        if current_track_path and not self.is_aimp_running():
            return self.play(current_track_path)

        if self.aimp_path and self.aimp_path.exists():
            try:
                flags = 0x00000008 if sys.platform == "win32" else 0
                subprocess.Popen(
                    [str(self.aimp_path), "/PLAY_PAUSE"],
                    creationflags=flags,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return True
            except Exception as e:
                self.last_error = f"Failed to send /PLAY_PAUSE to AIMP: {e}"
        return False

    def resume(self, current_track_path: Optional[str] = None) -> bool:
        """Forces playback to start or resume in AIMP using native Win32 IPC or CLI fallback."""
        if self.ipc.is_connected():
            state = self.ipc.get_playback_state()
            if state == 1:
                return self.ipc.play()
            elif state == 0 and current_track_path:
                return self.play(current_track_path)
            elif state == 0:
                return self.ipc.play()
            return True

        if current_track_path and not self.is_aimp_running():
            return self.play(current_track_path)

        if self.aimp_path and self.aimp_path.exists():
            try:
                flags = 0x00000008 if sys.platform == "win32" else 0
                subprocess.Popen(
                    [str(self.aimp_path), "/PLAY"],
                    creationflags=flags,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return True
            except Exception as e:
                self.last_error = f"Failed to send /PLAY to AIMP: {e}"
        return False

    def stop(self) -> bool:
        """Stops playback in AIMP using native Win32 IPC or CLI fallback."""
        if self.ipc.is_connected():
            return self.ipc.stop()

        if self.aimp_path and self.aimp_path.exists():
            try:
                flags = 0x00000008 if sys.platform == "win32" else 0
                subprocess.Popen(
                    [str(self.aimp_path), "/STOP"],
                    creationflags=flags,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return True
            except Exception as e:
                self.last_error = f"Failed to send stop to AIMP: {e}"
        return False

    def seek(self, position_seconds: float) -> bool:
        """Seeks to the given position in seconds in AIMP."""
        return self.ipc.seek(position_seconds)

    def get_position(self) -> float:
        """Returns current playback position in seconds directly from AIMP."""
        return self.ipc.get_position()

    def get_duration(self) -> float:
        """Returns current track duration in seconds directly from AIMP."""
        return self.ipc.get_duration()

    def is_playing(self) -> bool:
        """Returns True if AIMP is actively playing."""
        return self.ipc.is_playing()

    def is_aimp_connected(self) -> bool:
        """Returns True if AIMP IPC is connected and active."""
        return self.ipc.is_connected()

    def get_volume(self) -> int:
        """Returns current volume percentage (0-100) from AIMP."""
        return self.ipc.get_volume()

    def set_volume(self, volume_percent: int) -> bool:
        """Sets AIMP volume percentage (0-100)."""
        return self.ipc.set_volume(volume_percent)

    def get_status(self) -> PlayerStatus:
        """Returns the current diagnostic status of player integration with IPC telemetry."""
        is_installed = self.aimp_path is not None and self.aimp_path.exists()
        ipc_info = self.ipc.get_info()
        running = (self.is_aimp_running() if is_installed else False) or ipc_info["connected"]

        player_type = "AIMP" if is_installed else "Windows Association Fallback"
        exe_path = str(self.aimp_path) if self.aimp_path else None

        return PlayerStatus(
            player_type=player_type,
            executable_path=exe_path,
            is_installed=is_installed,
            is_running=running,
            last_error=self.last_error,
            aimp_connected=ipc_info["connected"],
            position=ipc_info["position"],
            duration=ipc_info["duration"],
            volume=ipc_info["volume"],
            state=ipc_info["state"],
        )

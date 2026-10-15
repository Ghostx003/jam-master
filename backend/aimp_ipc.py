"""AIMP Win32 IPC Controller.
Provides direct, real-time control of AIMP audio player on Windows:
- Synchronized playback state (playing, paused, stopped)
- Real-time playback position and track duration
- Precise seeking to any second or millisecond
- Master volume read & write
- Play, pause, resume, stop, and track navigation commands

All while preserving AIMP's native DSP audio processing engine
(equalizer, reverb, bass boost, pitch, playback speed, sound effects).
"""

from __future__ import annotations

import sys
import time
from typing import Any, Dict, Optional, Tuple

# Constants for AIMP Remote API
WM_USER = 0x0400
WM_AIMP_COMMAND = WM_USER + 0x75
WM_AIMP_PROPERTY = WM_USER + 0x77

# Property Access Flags
AIMP_RA_PROPVALUE_GET = 0
AIMP_RA_PROPVALUE_SET = 1

# Properties
AIMP_RA_PROPERTY_VERSION = 0x10
AIMP_RA_PROPERTY_PLAYER_POSITION = 0x20  # milliseconds
AIMP_RA_PROPERTY_PLAYER_DURATION = 0x30  # milliseconds
AIMP_RA_PROPERTY_PLAYER_STATE = 0x40     # 0: Stopped, 1: Paused, 2: Playing
AIMP_RA_PROPERTY_VOLUME = 0x50           # 0-100%
AIMP_RA_PROPERTY_MUTE = 0x60             # 0 or 1
AIMP_RA_PROPERTY_TRACK_REPEAT = 0x70
AIMP_RA_PROPERTY_TRACK_SHUFFLE = 0x80

# Commands
AIMP_RA_CMD_BASE = 10
AIMP_RA_CMD_PLAY = AIMP_RA_CMD_BASE + 3       # 13
AIMP_RA_CMD_PLAYPAUSE = AIMP_RA_CMD_BASE + 4  # 14
AIMP_RA_CMD_PAUSE = AIMP_RA_CMD_BASE + 5      # 15
AIMP_RA_CMD_STOP = AIMP_RA_CMD_BASE + 6       # 16
AIMP_RA_CMD_NEXT = AIMP_RA_CMD_BASE + 7       # 17
AIMP_RA_CMD_PREV = AIMP_RA_CMD_BASE + 8       # 18


class AimpIpcController:
    """Controls and monitors AIMP directly via native Windows IPC messaging."""

    def __init__(self) -> None:
        self._user32 = None
        self._cached_hwnd: int = 0
        self._last_hwnd_check: float = 0.0

        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes

            self._user32 = ctypes.windll.user32
            # Configure 64-bit safe SendMessageW signature
            self._user32.SendMessageW.argtypes = [
                wintypes.HWND,
                wintypes.UINT,
                wintypes.WPARAM,
                wintypes.LPARAM,
            ]
            self._user32.SendMessageW.restype = ctypes.c_int64

    def get_window_handle(self) -> int:
        """Finds or validates the HWND for AIMP's remote API window."""
        if not self._user32:
            return 0

        now = time.time()
        # Cache check for 1 second unless invalid
        if self._cached_hwnd and (now - self._last_hwnd_check < 1.0):
            if self._user32.IsWindow(self._cached_hwnd):
                return self._cached_hwnd

        self._last_hwnd_check = now

        # Try official AIMP Remote API window class first
        hwnd = self._user32.FindWindowW("AIMP2_RemoteInfo", None)
        if not hwnd:
            # Fallback to Winamp emulation window if present
            hwnd = self._user32.FindWindowW("Winamp v1.x", None)

        if not hwnd:
            try:
                h_desk = self._user32.OpenDesktopW("default", 0, False, 0x01FF)
                if h_desk:
                    self._user32.SetThreadDesktop(h_desk)
                    hwnd = self._user32.FindWindowW("AIMP2_RemoteInfo", None)
                    if not hwnd:
                        hwnd = self._user32.FindWindowW("Winamp v1.x", None)
            except Exception:
                pass

        self._cached_hwnd = hwnd or 0
        return self._cached_hwnd

    def get_winamp_window_handle(self) -> int:
        """Finds the HWND for AIMP's Winamp emulation window ('Winamp v1.x')."""
        if not self._user32:
            return 0
        hwnd = self._user32.FindWindowW("Winamp v1.x", None)
        if not hwnd:
            try:
                h_desk = self._user32.OpenDesktopW("default", 0, False, 0x01FF)
                if h_desk:
                    self._user32.SetThreadDesktop(h_desk)
                    hwnd = self._user32.FindWindowW("Winamp v1.x", None)
            except Exception:
                pass
        return hwnd or 0

    def disable_internal_shuffle_and_repeat(self) -> None:
        """Ensures AIMP's internal shuffle and repeat are disabled so it does not hijack playback queue."""
        hwnd = self.get_window_handle()
        if not hwnd or not self._user32:
            return
        try:
            self._user32.SendMessageW(
                hwnd,
                WM_AIMP_PROPERTY,
                AIMP_RA_PROPERTY_TRACK_SHUFFLE | AIMP_RA_PROPVALUE_SET,
                0,
            )
            self._user32.SendMessageW(
                hwnd,
                WM_AIMP_PROPERTY,
                AIMP_RA_PROPERTY_TRACK_REPEAT | AIMP_RA_PROPVALUE_SET,
                0,
            )
        except Exception:
            pass

    def play_file(self, file_path: Any) -> bool:
        """Dispatches an audio file directly into AIMP using native Winamp emulation WM_COPYDATA.
        This immediately loads and starts playing the track inside AIMP with its full DSP audio
        engine and UI updated, without spawning child processes or causing CLI lockups.
        """
        if not self._user32 or sys.platform != "win32":
            return False

        hwnd_winamp = self.get_winamp_window_handle()
        if not hwnd_winamp:
            return False

        import ctypes
        from ctypes import wintypes
        from pathlib import Path

        path_obj = Path(file_path).resolve()
        if not path_obj.exists():
            return False

        long_path = str(path_obj)

        # Obtain 8.3 short path if available to guarantee pure ANSI compatibility across all locales
        short_path = long_path
        try:
            kernel32 = ctypes.windll.kernel32
            kernel32.GetShortPathNameW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
            kernel32.GetShortPathNameW.restype = wintypes.DWORD
            buf = ctypes.create_unicode_buffer(1024)
            res = kernel32.GetShortPathNameW(long_path, buf, 1024)
            if res > 0 and buf.value:
                short_path = buf.value
        except Exception:
            pass

        class COPYDATASTRUCT(ctypes.Structure):
            _fields_ = [
                ("dwData", ctypes.c_size_t),
                ("cbData", wintypes.DWORD),
                ("lpData", ctypes.c_void_p),
            ]

        try:
            data_bytes = (short_path + "\0").encode("ascii")
        except Exception:
            try:
                data_bytes = (long_path + "\0").encode("mbcs")
            except Exception:
                data_bytes = (long_path + "\0").encode("utf-8")

        cds = COPYDATASTRUCT()
        cds.dwData = 100  # IPC_PLAYFILE
        cds.cbData = len(data_bytes)
        cds.lpData = ctypes.cast(ctypes.c_char_p(data_bytes), ctypes.c_void_p)

        try:
            WM_USER = 0x0400
            IPC_DELETE = 101
            # Clear AIMP internal playlist so it only contains the currently playing track
            # This prevents AIMP from autodispatching random songs on track completion
            self._user32.SendMessageW(hwnd_winamp, WM_USER, 0, IPC_DELETE)

            WM_COPYDATA = 0x004A
            self._user32.SendMessageW(
                hwnd_winamp,
                WM_COPYDATA,
                0,
                ctypes.addressof(cds),
            )
            time.sleep(0.1)

            # Keep AIMP internal shuffle/repeat disabled
            self.disable_internal_shuffle_and_repeat()

            # Ensure playback starts
            if self.get_playback_state() != 2:
                self.play()
            return True
        except Exception:
            return False

    def is_connected(self) -> bool:
        """Returns True if AIMP window is detected and responding."""
        return self.get_window_handle() != 0

    def get_playback_state(self) -> int:
        """Returns: 0 = Stopped, 1 = Paused, 2 = Playing, -1 = Disconnected."""
        hwnd = self.get_window_handle()
        if not hwnd or not self._user32:
            return -1

        try:
            return int(
                self._user32.SendMessageW(
                    hwnd,
                    WM_AIMP_PROPERTY,
                    AIMP_RA_PROPERTY_PLAYER_STATE | AIMP_RA_PROPVALUE_GET,
                    0,
                )
            )
        except Exception:
            self._cached_hwnd = 0
            return -1

    def is_playing(self) -> bool:
        """Returns True if AIMP is actively playing audio."""
        return self.get_playback_state() == 2

    def is_paused(self) -> bool:
        """Returns True if AIMP is paused."""
        return self.get_playback_state() == 1

    def get_position(self) -> float:
        """Returns current playback position in seconds (float)."""
        hwnd = self.get_window_handle()
        if not hwnd or not self._user32:
            return 0.0

        try:
            ms = self._user32.SendMessageW(
                hwnd,
                WM_AIMP_PROPERTY,
                AIMP_RA_PROPERTY_PLAYER_POSITION | AIMP_RA_PROPVALUE_GET,
                0,
            )
            return max(0.0, float(ms) / 1000.0)
        except Exception:
            return 0.0

    def get_duration(self) -> float:
        """Returns track duration in seconds (float)."""
        hwnd = self.get_window_handle()
        if not hwnd or not self._user32:
            return 0.0

        try:
            ms = self._user32.SendMessageW(
                hwnd,
                WM_AIMP_PROPERTY,
                AIMP_RA_PROPERTY_PLAYER_DURATION | AIMP_RA_PROPVALUE_GET,
                0,
            )
            return max(0.0, float(ms) / 1000.0)
        except Exception:
            return 0.0

    def seek(self, position_seconds: float) -> bool:
        """Seeks to the given position in seconds in AIMP."""
        hwnd = self.get_window_handle()
        if not hwnd or not self._user32:
            return False

        try:
            ms = int(max(0.0, position_seconds) * 1000.0)
            self._user32.SendMessageW(
                hwnd,
                WM_AIMP_PROPERTY,
                AIMP_RA_PROPERTY_PLAYER_POSITION | AIMP_RA_PROPVALUE_SET,
                ms,
            )
            return True
        except Exception:
            return False

    def get_volume(self) -> int:
        """Returns AIMP volume as a percentage 0 - 100."""
        hwnd = self.get_window_handle()
        if not hwnd or not self._user32:
            return 100

        try:
            vol = self._user32.SendMessageW(
                hwnd,
                WM_AIMP_PROPERTY,
                AIMP_RA_PROPERTY_VOLUME | AIMP_RA_PROPVALUE_GET,
                0,
            )
            return max(0, min(100, int(vol)))
        except Exception:
            return 100

    def set_volume(self, volume_percent: int) -> bool:
        """Sets AIMP volume to a percentage 0 - 100."""
        hwnd = self.get_window_handle()
        if not hwnd or not self._user32:
            return False

        try:
            clamped = max(0, min(100, int(volume_percent)))
            self._user32.SendMessageW(
                hwnd,
                WM_AIMP_PROPERTY,
                AIMP_RA_PROPERTY_VOLUME | AIMP_RA_PROPVALUE_SET,
                clamped,
            )
            return True
        except Exception:
            return False

    def play(self) -> bool:
        """Sends Play command to AIMP."""
        hwnd = self.get_window_handle()
        if not hwnd or not self._user32:
            return False
        try:
            self._user32.SendMessageW(hwnd, WM_AIMP_COMMAND, AIMP_RA_CMD_PLAY, 0)
            return True
        except Exception:
            return False

    def toggle_play_pause(self) -> bool:
        """Toggles Play / Pause state in AIMP."""
        hwnd = self.get_window_handle()
        if not hwnd or not self._user32:
            return False
        try:
            self._user32.SendMessageW(hwnd, WM_AIMP_COMMAND, AIMP_RA_CMD_PLAYPAUSE, 0)
            return True
        except Exception:
            return False

    def pause(self) -> bool:
        """Pauses playback in AIMP."""
        hwnd = self.get_window_handle()
        if not hwnd or not self._user32:
            return False
        try:
            self._user32.SendMessageW(hwnd, WM_AIMP_COMMAND, AIMP_RA_CMD_PAUSE, 0)
            return True
        except Exception:
            return False

    def stop(self) -> bool:
        """Stops playback in AIMP."""
        hwnd = self.get_window_handle()
        if not hwnd or not self._user32:
            return False
        try:
            self._user32.SendMessageW(hwnd, WM_AIMP_COMMAND, AIMP_RA_CMD_STOP, 0)
            return True
        except Exception:
            return False

    def get_info(self) -> Dict[str, Any]:
        """Returns comprehensive IPC telemetry dictionary."""
        connected = self.is_connected()
        state_id = self.get_playback_state()
        state_names = {-1: "disconnected", 0: "stopped", 1: "paused", 2: "playing"}
        return {
            "connected": connected,
            "hwnd": self._cached_hwnd,
            "state_id": state_id,
            "state": state_names.get(state_id, "unknown"),
            "position": self.get_position() if connected else 0.0,
            "duration": self.get_duration() if connected else 0.0,
            "volume": self.get_volume() if connected else 100,
        }

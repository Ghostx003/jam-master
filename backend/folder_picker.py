"""Native Windows folder-picker dialog integration.
Spawns a detached process with top-most native folder dialog.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Optional


def open_windows_folder_dialog(title: str = "Select Music Folder") -> Optional[str]:
    """Opens a native Windows folder picker dialog and returns the selected path, or None if cancelled."""
    cmd = [
        sys.executable,
        "-c",
        (
            "import tkinter as tk, tkinter.filedialog as fd; "
            "r = tk.Tk(); "
            "r.withdraw(); "
            "r.wm_attributes('-topmost', 1); "
            f"chosen = fd.askdirectory(title={title!r}); "
            "print(chosen or ''); "
            "r.destroy()"
        ),
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        output = res.stdout.strip()
        if output:
            p = Path(output)
            if p.exists() and p.is_dir():
                return str(p.resolve())
        return None
    except Exception:
        # Fallback to PowerShell FolderBrowserDialog
        ps_cmd = [
            "powershell",
            "-NoProfile",
            "-Command",
            (
                "Add-Type -AssemblyName System.Windows.Forms; "
                "$f = New-Object System.Windows.Forms.FolderBrowserDialog; "
                f"$f.Description = '{title}'; "
                "$f.ShowNewFolderButton = $true; "
                "if ($f.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { Write-Output $f.SelectedPath }"
            ),
        ]
        try:
            res = subprocess.run(ps_cmd, capture_output=True, text=True, timeout=180)
            output = res.stdout.strip()
            if output:
                p = Path(output)
                if p.exists() and p.is_dir():
                    return str(p.resolve())
        except Exception:
            pass

    return None

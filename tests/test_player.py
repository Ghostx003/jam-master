"""Tests for audio player controller and fallback mechanisms.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch
from backend.player import AudioPlayer


def test_player_status():
    player = AudioPlayer()
    status = player.get_status()
    assert status.player_type in ("AIMP", "Windows Association Fallback")
    assert isinstance(status.is_installed, bool)


def test_play_non_existent_file(tmp_path):
    player = AudioPlayer()
    non_existent = tmp_path / "does_not_exist.mp3"
    result = player.play(non_existent)
    assert result is False
    assert "not found" in player.last_error.lower()


def test_aimp_play_invocation(tmp_path):
    audio_file = tmp_path / "test.mp3"
    audio_file.write_bytes(b"dummy")

    with patch("subprocess.Popen") as mock_popen:
        player = AudioPlayer(custom_aimp_path="C:/Program Files/AIMP/AIMP.exe")
        player.aimp_path = Path("C:/Program Files/AIMP/AIMP.exe")
        player.ipc.is_connected = MagicMock(return_value=False)
        player.is_aimp_running = MagicMock(return_value=False)

        with patch.object(Path, "exists", return_value=True):
            res = player.play(audio_file)
            assert res is True
            mock_popen.assert_called_once()
            call_args = mock_popen.call_args[0][0]
            assert str(audio_file.resolve()) in call_args


def test_aimp_play_via_ipc(tmp_path):
    audio_file = tmp_path / "test.mp3"
    audio_file.write_bytes(b"dummy")

    player = AudioPlayer(custom_aimp_path="C:/Program Files/AIMP/AIMP.exe")
    player.ipc.is_connected = MagicMock(return_value=True)
    player.ipc.play_file = MagicMock(return_value=True)

    res = player.play(audio_file)
    assert res is True
    player.ipc.play_file.assert_called_once_with(str(audio_file.resolve()))


def test_aimp_pause_and_stop_fallback():
    with patch("subprocess.Popen") as mock_popen:
        player = AudioPlayer(custom_aimp_path="C:/Program Files/AIMP/AIMP.exe")
        player.aimp_path = Path("C:/Program Files/AIMP/AIMP.exe")
        # Ensure CLI fallback is tested by disabling IPC
        player.ipc.is_connected = MagicMock(return_value=False)

        with patch.object(Path, "exists", return_value=True):
            assert player.pause() is True
            assert player.stop() is True
            assert mock_popen.call_count == 2


def test_aimp_ipc_integration():
    player = AudioPlayer()
    player.ipc.is_connected = MagicMock(return_value=True)
    player.ipc.toggle_play_pause = MagicMock(return_value=True)
    player.ipc.stop = MagicMock(return_value=True)
    player.ipc.seek = MagicMock(return_value=True)
    player.ipc.get_position = MagicMock(return_value=42.5)
    player.ipc.get_duration = MagicMock(return_value=180.0)

    assert player.pause() is True
    assert player.stop() is True
    assert player.seek(42.5) is True
    assert player.get_position() == 42.5
    assert player.get_duration() == 180.0

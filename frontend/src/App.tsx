import React, { useEffect, useState } from "react";
import { Navigation, ViewTab } from "./components/Navigation";
import { PlayerBar } from "./components/PlayerBar";
import { NowPlayingView } from "./views/NowPlayingView";
import { LibraryView } from "./views/LibraryView";
import { PlaylistsView } from "./views/PlaylistsView";
import { RecentlyPlayedView } from "./views/RecentlyPlayedView";
import { ImportExportView } from "./views/ImportExportView";
import { SettingsView } from "./views/SettingsView";
import { LyricsModal } from "./components/LyricsModal";
import { AddToPlaylistModal } from "./components/AddToPlaylistModal";
import {
  addTracksToPlaylist,
  createPlaylist,
  fetchPlaybackState,
  fetchPlaylists,
  playbackNext,
  playbackPause,
  playbackPrev,
  playbackRepeat,
  playbackSeek,
  playbackShuffleMore,
  playbackVolume,
  playLibrary,
  rateTrack,
  toggleWholeDeck,
} from "./api";
import { PlaybackState, Playlist } from "./types";

const VALID_TABS: ViewTab[] = [
  "now-playing",
  "playlists",
  "history",
  "import-export",
  "library",
  "settings",
];

const getTabFromUrl = (): ViewTab => {
  const path = window.location.pathname.replace(/^\/+/, "").split("/")[0];
  if (VALID_TABS.includes(path as ViewTab)) {
    return path as ViewTab;
  }
  const hash = window.location.hash.replace(/^#\/?/, "").split("/")[0];
  if (VALID_TABS.includes(hash as ViewTab)) {
    return hash as ViewTab;
  }
  return "now-playing";
};

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<ViewTab>(getTabFromUrl);
  const [playbackState, setPlaybackState] = useState<PlaybackState | null>(null);
  const [errorToast, setErrorToast] = useState<string | null>(null);

  // Lyrics and AddToPlaylist modals
  const [isLyricsOpen, setIsLyricsOpen] = useState(false);
  const [isAddToPlaylistOpen, setIsAddToPlaylistOpen] = useState(false);
  const [availablePlaylists, setAvailablePlaylists] = useState<Playlist[]>([]);

  // Initialize theme
  useEffect(() => {
    const savedTheme = localStorage.getItem("shuffle_master_theme") || "default";
    // Remove previous theme classes
    document.documentElement.className = document.documentElement.className
      .replace(/\btheme-[^\s]+\b/g, "")
      .trim();
    if (savedTheme !== "default") {
      document.documentElement.classList.add(`theme-${savedTheme}`);
    }
  }, []);

  const navigateToTab = (tab: ViewTab) => {
    setCurrentTab(tab);
    if (window.location.pathname !== `/${tab}`) {
      window.history.pushState(null, "", `/${tab}`);
    }
  };

  useEffect(() => {
    const handlePopState = () => {
      setCurrentTab(getTabFromUrl());
    };
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  const syncPlaybackState = async () => {
    try {
      const state = await fetchPlaybackState();
      setPlaybackState(state);
    } catch {
      // Backend not yet reachable or waking up
    }
  };

  useEffect(() => {
    syncPlaybackState();
    // Poll every 1 second for synchronized real-time playback position with AIMP
    const interval = setInterval(syncPlaybackState, 1000);
    return () => clearInterval(interval);
  }, []);

  const handlePlayLibrary = async () => {
    try {
      let savedFolders: string[] | undefined;
      const stored = localStorage.getItem("shuffle_master_selected_folders");
      if (stored) {
        try {
          const parsed = JSON.parse(stored);
          if (Array.isArray(parsed) && parsed.length > 0) {
            savedFolders = parsed;
          }
        } catch {}
      }
      const state = await playLibrary(savedFolders);
      setPlaybackState(state);
    } catch (err: any) {
      setErrorToast(`Library playback error: ${err.message}`);
    }
  };

  const handleNext = async () => {
    try {
      const state = await playbackNext(false);
      setPlaybackState(state);
    } catch (err: any) {
      setErrorToast(`Next song error: ${err.message}`);
    }
  };

  const handlePrev = async () => {
    try {
      const state = await playbackPrev();
      setPlaybackState(state);
    } catch (err: any) {
      setErrorToast(`Previous song error: ${err.message}`);
    }
  };

  const handleShuffleMore = async () => {
    try {
      const state = await playbackShuffleMore();
      setPlaybackState(state);
    } catch (err: any) {
      setErrorToast(`Shuffle more error: ${err.message}`);
    }
  };

  const handlePause = async () => {
    try {
      await playbackPause();
      await syncPlaybackState();
    } catch (err: any) {
      setErrorToast(`Pause error: ${err.message}`);
    }
  };

  const handleRepeat = async (count: number) => {
    try {
      const state = await playbackRepeat(count);
      setPlaybackState(state);
    } catch (err: any) {
      setErrorToast(`Repeat error: ${err.message}`);
    }
  };

  const handleToggleWholeDeck = async () => {
    try {
      const state = await toggleWholeDeck();
      setPlaybackState(state);
    } catch (err: any) {
      setErrorToast(`Toggle whole deck error: ${err.message}`);
    }
  };

  const handleRateCurrentTrack = async (rating: number) => {
    if (!playbackState?.current_track) return;
    try {
      await rateTrack(playbackState.current_track.id, rating);
      setPlaybackState((prev) =>
        prev && prev.current_track
          ? {
              ...prev,
              current_track: {
                ...prev.current_track,
                rating,
              },
            }
          : prev
      );
    } catch (err: any) {
      setErrorToast(`Rating error: ${err.message}`);
    }
  };

  const handleSeek = async (position: number) => {
    try {
      setPlaybackState((prev) =>
        prev ? { ...prev, position_seconds: position } : prev
      );
      await playbackSeek(position);
    } catch (err: any) {
      setErrorToast(`Seek error: ${err.message}`);
    }
  };

  const handleVolumeChange = async (volume: number) => {
    try {
      setPlaybackState((prev) =>
        prev ? { ...prev, volume } : prev
      );
      await playbackVolume(volume);
    } catch (err: any) {
      setErrorToast(`Volume error: ${err.message}`);
    }
  };

  // Global Keyboard Shortcuts
  // Space: Pause/Resume, ArrowRight: Next Song, ArrowLeft: Previous Song, ArrowUp: Shuffle & Change
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      if (
        target &&
        (target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.tagName === "SELECT" ||
          target.isContentEditable ||
          target.closest("input, textarea, select, [contenteditable='true']"))
      ) {
        return;
      }

      if (e.code === "Space" || e.key === " ") {
        e.preventDefault();
        handlePause();
        return;
      }

      if (e.key === "ArrowRight") {
        e.preventDefault();
        handleNext();
        return;
      }

      if (e.key === "ArrowLeft") {
        e.preventDefault();
        handlePrev();
        return;
      }

      if (e.key === "ArrowUp") {
        e.preventDefault();
        handleShuffleMore();
        return;
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [playbackState?.is_playing]);

  // Auto-switch track detection guarantee in frontend polling
  const autoSwitchCooldownRef = React.useRef<number>(0);
  useEffect(() => {
    if (!playbackState?.current_track) return;
    const pos = playbackState.position_seconds || 0;
    const dur = playbackState.duration_seconds || (playbackState.current_track.duration || 0);
    const isStopped = playbackState.player?.state === "stopped";

    if (dur > 5.0 && (pos >= dur - 1.2 || (isStopped && pos === 0))) {
      const now = Date.now();
      if (now - autoSwitchCooldownRef.current > 3500) {
        autoSwitchCooldownRef.current = now;
        handleNext();
      }
    }
  }, [playbackState?.position_seconds, playbackState?.duration_seconds, playbackState?.is_playing, playbackState?.player?.state]);

  const handleOpenLyrics = () => {
    if (!playbackState?.current_track) {
      setErrorToast("No track currently playing to fetch lyrics for.");
      return;
    }
    setIsLyricsOpen(true);
  };

  const handleOpenAddToPlaylist = async () => {
    const track = playbackState?.current_track;
    if (!track) {
      setErrorToast("No song is currently playing.");
      return;
    }
    try {
      const pls = await fetchPlaylists();
      if (pls.length === 0) {
        const created = await createPlaylist("My Playlist");
        await addTracksToPlaylist(created.id, [track.id]);
        setErrorToast(`Created 'My Playlist' and added "${track.display_title}"!`);
        return;
      }
      if (pls.length === 1) {
        await addTracksToPlaylist(pls[0].id, [track.id]);
        setErrorToast(`Added "${track.display_title}" to playlist "${pls[0].name}"!`);
      } else {
        setAvailablePlaylists(pls);
        setIsAddToPlaylistOpen(true);
      }
    } catch (err: any) {
      const msg = err.message || "";
      setErrorToast(
        msg.toLowerCase().includes("already exists")
          ? "Song already exists in playlist."
          : `Failed to add track: ${msg}`
      );
    }
  };

  const handleConfirmAddToPlaylist = async (playlistId: number) => {
    const track = playbackState?.current_track;
    if (!track) return;
    try {
      await addTracksToPlaylist(playlistId, [track.id]);
      const targetPl = availablePlaylists.find((p) => p.id === playlistId);
      setErrorToast(`Added "${track.display_title}" to "${targetPl?.name || "playlist"}"!`);
    } catch (err: any) {
      const msg = err.message || "";
      setErrorToast(
        msg.toLowerCase().includes("already exists")
          ? "Song already exists in playlist."
          : `Failed to add track: ${msg}`
      );
    }
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#090d16] text-slate-100 font-sans selection:bg-indigo-600 selection:text-white">
      {/* Sidebar Navigation */}
      <Navigation
        currentTab={currentTab}
        onTabChange={navigateToTab}
        playerStatus={playbackState?.player}
      />

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col h-screen overflow-y-auto min-w-0">
        {/* Error / Notification Toast */}
        {errorToast && (
          <div className="sticky top-4 z-50 mx-auto max-w-md p-3.5 bg-indigo-600/95 text-white text-xs font-semibold rounded-2xl shadow-2xl flex items-center justify-between backdrop-blur-md">
            <span>{errorToast}</span>
            <button onClick={() => setErrorToast(null)} className="ml-3 p-1 hover:text-slate-200">
              ✕
            </button>
          </div>
        )}

        {/* View Router */}
        <div className="flex-1 pb-10">
          {currentTab === "now-playing" && (
            <NowPlayingView
              state={playbackState}
              onPlayLibrary={handlePlayLibrary}
              onNavigateToPlaylists={() => navigateToTab("playlists")}
              onToggleWholeDeck={handleToggleWholeDeck}
              onRateCurrentTrack={handleRateCurrentTrack}
              onOpenLyrics={handleOpenLyrics}
              onStateUpdate={syncPlaybackState}
            />
          )}

          {currentTab === "library" && (
            <LibraryView onStateUpdate={syncPlaybackState} />
          )}

          {currentTab === "playlists" && (
            <PlaylistsView
              onStateUpdate={syncPlaybackState}
              playbackState={playbackState}
              onPause={handlePause}
              onNext={handleNext}
              onPrev={handlePrev}
              onRepeat={handleRepeat}
              onVolumeChange={handleVolumeChange}
              onRateCurrentTrack={handleRateCurrentTrack}
            />
          )}

          {currentTab === "history" && (
            <RecentlyPlayedView onStateUpdate={syncPlaybackState} />
          )}

          {currentTab === "import-export" && <ImportExportView />}

          {currentTab === "settings" && <SettingsView />}
        </div>

        {/* Persistent Bottom Player Bar (Matches Screenshot 1) */}
        <PlayerBar
          state={playbackState}
          onNext={handleNext}
          onPrev={handlePrev}
          onShuffleMore={handleShuffleMore}
          onPause={handlePause}
          onRepeat={handleRepeat}
          onOpenNowPlaying={() => {
            if (playbackState?.active_playlist_id != null) {
              navigateToTab("playlists");
            } else {
              navigateToTab("now-playing");
            }
          }}
          onSeek={handleSeek}
          onVolumeChange={handleVolumeChange}
          onAddToPlaylist={handleOpenAddToPlaylist}
          onOpenLyrics={handleOpenLyrics}
          onToggleUpNext={() => navigateToTab("now-playing")}
        />
      </main>

      {/* Lyrics Modal with Indic Romanization */}
      <LyricsModal
        isOpen={isLyricsOpen}
        onClose={() => setIsLyricsOpen(false)}
        title={playbackState?.current_track?.display_title || ""}
        artist={playbackState?.current_track?.display_artist || ""}
      />

      {/* Add To Playlist Modal */}
      <AddToPlaylistModal
        isOpen={isAddToPlaylistOpen}
        trackTitle={playbackState?.current_track?.display_title || ""}
        playlists={availablePlaylists}
        onClose={() => setIsAddToPlaylistOpen(false)}
        onSelectPlaylist={handleConfirmAddToPlaylist}
      />
    </div>
  );
};

export default App;

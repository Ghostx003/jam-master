import React, { useEffect, useState } from "react";
import {
  ArrowDown,
  ArrowUp,
  Clock,
  Download,
  ListMusic,
  Music,
  Pause,
  Play,
  Plus,
  RefreshCw,
  Repeat,
  Search,
  Shuffle,
  SkipBack,
  SkipForward,
  Sparkles,
  Trash2,
  Volume2,
  X,
} from "lucide-react";
import {
  addTracksToPlaylist,
  createPlaylist,
  deletePlaylist,
  exportPlaylists,
  fetchPlaylistDetails,
  fetchPlaylists,
  fetchTracks,
  generateRandomPlaylist,
  playPlaylist,
  playTrack,
  rateTrack,
  refillPlaylist,
  removePlaylistEntry,
  renamePlaylist,
  reorderPlaylist,
} from "../api";
import { PlaybackState, Playlist, PlaylistDetails, Track } from "../types";
import { ArtworkImage } from "../components/ArtworkImage";
import { StarRating } from "../components/StarRating";
import { RepeatModal } from "../components/RepeatModal";
import { VolumeSlider } from "../components/VolumeSlider";

interface Props {
  onStateUpdate: () => void;
  playbackState?: PlaybackState | null;
  onPause?: () => void;
  onNext?: () => void;
  onPrev?: () => void;
  onRepeat?: (count: number) => void;
  onVolumeChange?: (v: number) => void;
  onRateCurrentTrack?: (rating: number) => void;
}

export const PlaylistsView: React.FC<Props> = ({
  onStateUpdate,
  playbackState,
  onPause,
  onNext,
  onPrev,
  onRepeat,
  onVolumeChange,
  onRateCurrentTrack,
}) => {
  const [playlists, setPlaylists] = useState<Playlist[]>([]);
  const [selectedPlaylistId, setSelectedPlaylistId] = useState<number | null>(null);
  const [playlistDetails, setPlaylistDetails] = useState<PlaylistDetails | null>(null);

  // Modals & form state
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [newPlName, setNewPlName] = useState("");
  const [newPlDesc, setNewPlDesc] = useState("");

  const [isAddSongsOpen, setIsAddSongsOpen] = useState(false);
  const [libraryTracks, setLibraryTracks] = useState<Track[]>([]);
  const [searchTrackQuery, setSearchTrackQuery] = useState("");
  const [selectedTrackIdsToAdd, setSelectedTrackIdsToAdd] = useState<Set<number>>(new Set());

  // Random Playlist & Refill state
  const [isRandomOpen, setIsRandomOpen] = useState(false);
  const [randomName, setRandomName] = useState("Random Mix");
  const [randomLimit, setRandomLimit] = useState(50);
  const [isRefilling, setIsRefilling] = useState(false);
  const [isRepeatModalOpen, setIsRepeatModalOpen] = useState(false);

  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const getSelectedFolderPaths = (): string[] => {
    try {
      const raw = localStorage.getItem("shuffle_master_selected_folders");
      if (raw) return JSON.parse(raw);
    } catch {}
    return [];
  };

  const loadPlaylists = async () => {
    try {
      const list = await fetchPlaylists();
      setPlaylists(list);
      if (!selectedPlaylistId && list.length > 0) {
        setSelectedPlaylistId(list[0].id);
      }
    } catch (err: any) {
      setStatusMessage(`Error loading playlists: ${err.message}`);
    }
  };

  const loadDetails = async (id: number) => {
    try {
      const details = await fetchPlaylistDetails(id);
      setPlaylistDetails(details);
    } catch (err: any) {
      setStatusMessage(`Error loading playlist details: ${err.message}`);
    }
  };

  useEffect(() => {
    loadPlaylists();
  }, []);

  useEffect(() => {
    if (selectedPlaylistId) {
      loadDetails(selectedPlaylistId);
    } else {
      setPlaylistDetails(null);
    }
  }, [selectedPlaylistId]);

  // Handle Create Playlist
  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPlName.trim()) return;
    try {
      const created = await createPlaylist(newPlName.trim(), newPlDesc.trim());
      setNewPlName("");
      setNewPlDesc("");
      setIsCreateOpen(false);
      await loadPlaylists();
      setSelectedPlaylistId(created.id);
      setStatusMessage(`Created playlist '${created.name}'.`);
    } catch (err: any) {
      setStatusMessage(`Error: ${err.message}`);
    }
  };

  // Handle Generate Random Playlist
  const handleGenerateRandom = async (e: React.FormEvent) => {
    e.preventDefault();
    const limit = Math.max(1, Math.min(randomLimit, 500));
    const folders = getSelectedFolderPaths();
    try {
      const created = await generateRandomPlaylist(randomName.trim() || "Random Mix", limit, folders);
      setIsRandomOpen(false);
      await loadPlaylists();
      setSelectedPlaylistId(created.id);
      setPlaylistDetails(created);
      setStatusMessage(
        `Generated random playlist '${created.name}' with ${created.entries.length} track(s) (target limit: ${limit}).`
      );
    } catch (err: any) {
      setStatusMessage(`Error generating random playlist: ${err.message}`);
    }
  };

  // Handle Refill Random Playlist
  const handleRefill = async () => {
    if (!selectedPlaylistId || !playlistDetails) return;
    setIsRefilling(true);
    try {
      const folders = getSelectedFolderPaths();
      const res = await refillPlaylist(selectedPlaylistId, folders);
      setPlaylistDetails(res.details);
      await loadPlaylists();
      setStatusMessage(res.message);
    } catch (err: any) {
      setStatusMessage(`Refill error: ${err.message}`);
    } finally {
      setIsRefilling(false);
    }
  };

  // Handle Rate Track inside Playlist
  const handleRateTrack = async (trackId: number, rating: number) => {
    // 1. Optimistically update local playlist details immediately so star stays
    setPlaylistDetails((prev) =>
      prev
        ? {
            ...prev,
            entries: prev.entries.map((entry) => {
              if (entry.track?.id === trackId) {
                return {
                  ...entry,
                  track: {
                    ...entry.track,
                    rating,
                  },
                };
              }
              return entry;
            }),
          }
        : prev
    );

    // 2. Also notify parent App state immediately
    if (onRateCurrentTrack && playbackState?.current_track?.id === trackId) {
      onRateCurrentTrack(rating);
    }

    // 3. Persist to backend and SQLite database
    try {
      await rateTrack(trackId, rating);
    } catch (err: any) {
      setStatusMessage(`Rating error: ${err.message}`);
    }
  };

  // Handle Delete Playlist
  const handleDelete = async (id: number, name: string) => {
    if (!window.confirm(`Are you sure you want to delete playlist "${name}"? Tracks in your library will not be deleted.`)) {
      return;
    }
    try {
      await deletePlaylist(id);
      setStatusMessage(`Deleted playlist '${name}'.`);
      setSelectedPlaylistId(null);
      await loadPlaylists();
    } catch (err: any) {
      setStatusMessage(`Error deleting playlist: ${err.message}`);
    }
  };

  // Handle Play Playlist
  const handlePlay = async (id: number) => {
    try {
      await playPlaylist(id);
      onStateUpdate();
      setStatusMessage("Playlist playback started in AIMP.");
    } catch (err: any) {
      setStatusMessage(`Playback error: ${err.message}`);
    }
  };

  // Handle Play Specific Track in Playlist
  const handlePlaySingleTrack = async (trackId: number) => {
    try {
      await playTrack(trackId);
      onStateUpdate();
    } catch (err: any) {
      setStatusMessage(`Error playing track: ${err.message}`);
    }
  };

  // Handle Remove Entry
  const handleRemoveEntry = async (entryId: number) => {
    if (!selectedPlaylistId) return;
    try {
      await removePlaylistEntry(selectedPlaylistId, entryId);
      await loadDetails(selectedPlaylistId);
      await loadPlaylists();
    } catch (err: any) {
      setStatusMessage(`Error removing track: ${err.message}`);
    }
  };

  // Handle Reorder: Move Up / Down
  const handleMove = async (index: number, direction: "up" | "down") => {
    if (!playlistDetails || !selectedPlaylistId) return;
    const entries = [...playlistDetails.entries];
    const targetIndex = direction === "up" ? index - 1 : index + 1;

    if (targetIndex < 0 || targetIndex >= entries.length) return;

    const temp = entries[index];
    entries[index] = entries[targetIndex];
    entries[targetIndex] = temp;

    const orderedIds = entries.map((e) => e.id);
    try {
      await reorderPlaylist(selectedPlaylistId, orderedIds);
      await loadDetails(selectedPlaylistId);
    } catch (err: any) {
      setStatusMessage(`Reorder error: ${err.message}`);
    }
  };

  // Export Single Playlist
  const handleExportSingle = async (playlistId: number, name: string) => {
    try {
      const blob = await exportPlaylists([playlistId]);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${name.replace(/\s+/g, "_")}.zip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      setStatusMessage(`Export failed: ${err.message}`);
    }
  };

  // Open Add Songs Modal
  const openAddSongs = async () => {
    setIsAddSongsOpen(true);
    setSelectedTrackIdsToAdd(new Set());
    try {
      const tracks = await fetchTracks({ limit: 150 });
      setLibraryTracks(tracks);
    } catch {}
  };

  // Add Songs Submit with duplicate detection
  const handleAddSongsSubmit = async () => {
    if (!selectedPlaylistId) return;
    const ids = Array.from(selectedTrackIdsToAdd);
    if (ids.length === 0) {
      setIsAddSongsOpen(false);
      return;
    }
    try {
      const res = await addTracksToPlaylist(selectedPlaylistId, ids);
      setIsAddSongsOpen(false);
      await loadDetails(selectedPlaylistId);
      await loadPlaylists();
      setStatusMessage(`Added ${res.added_count} track(s) to playlist.`);
    } catch (err: any) {
      if (err.message && err.message.toLowerCase().includes("already exists")) {
        setStatusMessage("Song already exists in playlist.");
      } else {
        setStatusMessage(`Error adding tracks: ${err.message}`);
      }
    }
  };

  const filteredLibraryTracks = libraryTracks.filter((t) => {
    if (!searchTrackQuery.trim()) return true;
    const q = searchTrackQuery.toLowerCase();
    return (
      t.display_title.toLowerCase().includes(q) ||
      t.display_artist.toLowerCase().includes(q) ||
      (t.album && t.album.toLowerCase().includes(q))
    );
  });

  // Check if currently playing audio is this playlist
  const isThisPlaylistPlaying = Boolean(
    playbackState?.active_playlist_id &&
    playbackState.active_playlist_id === selectedPlaylistId
  );
  const activeTrack = isThisPlaylistPlaying
    ? (playlistDetails?.entries.find((e) => e.track?.id === playbackState?.current_track?.id)?.track || playbackState?.current_track)
    : (playlistDetails?.entries?.[0]?.track || null);
  const isPlaying = Boolean(isThisPlaylistPlaying && playbackState?.is_playing);
  const isRepeating = Boolean(playbackState?.repeats_remaining && playbackState.repeats_remaining > 0);
  const volume = playbackState?.volume ?? 100;
  const aimpConnected = Boolean(playbackState?.aimp_connected);

  return (
    <div className="flex-1 px-4 py-6 md:px-8 w-full space-y-6 animate-in fade-in duration-200">
      {/* Top Header (Clean: Curation & Organization removed) */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-white/5">
        <div>
          <span className="text-xs uppercase tracking-widest font-bold text-indigo-400">
            Playlists
          </span>
          <h2 className="text-2xl font-bold text-white flex items-center gap-2 mt-0.5">
            Your Playlists
          </h2>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              setRandomName(`Random Mix ${playlists.length + 1}`);
              setIsRandomOpen(true);
            }}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-semibold text-xs shadow-lg shadow-purple-600/30 active:scale-95 transition-all"
          >
            <Sparkles className="w-4 h-4" />
            Random Playlist
          </button>
          <button
            onClick={() => setIsCreateOpen(true)}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs shadow-lg shadow-indigo-600/30 active:scale-95 transition-all"
          >
            <Plus className="w-4 h-4" />
            New Playlist
          </button>
        </div>
      </div>

      {statusMessage && (
        <div className="p-3.5 rounded-xl bg-slate-800/90 border border-indigo-500/30 text-xs text-indigo-300 flex items-center justify-between shadow-lg">
          <span>{statusMessage}</span>
          <button onClick={() => setStatusMessage(null)} className="text-slate-400 hover:text-white">
            ✕
          </button>
        </div>
      )}

      {/* Top Horizontal Playlist Selector Cards (All in 1 place without horizontal scrolling on tracks) */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
            Select Playlist ({playlists.length})
          </span>
        </div>

        {playlists.length === 0 ? (
          <div className="bg-[#111827] border border-white/5 rounded-2xl p-8 text-center text-slate-400 text-xs">
            No playlists created yet. Click "New Playlist" or "Random Playlist" above to start!
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3">
            {playlists.map((p) => {
              const isSelected = selectedPlaylistId === p.id;
              const isPlayingThis = Boolean(
                playbackState?.active_playlist_id && playbackState.active_playlist_id === p.id
              );
              return (
                <button
                  key={p.id}
                  onClick={() => setSelectedPlaylistId(p.id)}
                  className={`w-full p-3.5 rounded-2xl border text-left transition-all active:scale-[0.98] ${
                    isSelected
                      ? "bg-gradient-to-r from-indigo-900/60 to-purple-900/40 border-indigo-500/80 shadow-lg shadow-indigo-600/25 ring-1 ring-indigo-500/50"
                      : "bg-[#111827] border-white/5 hover:border-white/15 text-slate-300 hover:bg-slate-800/40"
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <p className={`font-bold text-sm truncate ${isSelected ? "text-white" : "text-slate-200"}`}>
                      {p.name}
                    </p>
                    {isPlayingThis && (
                      <span className="flex items-center gap-1 text-[9px] px-1.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 font-bold border border-emerald-500/30 shrink-0">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                        PLAYING
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2 mt-1.5 text-[11px] text-slate-400">
                    <span className="flex items-center gap-1">
                      <ListMusic className="w-3.5 h-3.5 text-indigo-400" />
                      {p.track_count} tracks
                    </span>
                    {p.target_capacity && (
                      <span className="text-purple-400/90 font-medium">· Limit: {p.target_capacity}</span>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Full Width Main Container: Replicated Player + Full-Width Tracks Table */}
      {playlistDetails && (
        <div className="bg-[#111827] border border-white/5 rounded-3xl p-6 space-y-6 shadow-2xl">
          {/* Header Row: Title & Action Buttons */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-white/5">
            <div>
              <div className="flex items-center gap-2.5">
                <h3 className="text-2xl font-bold text-white">
                  {playlistDetails.name}
                </h3>
                {Boolean(playlistDetails.target_capacity) && (
                  <span className="text-[10px] px-2.5 py-0.5 rounded-full bg-purple-500/20 text-purple-300 font-semibold border border-purple-500/30">
                    Target Limit: {playlistDetails.target_capacity} tracks
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 mt-1">
                {playlistDetails.track_count} tracks · {playlistDetails.description || "Custom playlist"}
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2.5">
              {Boolean(
                playlistDetails.target_capacity &&
                playlistDetails.entries.length < playlistDetails.target_capacity
              ) && (
                <button
                  onClick={handleRefill}
                  disabled={isRefilling}
                  className="flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 disabled:opacity-50 text-white rounded-xl text-xs font-bold shadow-md shadow-purple-600/30 active:scale-95 transition-all"
                  title={`Refill back to original limit of ${playlistDetails.target_capacity} songs`}
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${isRefilling ? "animate-spin" : ""}`} />
                  Add More Songs (Refill to {playlistDetails.target_capacity})
                </button>
              )}

              <button
                onClick={() => handlePlay(playlistDetails.id)}
                className="flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-indigo-600 to-cyan-600 hover:from-indigo-500 hover:to-cyan-500 text-white rounded-xl text-xs font-bold shadow-lg shadow-indigo-600/30 active:scale-95 transition-all"
              >
                <Shuffle className="w-3.5 h-3.5" />
                Shuffle & Play Playlist
              </button>

              <button
                onClick={openAddSongs}
                className="flex items-center gap-2 px-3.5 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-medium border border-white/5 active:scale-95 transition-all"
              >
                <Plus className="w-3.5 h-3.5" />
                Add Songs
              </button>

              <button
                onClick={() => handleExportSingle(playlistDetails.id, playlistDetails.name)}
                title="Export playlist to ZIP archive"
                className="p-2.5 bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white rounded-xl border border-white/5 transition-colors"
              >
                <Download className="w-4 h-4" />
              </button>

              <button
                onClick={() => handleDelete(playlistDetails.id, playlistDetails.name)}
                title="Delete playlist"
                className="flex items-center gap-1.5 px-3 py-2.5 bg-slate-800 hover:bg-rose-500/20 text-slate-400 hover:text-rose-400 rounded-xl border border-white/5 transition-colors text-xs font-medium"
              >
                <Trash2 className="w-3.5 h-3.5" />
                Delete
              </button>
            </div>
          </div>

          {/* Replicated Dedicated Player for this Playlist */}
          {activeTrack && (
            <div className="bg-slate-900/80 border border-white/10 rounded-2xl p-5 shadow-xl">
              <div className="flex flex-col md:flex-row items-center gap-6">
                {/* Artwork */}
                <div className="relative group shrink-0">
                  <ArtworkImage
                    trackId={activeTrack.id}
                    className="w-28 h-28 md:w-32 md:h-32 rounded-2xl shadow-xl border border-white/10"
                    iconClassName="w-12 h-12 text-indigo-400"
                  />
                </div>

                {/* Metadata & Controls */}
                <div className="flex-1 min-w-0 space-y-3 w-full">
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-2">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                          {isThisPlaylistPlaying ? "Now Playing (Playlist)" : "Featured Playlist Track"}
                        </span>
                        {isThisPlaylistPlaying && (
                          <span className="flex items-center gap-1 text-[10px] text-emerald-400 font-semibold">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                            Live in AIMP
                          </span>
                        )}
                      </div>
                      <h4 className="text-lg md:text-xl font-bold text-white truncate mt-1">
                        {activeTrack.display_title}
                      </h4>
                      <p className="text-xs text-slate-300 truncate">
                        {activeTrack.display_artist || "Unknown Artist"} {activeTrack.album ? `· ${activeTrack.album}` : ""}
                      </p>
                    </div>

                    {/* Rating */}
                    <div className="flex items-center gap-2 shrink-0">
                      <span className="text-xs text-slate-400">Rating:</span>
                      <StarRating
                        rating={activeTrack.rating || 0}
                        size="sm"
                        onRate={(r) => handleRateTrack(activeTrack.id, r)}
                      />
                    </div>
                  </div>

                  {/* Aesthetic Playback Buttons */}
                  <div className="flex flex-wrap items-center gap-3 pt-1">
                    <button
                      onClick={onPrev}
                      title="Previous Song"
                      className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-semibold text-xs border border-white/10 active:scale-95 transition-all shadow-md"
                    >
                      <SkipBack className="w-4 h-4" />
                      Prev
                    </button>

                    <button
                      onClick={() => {
                        if (isThisPlaylistPlaying && onPause) {
                          onPause();
                        } else {
                          handlePlay(playlistDetails.id);
                        }
                      }}
                      className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-cyan-500 hover:from-indigo-500 hover:to-cyan-400 text-white font-bold text-xs shadow-lg shadow-indigo-600/30 active:scale-95 transition-all"
                    >
                      {isPlaying ? (
                        <Pause className="w-4 h-4 fill-current" />
                      ) : (
                        <Play className="w-4 h-4 fill-current" />
                      )}
                      {isPlaying ? "Pause in AIMP" : "Play Playlist"}
                    </button>

                    <button
                      onClick={onNext}
                      title="Next Song"
                      className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-semibold text-xs border border-white/10 active:scale-95 transition-all shadow-md"
                    >
                      <SkipForward className="w-4 h-4" />
                      Next
                    </button>

                    <button
                      onClick={() => setIsRepeatModalOpen(true)}
                      className={`flex items-center gap-2 px-3.5 py-2.5 rounded-xl text-xs font-semibold border active:scale-95 transition-all ${
                        isRepeating
                          ? "bg-indigo-600/20 border-indigo-500/40 text-indigo-300"
                          : "bg-slate-800 hover:bg-slate-700 text-slate-300 border-white/5"
                      }`}
                    >
                      <Repeat className="w-3.5 h-3.5" />
                      Repeat {isRepeating && `(${playbackState?.repeats_remaining})`}
                    </button>

                    {/* AIMP Volume Control */}
                    {onVolumeChange && (
                      <div className="flex items-center gap-2 ml-auto">
                        <span className="text-[11px] font-semibold text-slate-400">Volume:</span>
                        <VolumeSlider
                          volume={volume}
                          onVolumeChange={onVolumeChange}
                          disabled={!aimpConnected}
                        />
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Full-Width Tracks Table */}
          {playlistDetails.entries.length === 0 ? (
            <div className="p-12 text-center text-slate-500 text-xs bg-slate-900/40 rounded-2xl border border-white/5">
              This playlist is empty. Click "Add Songs" above to add tracks from your library.
            </div>
          ) : (
            <div className="border border-white/5 rounded-2xl overflow-hidden bg-slate-900/40">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-900/90 text-slate-400 text-xs border-b border-white/5">
                  <tr>
                    <th className="py-3 px-3 w-10 text-center">#</th>
                    <th className="py-3 px-3 w-24 text-center whitespace-nowrap">Play / ✕ Remove</th>
                    <th className="py-3 px-4 font-semibold">Title & Track</th>
                    <th className="py-3 px-4 font-semibold w-40 truncate">Artist</th>
                    <th className="py-3 px-4 font-semibold text-center w-28 whitespace-nowrap">Rating</th>
                    <th className="py-3 px-4 font-semibold text-right w-20 whitespace-nowrap">Duration</th>
                    <th className="py-3 px-3 font-semibold text-center w-20 whitespace-nowrap">Order</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5 text-slate-300">
                  {playlistDetails.entries.map((entry, idx) => {
                    const t = entry.track;
                    if (!t) return null;
                    const isRowPlaying = Boolean(
                      isThisPlaylistPlaying && playbackState?.current_track?.id === t.id
                    );
                    return (
                      <tr
                        key={entry.id}
                        className={`transition-colors group ${
                          isRowPlaying
                            ? "bg-indigo-600/15 text-white"
                            : "hover:bg-white/[0.03]"
                        }`}
                      >
                        <td className="py-2.5 px-3 text-slate-500 text-xs text-center font-mono">
                          {entry.position}
                        </td>
                        <td className="py-2.5 px-3 text-center whitespace-nowrap">
                          <div className="inline-flex items-center gap-2">
                            {/* Play Button */}
                            <button
                              type="button"
                              onClick={() => handlePlaySingleTrack(t.id)}
                              className={`p-2 rounded-xl transition-all shadow-sm ${
                                isRowPlaying
                                  ? "bg-indigo-600 text-white shadow-indigo-600/30 scale-105"
                                  : "bg-slate-800 text-slate-300 hover:text-white hover:bg-indigo-600"
                              }`}
                              title="Play this track in AIMP"
                            >
                              <Play className="w-3.5 h-3.5 fill-current" />
                            </button>
                            {/* Big Unmissable Red Cross (✕) Delete Button */}
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleRemoveEntry(entry.id);
                              }}
                              title="Remove this song from playlist (✕)"
                              className="p-2 rounded-xl bg-rose-500/25 text-rose-300 hover:bg-rose-600 hover:text-white transition-all shadow-sm border border-rose-500/40 active:scale-95"
                            >
                              <X className="w-4 h-4 stroke-[3]" />
                            </button>
                          </div>
                        </td>
                        <td className="py-2.5 px-4">
                          <div className="flex items-center gap-3">
                            <ArtworkImage
                              trackId={t.id}
                              className="w-8 h-8 rounded-lg shrink-0 border border-white/10"
                              iconClassName="w-4 h-4 text-indigo-400"
                            />
                            <div className="min-w-0">
                              <p className={`font-semibold text-sm ${isRowPlaying ? "text-indigo-300" : "text-white"}`}>
                                {t.display_title}
                              </p>
                              {t.album && (
                                <p className="text-[11px] text-slate-400 truncate">{t.album}</p>
                              )}
                            </div>
                          </div>
                        </td>
                        <td className="py-2.5 px-4 text-xs text-slate-300 truncate max-w-[160px]">
                          {t.display_artist || "--"}
                        </td>
                        <td className="py-2.5 px-4 text-center whitespace-nowrap">
                          <div className="flex justify-center" onClick={(e) => e.stopPropagation()}>
                            <StarRating
                              rating={t.rating || 0}
                              onRate={(r: number) => handleRateTrack(t.id, r)}
                              size="sm"
                            />
                          </div>
                        </td>
                        <td className="py-2.5 px-4 text-right text-xs font-mono text-slate-400 whitespace-nowrap">
                          {t.display_duration}
                        </td>
                        <td className="py-2.5 px-3 text-center whitespace-nowrap">
                          <div className="flex items-center justify-center gap-1">
                            <button
                              disabled={idx === 0}
                              onClick={() => handleMove(idx, "up")}
                              title="Move Up"
                              className="p-1 text-slate-500 hover:text-white disabled:opacity-20 rounded hover:bg-white/5"
                            >
                              <ArrowUp className="w-3.5 h-3.5" />
                            </button>
                            <button
                              disabled={idx === playlistDetails.entries.length - 1}
                              onClick={() => handleMove(idx, "down")}
                              title="Move Down"
                              className="p-1 text-slate-500 hover:text-white disabled:opacity-20 rounded hover:bg-white/5"
                            >
                              <ArrowDown className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Modal: Create Playlist */}
      {isCreateOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#111827] border border-white/10 rounded-3xl w-full max-w-md p-6 shadow-2xl relative">
            <button
              onClick={() => setIsCreateOpen(false)}
              className="absolute top-4 right-4 text-slate-400 hover:text-white p-1 rounded-lg"
            >
              <X className="w-5 h-5" />
            </button>
            <h3 className="text-lg font-bold text-white mb-4">Create New Playlist</h3>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">
                  Playlist Name *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Synthwave Night Drive"
                  value={newPlName}
                  onChange={(e) => setNewPlName(e.target.value)}
                  className="w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">
                  Description (Optional)
                </label>
                <textarea
                  rows={2}
                  placeholder="Notes about this collection..."
                  value={newPlDesc}
                  onChange={(e) => setNewPlDesc(e.target.value)}
                  className="w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-2 text-white text-sm focus:outline-none focus:border-indigo-500"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsCreateOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/30"
                >
                  Create Playlist
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Generate Random Playlist */}
      {isRandomOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#111827] border border-white/10 rounded-3xl w-full max-w-md p-6 shadow-2xl relative space-y-4">
            <button
              onClick={() => setIsRandomOpen(false)}
              className="absolute top-4 right-4 text-slate-400 hover:text-white p-1 rounded-lg"
            >
              <X className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-purple-600/20 text-purple-400 flex items-center justify-center">
                <Sparkles className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white">Generate Random Playlist</h3>
                <p className="text-xs text-slate-400">
                  Pulls a random selection of songs from your library
                </p>
              </div>
            </div>

            <form onSubmit={handleGenerateRandom} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">
                  Playlist Name
                </label>
                <input
                  type="text"
                  value={randomName}
                  onChange={(e) => setRandomName(e.target.value)}
                  className="w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none focus:border-purple-500"
                />
              </div>

              <div>
                <div className="flex justify-between items-center text-xs font-semibold mb-1">
                  <span className="text-slate-400">Number of Songs (Capacity Limit)</span>
                  <span className="text-purple-400 font-bold">{randomLimit} tracks</span>
                </div>
                <input
                  type="number"
                  min={1}
                  max={500}
                  value={randomLimit}
                  onChange={(e) => setRandomLimit(parseInt(e.target.value) || 50)}
                  className="w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none focus:border-purple-500"
                />
                <p className="text-[11px] text-slate-500 mt-1">
                  If you delete songs, clicking "Refill" will replenish back to this limit.
                </p>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsRandomOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-bold shadow-lg shadow-purple-600/30"
                >
                  Generate Playlist
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Add Songs from Library */}
      {isAddSongsOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#111827] border border-white/10 rounded-3xl w-full max-w-2xl p-6 shadow-2xl flex flex-col max-h-[85vh] space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-white/5">
              <h3 className="font-bold text-white text-base">
                Add Songs to '{playlistDetails?.name}'
              </h3>
              <button
                onClick={() => setIsAddSongsOpen(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-white/5"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Search Box */}
            <div className="relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
              <input
                type="text"
                placeholder="Search tracks by title, artist, or album..."
                value={searchTrackQuery}
                onChange={(e) => setSearchTrackQuery(e.target.value)}
                className="w-full bg-slate-900 border border-white/10 rounded-xl pl-10 pr-4 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>

            {/* Track Selection List */}
            <div className="flex-1 overflow-y-auto space-y-1 pr-1 max-h-96 divide-y divide-white/5">
              {filteredLibraryTracks.length === 0 ? (
                <p className="text-center text-xs text-slate-500 py-8">
                  No matching tracks found in library.
                </p>
              ) : (
                filteredLibraryTracks.map((t) => {
                  const isSelected = selectedTrackIdsToAdd.has(t.id);
                  return (
                    <div
                      key={t.id}
                      onClick={() => {
                        const next = new Set(selectedTrackIdsToAdd);
                        if (isSelected) {
                          next.delete(t.id);
                        } else {
                          next.add(t.id);
                        }
                        setSelectedTrackIdsToAdd(next);
                      }}
                      className={`flex items-center justify-between p-2.5 rounded-xl cursor-pointer transition-colors ${
                        isSelected ? "bg-indigo-600/20" : "hover:bg-white/[0.03]"
                      }`}
                    >
                      <div className="flex items-center gap-3 min-w-0 pr-3">
                        <ArtworkImage
                          trackId={t.id}
                          className="w-8 h-8 rounded-lg shrink-0"
                          iconClassName="w-4 h-4 text-indigo-400"
                        />
                        <div className="min-w-0">
                          <p className="text-xs font-semibold text-white truncate">
                            {t.display_title}
                          </p>
                          <p className="text-[11px] text-slate-400 truncate">
                            {t.display_artist || "Unknown Artist"}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-3 shrink-0">
                        <span className="text-xs text-slate-500 font-mono">
                          {t.display_duration}
                        </span>
                        <div
                          className={`w-4 h-4 rounded border flex items-center justify-center ${
                            isSelected
                              ? "bg-indigo-600 border-indigo-500 text-white"
                              : "border-slate-600"
                          }`}
                        >
                          {isSelected && <span className="text-[10px]">✓</span>}
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            <div className="flex items-center justify-between pt-3 border-t border-white/5">
              <span className="text-xs text-slate-400">
                {selectedTrackIdsToAdd.size} track(s) selected
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setIsAddSongsOpen(false)}
                  className="px-4 py-2 text-xs text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleAddSongsSubmit}
                  disabled={selectedTrackIdsToAdd.size === 0}
                  className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white text-xs font-semibold rounded-xl shadow-lg shadow-indigo-600/30"
                >
                  Add to Playlist
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Repeat Modal */}
      {activeTrack && (
        <RepeatModal
          isOpen={isRepeatModalOpen}
          trackTitle={activeTrack.display_title}
          onClose={() => setIsRepeatModalOpen(false)}
          onConfirm={(count) => {
            if (onRepeat) onRepeat(count);
            setIsRepeatModalOpen(false);
          }}
        />
      )}
    </div>
  );
};

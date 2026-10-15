import React, { useEffect, useState } from "react";
import {
  Clock,
  Disc3,
  Layers,
  ListPlus,
  Music2,
  Play,
  RotateCw,
  Shuffle,
  Sparkles,
} from "lucide-react";
import { PlaybackState, Playlist, Track } from "../types";
import { ArtworkImage } from "../components/ArtworkImage";
import { StarRating } from "../components/StarRating";
import { AddToPlaylistModal } from "../components/AddToPlaylistModal";
import { PoolSelectionModal } from "../components/PoolSelectionModal";
import {
  addTracksToPlaylist,
  createPlaylist,
  fetchPlaylists,
  fetchUpNext,
  playLibrary,
  playPlaylist,
  playTrack,
  reshuffleUpNext,
} from "../api";

interface Props {
  state: PlaybackState | null;
  onPlayLibrary?: () => void;
  onNavigateToPlaylists?: () => void;
  onToggleWholeDeck?: () => void;
  onRateCurrentTrack?: (rating: number) => void;
  onOpenLyrics?: () => void;
  onStateUpdate?: () => void;
}

const getFolderName = (folderPath?: string): string => {
  if (!folderPath) return "";
  const normalized = folderPath.replace(/\\/g, "/").replace(/\/+$/, "");
  const parts = normalized.split("/");
  return parts[parts.length - 1] || "";
};

export const NowPlayingView: React.FC<Props> = ({
  state,
  onPlayLibrary,
  onNavigateToPlaylists,
  onToggleWholeDeck,
  onRateCurrentTrack,
  onOpenLyrics,
  onStateUpdate,
}) => {
  const [isAddToPlaylistOpen, setIsAddToPlaylistOpen] = useState(false);
  const [isPoolModalOpen, setIsPoolModalOpen] = useState(false);
  const [availablePlaylists, setAvailablePlaylists] = useState<Playlist[]>([]);
  const [notificationMsg, setNotificationMsg] = useState<string | null>(null);

  const [upNextTracks, setUpNextTracks] = useState<Track[]>([]);
  const [isReshuffling, setIsReshuffling] = useState(false);

  const track = state?.current_track;
  const isPlaylistActive = Boolean(state?.active_playlist_id != null);
  const isWholeDeck = Boolean(state?.shuffle_whole_deck);
  const folderName = getFolderName(track?.folder_path);

  const loadUpNext = async () => {
    try {
      const limit = isPlaylistActive ? 1000 : 50;
      const tracks = await fetchUpNext(limit);
      if (tracks.length === 0) {
        // Deck reached the end -> auto reshuffle the entire upcoming tree
        const refreshed = await reshuffleUpNext(limit);
        setUpNextTracks(refreshed);
      } else {
        setUpNextTracks(tracks);
      }
    } catch {}
  };

  useEffect(() => {
    loadUpNext();
  }, [track?.id, isPlaylistActive, state?.active_playlist_id]);

  const handleOpenPoolModal = async () => {
    try {
      const pls = await fetchPlaylists();
      setAvailablePlaylists(pls);
    } catch {}
    setIsPoolModalOpen(true);
  };

  const handleSelectLibraryPool = async () => {
    try {
      if (onPlayLibrary) {
        await onPlayLibrary();
      } else {
        await playLibrary();
      }
      setNotificationMsg("Switched playback pool to Main Music Library.");
      setTimeout(() => setNotificationMsg(null), 3000);
      if (onStateUpdate) onStateUpdate();
      const tracks = await fetchUpNext(50);
      setUpNextTracks(tracks);
    } catch (err: any) {
      setNotificationMsg(`Failed to activate library pool: ${err.message}`);
      setTimeout(() => setNotificationMsg(null), 3000);
    }
  };

  const handleSelectPlaylistPool = async (playlistId: number) => {
    try {
      await playPlaylist(playlistId);
      const targetPl = availablePlaylists.find((p) => p.id === playlistId);
      setNotificationMsg(`Switched playback pool to "${targetPl?.name || "Playlist"}".`);
      setTimeout(() => setNotificationMsg(null), 3000);
      if (onStateUpdate) onStateUpdate();
      const tracks = await fetchUpNext(1000);
      setUpNextTracks(tracks);
    } catch (err: any) {
      setNotificationMsg(`Failed to activate playlist pool: ${err.message}`);
      setTimeout(() => setNotificationMsg(null), 3000);
    }
  };

  const handleReshuffleQueue = async () => {
    setIsReshuffling(true);
    try {
      const limit = isPlaylistActive ? 1000 : 50;
      const tracks = await reshuffleUpNext(limit);
      setUpNextTracks(tracks);
      setNotificationMsg(
        isPlaylistActive
          ? `Upcoming playlist queue reshuffled (${tracks.length} tracks).`
          : "Upcoming queue reshuffled with 50 tracks."
      );
      setTimeout(() => setNotificationMsg(null), 3000);
    } catch (err: any) {
      setNotificationMsg(`Failed to reshuffle queue: ${err.message}`);
      setTimeout(() => setNotificationMsg(null), 3000);
    } finally {
      setIsReshuffling(false);
    }
  };

  const handlePlayUpNextTrack = async (trackId: number) => {
    try {
      await playTrack(trackId);
      if (onStateUpdate) onStateUpdate();
      await loadUpNext();
    } catch (err: any) {
      setNotificationMsg(`Playback error: ${err.message}`);
      setTimeout(() => setNotificationMsg(null), 3000);
    }
  };

  const handleAddToPlaylistClick = async () => {
    if (!track) return;
    try {
      const pls = await fetchPlaylists();
      if (pls.length === 0) {
        const created = await createPlaylist("My Playlist");
        await addTracksToPlaylist(created.id, [track.id]);
        setNotificationMsg(`Created 'My Playlist' and added "${track.display_title}"!`);
        setTimeout(() => setNotificationMsg(null), 4000);
        return;
      }
      if (pls.length === 1) {
        await addTracksToPlaylist(pls[0].id, [track.id]);
        setNotificationMsg(`Added "${track.display_title}" to playlist "${pls[0].name}"!`);
        setTimeout(() => setNotificationMsg(null), 4000);
      } else {
        setAvailablePlaylists(pls);
        setIsAddToPlaylistOpen(true);
      }
    } catch (err: any) {
      const msg = err.message || "";
      setNotificationMsg(
        msg.toLowerCase().includes("already exists")
          ? "Song already exists in playlist."
          : `Failed to add track: ${msg}`
      );
      setTimeout(() => setNotificationMsg(null), 4000);
    }
  };

  const handleConfirmAddToPlaylist = async (playlistId: number) => {
    if (!track) return;
    try {
      await addTracksToPlaylist(playlistId, [track.id]);
      const targetPl = availablePlaylists.find((p) => p.id === playlistId);
      setNotificationMsg(
        `Added "${track.display_title}" to playlist "${targetPl?.name || "Playlist"}"!`
      );
      setTimeout(() => setNotificationMsg(null), 4000);
    } catch (err: any) {
      const msg = err.message || "";
      setNotificationMsg(
        msg.toLowerCase().includes("already exists")
          ? "Song already exists in playlist."
          : `Failed to add track: ${msg}`
      );
      setTimeout(() => setNotificationMsg(null), 4000);
    }
  };



  if (!track) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center min-h-[70vh] space-y-6">
        <div className="w-24 h-24 rounded-3xl bg-slate-800/60 border border-white/5 flex items-center justify-center text-slate-500 shadow-xl">
          <Disc3 className="w-12 h-12 animate-spin-slow opacity-40 text-cyan-400" />
        </div>
        <div className="space-y-2">
          <h2 className="text-2xl font-bold text-white">Music Library Shuffler</h2>
          <p className="text-slate-400 max-w-md text-sm">
            Shuffle and play random songs from your selected music folders directly through AIMP.
          </p>
        </div>
        {onPlayLibrary && (
          <button
            onClick={onPlayLibrary}
            className="flex items-center gap-3 px-8 py-4 rounded-2xl bg-gradient-to-r from-indigo-600 to-cyan-500 hover:from-indigo-500 hover:to-cyan-400 text-white font-bold text-sm shadow-xl shadow-indigo-600/40 active:scale-95 transition-all"
          >
            <Shuffle className="w-5 h-5" />
            Start Library Shuffle
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="flex-1 p-6 md:p-8 w-full max-w-[1750px] mx-auto space-y-6 animate-in fade-in duration-200">
      {/* Toast Notification Banner */}
      {notificationMsg && (
        <div className="p-3.5 bg-indigo-600/90 text-white text-xs font-semibold rounded-2xl shadow-xl flex items-center justify-between backdrop-blur-md">
          <span>{notificationMsg}</span>
          <button
            onClick={() => setNotificationMsg(null)}
            className="ml-3 p-1 hover:text-slate-200"
          >
            ✕
          </button>
        </div>
      )}

      {/* Top Breadcrumb & Minimalist Controls (Replaces chunky cards) */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-3 border-b border-white/5">
        <div>
          <span className="text-[11px] uppercase tracking-widest font-bold text-cyan-400">
            MUSIC LIBRARY / Shuffler
          </span>
          <h2 className="text-2xl font-extrabold text-white flex items-center gap-2 mt-0.5">
            {state?.context_name || "Library Shuffle"}
          </h2>
        </div>

        {/* Minimalized Badges: Pool count and Whole Deck toggle */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Clickable Library/Playlist Pool Badge */}
          <button
            onClick={handleOpenPoolModal}
            title="Click to select playback pool (Main Music Library vs Playlists)"
            className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-900/80 hover:bg-slate-800 border border-white/10 hover:border-cyan-500/40 text-xs text-slate-300 shadow-sm transition-all active:scale-95 cursor-pointer group"
          >
            <Layers className="w-3.5 h-3.5 text-cyan-400 group-hover:scale-110 transition-transform" />
            <span className="text-slate-400 font-medium">Pool:</span>
            <span className="font-bold text-white">{state?.pool_size || 0} tracks</span>
            <span className="text-[10px] bg-cyan-500/20 text-cyan-300 font-bold px-1.5 py-0.5 rounded ml-0.5 group-hover:bg-cyan-500 group-hover:text-slate-950 transition-colors">
              Change
            </span>
          </button>

          {/* Minimalist Whole Deck Toggle Badge */}
          {onToggleWholeDeck && (
            <button
              onClick={onToggleWholeDeck}
              title={
                isWholeDeck
                  ? "Whole Deck Active (Played songs included in shuffle)"
                  : "Unplayed Pool Only (Click to shuffle whole deck)"
              }
              className={`flex items-center gap-2 px-3 py-1.5 rounded-xl border text-xs font-semibold transition-all active:scale-95 shadow-sm ${
                isWholeDeck
                  ? "bg-indigo-600/20 border-indigo-500/50 text-indigo-300"
                  : "bg-slate-900/80 border-white/10 text-slate-400 hover:text-white hover:border-white/20"
              }`}
            >
              <Shuffle className="w-3.5 h-3.5" />
              <span>Use Played Songs:</span>
              <span
                className={`text-[10px] font-bold px-1.5 py-0.5 rounded transition-colors ${
                  isWholeDeck
                    ? "bg-indigo-600 text-white"
                    : "bg-slate-800 text-slate-400 border border-white/10"
                }`}
              >
                {isWholeDeck ? "ON" : "OFF"}
              </span>
            </button>
          )}
        </div>
      </div>

      {/* Two-Column Grid: Left Main Track Showcase + Right Up Next */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column: Main Track Card */}
        <div className="lg:col-span-7 xl:col-span-8 space-y-6">
          <div className="flex flex-col md:flex-row items-center md:items-start gap-8 bg-[#0e1424]/60 border border-white/5 rounded-3xl p-6 md:p-8 shadow-2xl backdrop-blur-md">
            {/* Large Album Artwork */}
            <div className="shrink-0 relative group">
              <div className="absolute -inset-2 bg-gradient-to-tr from-indigo-600/30 to-cyan-500/30 rounded-3xl blur-xl opacity-40 group-hover:opacity-70 transition-opacity" />
              <ArtworkImage
                trackId={track.id}
                className="w-64 h-64 md:w-80 md:h-80 rounded-2xl shadow-2xl relative border border-white/10"
                iconClassName="w-20 h-20 text-indigo-400"
              />
            </div>

            {/* Track Info (Title, Artist Name, Folder Name, Pills, Rating) */}
            <div className="flex-1 min-w-0 space-y-4 pt-2">
              <div>
                {/* Song Title (Balanced Font Size & Full Title Visible) */}
                <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight leading-tight break-words">
                  {track.display_title}
                </h1>

                {/* Artist Name and Folder Name */}
                <p className="text-base md:text-lg font-medium text-slate-300 mt-2 break-words flex flex-wrap items-center gap-2">
                  <span>{track.display_artist || "Unknown Artist"}</span>
                  {folderName && (
                    <>
                      <span className="text-slate-500 font-bold">·</span>
                      <span className="text-cyan-400 font-semibold">{folderName}</span>
                    </>
                  )}
                </p>

                {track.album && (
                  <p className="text-sm text-slate-400 mt-1 truncate">
                    {track.album}
                  </p>
                )}
              </div>

              {/* Details Pill Row */}
              <div className="flex flex-wrap items-center gap-3 text-xs text-slate-300 pt-1">
                <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-900 border border-white/5">
                  <Clock className="w-3.5 h-3.5 text-cyan-400" />
                  {track.display_duration}
                </span>
                <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-900 border border-white/5">
                  <Music2 className="w-3.5 h-3.5 text-indigo-400" />
                  {track.play_count} {track.play_count === 1 ? "play" : "plays"}
                </span>
                {track.genre && (
                  <span className="px-3 py-1.5 rounded-xl bg-slate-900 border border-white/5 text-slate-400">
                    {track.genre}
                  </span>
                )}
              </div>

              {/* 5-Star Interactive Rating Feature */}
              <div className="flex items-center gap-3 pt-2">
                <span className="text-xs font-semibold text-slate-400">Rating:</span>
                <StarRating
                  rating={track.rating || 0}
                  size="lg"
                  onRate={(newRating) => onRateCurrentTrack && onRateCurrentTrack(newRating)}
                />
              </div>

              {/* Quick Actions */}
              <div className="pt-3 flex flex-wrap items-center gap-3">
                <button
                  onClick={handleAddToPlaylistClick}
                  className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 hover:text-white font-semibold text-xs border border-indigo-500/30 active:scale-95 transition-all"
                >
                  <ListPlus className="w-4 h-4 text-indigo-400" />
                  Add to Playlist
                </button>

                {onOpenLyrics && (
                  <button
                    onClick={onOpenLyrics}
                    className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs border border-white/10 active:scale-95 transition-all"
                  >
                    <Sparkles className="w-4 h-4 text-cyan-400" />
                    Lyrics & Romanization
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Up Next Section */}
        <div className="lg:col-span-5 xl:col-span-4 bg-[#0e1424]/80 border border-white/5 rounded-3xl p-5 md:p-6 shadow-2xl backdrop-blur-md space-y-4">
          {/* Header with Reshuffle Button */}
          <div className="flex items-center justify-between pb-3 border-b border-white/5">
            <div className="flex items-center gap-2">
              <h3 className="text-lg font-bold text-white">Up Next</h3>
              <span className="px-2 py-0.5 rounded-md bg-indigo-500/15 text-indigo-300 text-[11px] font-bold">
                {upNextTracks.length} {isPlaylistActive ? "(Playlist)" : "(Deck)"}
              </span>
            </div>

            <button
              onClick={handleReshuffleQueue}
              disabled={isReshuffling}
              title="Reshuffle upcoming queue tracks"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-cyan-300 hover:text-cyan-200 font-semibold text-xs border border-cyan-500/20 active:scale-95 transition-all shadow-sm disabled:opacity-50"
            >
              <RotateCw className={`w-3.5 h-3.5 ${isReshuffling ? "animate-spin" : ""}`} />
              Reshuffle
            </button>
          </div>

          {/* Up Next List */}
          <div className="space-y-2 max-h-[520px] overflow-y-auto pr-1">
            {/* Currently Playing Song Row (Highlighted at the top) */}
            <div className="p-3 rounded-2xl bg-indigo-900/20 border border-indigo-500/40 flex items-center gap-3 shadow-md">
              <ArtworkImage
                trackId={track.id}
                className="w-12 h-12 rounded-xl shrink-0 border border-indigo-500/30 shadow-md"
              />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse shrink-0" />
                  <span className="text-[10px] uppercase tracking-wider font-bold text-emerald-400">
                    Now Playing
                  </span>
                </div>
                <h4 className="text-sm font-bold text-white truncate">
                  {track.display_title}
                </h4>
                <p className="text-xs text-slate-300 truncate flex items-center gap-1.5">
                  <span>{track.display_artist || "Unknown Artist"}</span>
                  {folderName && (
                    <>
                      <span className="text-slate-500">·</span>
                      <span className="text-cyan-400 font-medium">{folderName}</span>
                    </>
                  )}
                </p>
              </div>
            </div>

            {/* Upcoming Tracks in Deck */}
            {upNextTracks.length === 0 ? (
              <div className="py-8 text-center text-xs text-slate-500">
                No upcoming tracks queued in deck.
              </div>
            ) : (
              upNextTracks.map((nextT, idx) => {
                const nextFolder = getFolderName(nextT.folder_path);
                return (
                  <div
                    key={`${nextT.id}-${idx}`}
                    onClick={() => handlePlayUpNextTrack(nextT.id)}
                    title={`Play "${nextT.display_title}" now`}
                    className="p-2.5 rounded-2xl bg-slate-900/40 hover:bg-slate-800/80 border border-white/5 hover:border-white/10 flex items-center justify-between gap-3 group transition-all cursor-pointer"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <ArtworkImage
                        trackId={nextT.id}
                        className="w-11 h-11 rounded-xl shrink-0 border border-white/5 group-hover:border-indigo-500/30 transition-colors"
                      />
                      <div className="min-w-0">
                        <h5 className="text-sm font-semibold text-slate-200 group-hover:text-white truncate">
                          {nextT.display_title}
                        </h5>
                        <p className="text-xs text-slate-400 truncate flex items-center gap-1.5">
                          <span>{nextT.display_artist || "Unknown Artist"}</span>
                          {nextFolder && (
                            <>
                              <span className="text-slate-600">·</span>
                              <span className="text-cyan-400/80 font-medium">{nextFolder}</span>
                            </>
                          )}
                        </p>
                      </div>
                    </div>

                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handlePlayUpNextTrack(nextT.id);
                      }}
                      title="Play track"
                      className="p-2 text-slate-400 group-hover:text-white group-hover:bg-indigo-600 rounded-xl transition-all shrink-0 opacity-0 group-hover:opacity-100"
                    >
                      <Play className="w-3.5 h-3.5 fill-current" />
                    </button>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      <AddToPlaylistModal
        isOpen={isAddToPlaylistOpen}
        trackTitle={track.display_title}
        playlists={availablePlaylists}
        onClose={() => setIsAddToPlaylistOpen(false)}
        onSelectPlaylist={handleConfirmAddToPlaylist}
      />

      <PoolSelectionModal
        isOpen={isPoolModalOpen}
        onClose={() => setIsPoolModalOpen(false)}
        libraryPoolSize={state?.pool_size || 0}
        isPlaylistActive={isPlaylistActive}
        activePlaylistId={state?.active_playlist_id}
        playlists={availablePlaylists}
        onSelectLibraryPool={handleSelectLibraryPool}
        onSelectPlaylistPool={handleSelectPlaylistPool}
      />
    </div>
  );
};

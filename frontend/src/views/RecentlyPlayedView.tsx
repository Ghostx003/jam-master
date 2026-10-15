import React, { useEffect, useState } from "react";
import {
  Clock,
  History,
  ListPlus,
  Play,
  RotateCcw,
  Sparkles,
  X,
} from "lucide-react";
import {
  addTracksToPlaylist,
  createPlaylist,
  fetchHistory,
  fetchPlaylists,
  playTrack,
  setTrackRating,
} from "../api";
import { HistoryItem, Playlist } from "../types";
import { ArtworkImage } from "../components/ArtworkImage";
import { StarRating } from "../components/StarRating";
import { AddToPlaylistModal } from "../components/AddToPlaylistModal";

interface Props {
  onStateUpdate: () => void;
}

export const RecentlyPlayedView: React.FC<Props> = ({ onStateUpdate }) => {
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [playlists, setPlaylists] = useState<Playlist[]>([]);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  // Add to Playlist modal state
  const [targetTrack, setTargetTrack] = useState<{ id: number; title: string } | null>(null);
  const [isAddToPlaylistOpen, setIsAddToPlaylistOpen] = useState(false);

  const loadData = async () => {
    try {
      const [h, p] = await Promise.all([fetchHistory(100), fetchPlaylists()]);
      setHistory(h);
      setPlaylists(p);
    } catch (err: any) {
      setStatusMessage(`Error loading history: ${err.message}`);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleReplay = async (trackId: number) => {
    try {
      await playTrack(trackId);
      onStateUpdate();
      await loadData();
    } catch (err: any) {
      setStatusMessage(`Failed to replay track: ${err.message}`);
    }
  };

  const handleAddToPlaylistClick = async (track: { id: number; title: string }) => {
    try {
      const currentPlaylists = await fetchPlaylists();
      setPlaylists(currentPlaylists);

      if (currentPlaylists.length === 0) {
        // Auto-create default playlist
        const created = await createPlaylist("My Playlist");
        await addTracksToPlaylist(created.id, [track.id]);
        setStatusMessage(`Created 'My Playlist' and added "${track.title}".`);
        await loadData();
      } else if (currentPlaylists.length === 1) {
        // Auto-add to the single playlist
        const pl = currentPlaylists[0];
        await addTracksToPlaylist(pl.id, [track.id]);
        setStatusMessage(`Added "${track.title}" to ${pl.name}.`);
      } else {
        // Multiple playlists -> open picker modal
        setTargetTrack(track);
        setIsAddToPlaylistOpen(true);
      }
    } catch (err: any) {
      setStatusMessage(`Failed to add track: ${err.message}`);
    }
  };

  const handleConfirmAddToPlaylist = async (playlistId: number) => {
    if (!targetTrack) return;
    try {
      await addTracksToPlaylist(playlistId, [targetTrack.id]);
      const targetPl = playlists.find((p) => p.id === playlistId);
      setStatusMessage(`Added "${targetTrack.title}" to ${targetPl?.name || "playlist"}.`);
    } catch (err: any) {
      setStatusMessage(`Failed to add track: ${err.message}`);
    }
  };

  const handleRate = async (trackId: number, rating: number) => {
    try {
      await setTrackRating(trackId, rating);
      setHistory((prev) =>
        prev.map((item) =>
          item.track.id === trackId
            ? { ...item, track: { ...item.track, rating } }
            : item
        )
      );
    } catch (err: any) {
      setStatusMessage(`Failed to set rating: ${err.message}`);
    }
  };

  const formatPlayedAt = (timestamp: number) => {
    if (!timestamp) return "--";
    const date = new Date(timestamp * 1000);
    const datePart = date.toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
    });
    const timePart = date.toLocaleTimeString(undefined, {
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    });
    return `${datePart} · ${timePart}`;
  };

  return (
    <div className="flex-1 px-4 py-6 md:px-8 w-full space-y-6 animate-in fade-in duration-200">
      {/* Top Header */}
      <div className="flex items-center justify-between pb-4 border-b border-white/5">
        <div>
          <span className="text-xs uppercase tracking-widest font-bold text-indigo-400">
            Listening History
          </span>
          <h2 className="text-2xl font-bold text-white flex items-center gap-2 mt-0.5">
            Recently Played
          </h2>
        </div>
        <span className="text-xs text-slate-400">
          Showing last {history.length} plays
        </span>
      </div>

      {statusMessage && (
        <div className="p-3.5 rounded-xl bg-slate-800/80 border border-indigo-500/30 text-xs text-indigo-300 flex items-center justify-between">
          <span>{statusMessage}</span>
          <button onClick={() => setStatusMessage(null)} className="text-slate-400 hover:text-white">
            ✕
          </button>
        </div>
      )}

      {history.length === 0 ? (
        <div className="bg-[#111827]/40 border border-white/5 rounded-2xl p-16 text-center text-slate-500">
          <History className="w-12 h-12 mx-auto mb-3 opacity-40" />
          <p className="text-white font-medium">No listening history yet.</p>
          <p className="text-xs text-slate-500 mt-1">
            Tracks you play through AIMP will appear here automatically.
          </p>
        </div>
      ) : (
        <div className="bg-[#111827] border border-white/5 rounded-2xl overflow-hidden shadow-xl">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-900/80 text-slate-400 text-xs border-b border-white/5">
              <tr>
                <th className="py-3 px-3 w-10 text-center">#</th>
                <th className="py-3 px-3 font-semibold">Title</th>
                <th className="py-3 px-3 font-semibold w-40 truncate">Artist</th>
                <th className="py-3 px-3 font-semibold text-center w-28 whitespace-nowrap">Rating</th>
                <th className="py-3 px-3 font-semibold text-right w-20 whitespace-nowrap">Duration</th>
                <th className="py-3 px-3 font-semibold text-right whitespace-nowrap w-36 pr-4">Played At</th>
                <th className="py-3 px-3 text-center w-24 whitespace-nowrap">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 text-slate-300">
              {history.map((item, idx) => {
                const t = item.track;
                return (
                  <tr key={item.history_id} className="hover:bg-white/[0.03] transition-colors group">
                    <td className="py-3 px-3 text-slate-500 text-xs text-center">{idx + 1}</td>
                    <td className="py-3 px-3 flex items-center gap-3">
                      <ArtworkImage
                        trackId={t.id}
                        className="w-9 h-9 rounded-xl shrink-0"
                        iconClassName="w-4 h-4 text-indigo-400"
                      />
                      <div className="min-w-0">
                        <p className="font-semibold text-white truncate">
                          {t.display_title}
                        </p>
                        {item.was_skipped ? (
                          <span className="text-[10px] text-amber-400/80 font-medium">
                            Skipped
                          </span>
                        ) : null}
                      </div>
                    </td>
                    <td className="py-3 px-3 text-xs text-slate-400 truncate max-w-[180px]">
                      {t.display_artist || "--"}
                    </td>
                    <td className="py-3 px-3 text-center">
                      <StarRating
                        rating={t.rating || 0}
                        size="xs"
                        onRate={(r) => handleRate(t.id, r)}
                      />
                    </td>
                    <td className="py-3 px-3 text-right text-xs text-slate-400 font-mono">
                      {t.display_duration}
                    </td>
                    <td className="py-3 px-3 text-right text-xs text-slate-400 font-mono whitespace-nowrap pr-4">
                      {formatPlayedAt(item.played_at)}
                    </td>
                    <td className="py-3 px-3 text-center">
                      <div className="flex items-center justify-center gap-1.5">
                        <button
                          onClick={() => handleReplay(t.id)}
                          title="Replay Track"
                          className="p-1.5 bg-indigo-600/20 hover:bg-indigo-600 text-indigo-300 hover:text-white rounded-lg transition-colors"
                        >
                          <Play className="w-3.5 h-3.5 fill-current" />
                        </button>
                        <button
                          onClick={() =>
                            handleAddToPlaylistClick({
                              id: t.id,
                              title: t.display_title,
                            })
                          }
                          title="Add to Playlist"
                          className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white rounded-lg transition-colors"
                        >
                          <ListPlus className="w-3.5 h-3.5" />
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

      <AddToPlaylistModal
        isOpen={isAddToPlaylistOpen}
        trackTitle={targetTrack?.title || ""}
        playlists={playlists}
        onClose={() => setIsAddToPlaylistOpen(false)}
        onSelectPlaylist={handleConfirmAddToPlaylist}
      />
    </div>
  );
};

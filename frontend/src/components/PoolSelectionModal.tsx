import React from "react";
import { CheckCircle2, FolderHeart, Layers, ListMusic, Music, Play, X } from "lucide-react";
import { Playlist } from "../types";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  libraryPoolSize: number;
  isPlaylistActive: boolean;
  activePlaylistId?: number | null;
  playlists: Playlist[];
  onSelectLibraryPool: () => void;
  onSelectPlaylistPool: (playlistId: number) => void;
}

export const PoolSelectionModal: React.FC<Props> = ({
  isOpen,
  onClose,
  libraryPoolSize,
  isPlaylistActive,
  activePlaylistId,
  playlists,
  onSelectLibraryPool,
  onSelectPlaylistPool,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-150">
      <div className="bg-[#0f172a] border border-white/10 rounded-3xl w-full max-w-lg p-6 shadow-2xl space-y-5">
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-white/5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 flex items-center justify-center shadow-inner">
              <Layers className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-white text-lg">Select Playback Pool</h3>
              <p className="text-xs text-slate-400">
                Choose the song pool to shuffle and play in Now Playing.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-xl text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Option 1: Big Music Library Pool */}
        <div className="space-y-2">
          <span className="text-[11px] font-bold uppercase tracking-wider text-cyan-400">
            Primary Library Source
          </span>

          <div
            onClick={() => {
              onSelectLibraryPool();
              onClose();
            }}
            className={`p-4 rounded-2xl border transition-all cursor-pointer flex items-center justify-between gap-4 group ${
              !isPlaylistActive
                ? "bg-gradient-to-r from-cyan-950/40 to-indigo-950/40 border-cyan-500/50 shadow-lg shadow-cyan-950/50"
                : "bg-slate-900/70 border-white/10 hover:border-cyan-500/30 hover:bg-slate-800/80"
            }`}
          >
            <div className="flex items-center gap-3.5 min-w-0">
              <div
                className={`w-11 h-11 rounded-xl flex items-center justify-center shrink-0 border ${
                  !isPlaylistActive
                    ? "bg-cyan-500/20 border-cyan-500/40 text-cyan-300"
                    : "bg-slate-800 border-white/5 text-slate-400 group-hover:text-cyan-400"
                }`}
              >
                <FolderHeart className="w-5 h-5" />
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <h4 className="font-bold text-white text-sm truncate">
                    Main Music Library Pool
                  </h4>
                  {!isPlaylistActive && (
                    <span className="flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                      <CheckCircle2 className="w-3 h-3" />
                      Active
                    </span>
                  )}
                </div>
                <p className="text-xs text-slate-400 truncate">
                  Shuffles all songs across your selected music folders
                </p>
                <p className="text-[11px] font-semibold text-cyan-400 mt-0.5 font-mono">
                  {libraryPoolSize.toLocaleString()} eligible tracks
                </p>
              </div>
            </div>

            <button
              type="button"
              className={`p-2.5 rounded-xl transition-all shrink-0 ${
                !isPlaylistActive
                  ? "bg-cyan-500 text-slate-950 font-bold shadow-md"
                  : "bg-slate-800 text-slate-400 group-hover:bg-cyan-500 group-hover:text-slate-950"
              }`}
            >
              <Play className="w-4 h-4 fill-current" />
            </button>
          </div>
        </div>

        {/* Option 2: Custom Playlists Pools */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-indigo-400">
              Playlist Pools
            </span>
            <span className="text-xs text-slate-500 font-medium">
              {playlists.length} {playlists.length === 1 ? "playlist" : "playlists"} available
            </span>
          </div>

          <div className="max-h-60 overflow-y-auto space-y-2 pr-1 custom-scrollbar">
            {playlists.length === 0 ? (
              <div className="p-6 text-center text-xs text-slate-500 bg-slate-900/40 rounded-2xl border border-white/5">
                No custom playlists created yet. Create playlists in the Playlists section.
              </div>
            ) : (
              playlists.map((pl) => {
                const isActive = isPlaylistActive && activePlaylistId === pl.id;
                return (
                  <div
                    key={pl.id}
                    onClick={() => {
                      onSelectPlaylistPool(pl.id);
                      onClose();
                    }}
                    className={`p-3.5 rounded-2xl border transition-all cursor-pointer flex items-center justify-between gap-3 group ${
                      isActive
                        ? "bg-indigo-950/40 border-indigo-500/50 shadow-md shadow-indigo-950/40"
                        : "bg-slate-900/60 border-white/5 hover:border-indigo-500/30 hover:bg-slate-800/70"
                    }`}
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div
                        className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 border ${
                          isActive
                            ? "bg-indigo-500/20 border-indigo-500/40 text-indigo-300"
                            : "bg-slate-800 border-white/5 text-slate-400 group-hover:text-indigo-400"
                        }`}
                      >
                        <ListMusic className="w-4 h-4" />
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <p className="text-sm font-semibold text-white group-hover:text-indigo-300 truncate">
                            {pl.name}
                          </p>
                          {isActive && (
                            <span className="flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                              <CheckCircle2 className="w-2.5 h-2.5" />
                              Active
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-slate-400">
                          {pl.track_count || 0} {pl.track_count === 1 ? "song" : "songs"}
                        </p>
                      </div>
                    </div>

                    <button
                      type="button"
                      className={`p-2 rounded-xl transition-all shrink-0 ${
                        isActive
                          ? "bg-indigo-600 text-white font-bold"
                          : "bg-slate-800 text-slate-400 group-hover:bg-indigo-600 group-hover:text-white"
                      }`}
                    >
                      <Play className="w-3.5 h-3.5 fill-current" />
                    </button>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Footer info */}
        <div className="pt-2 text-center">
          <p className="text-[11px] text-slate-500">
            Selected pool immediately begins shuffling and playing via AIMP.
          </p>
        </div>
      </div>
    </div>
  );
};

import React from "react";
import { ListMusic, Plus, X } from "lucide-react";
import { Playlist } from "../types";

interface Props {
  isOpen: boolean;
  trackTitle: string;
  playlists: Playlist[];
  onClose: () => void;
  onSelectPlaylist: (playlistId: number) => void;
  onCreateNewPlaylist?: () => void;
}

export const AddToPlaylistModal: React.FC<Props> = ({
  isOpen,
  trackTitle,
  playlists,
  onClose,
  onSelectPlaylist,
  onCreateNewPlaylist,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="bg-[#111827] border border-white/10 rounded-3xl w-full max-w-md p-6 shadow-2xl space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-white/5">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-indigo-500/20 text-indigo-400 flex items-center justify-center">
              <ListMusic className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-bold text-white text-base">Add to Playlist</h3>
              <p className="text-xs text-slate-400 truncate max-w-[260px]">{trackTitle}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-white/5"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <p className="text-xs text-slate-400 font-medium">Select destination playlist:</p>

        <div className="max-h-60 overflow-y-auto space-y-2 pr-1">
          {playlists.map((pl) => (
            <button
              key={pl.id}
              onClick={() => {
                onSelectPlaylist(pl.id);
                onClose();
              }}
              className="w-full flex items-center justify-between p-3 rounded-2xl bg-slate-900/80 hover:bg-indigo-600/20 border border-white/5 hover:border-indigo-500/40 text-left transition-all group"
            >
              <div>
                <p className="text-sm font-semibold text-white group-hover:text-indigo-300">
                  {pl.name}
                </p>
                <p className="text-[11px] text-slate-400">
                  {pl.track_count} tracks {pl.target_capacity ? `· Limit: ${pl.target_capacity}` : ""}
                </p>
              </div>
              <span className="text-xs text-indigo-400 font-medium opacity-0 group-hover:opacity-100 transition-opacity">
                Add →
              </span>
            </button>
          ))}
        </div>

        {onCreateNewPlaylist && (
          <button
            onClick={() => {
              onClose();
              onCreateNewPlaylist();
            }}
            className="w-full py-2.5 px-4 rounded-2xl border border-dashed border-white/20 hover:border-indigo-400 text-xs font-semibold text-slate-300 hover:text-white flex items-center justify-center gap-2 hover:bg-white/5 transition-all"
          >
            <Plus className="w-4 h-4 text-indigo-400" />
            Create New Playlist
          </button>
        )}
      </div>
    </div>
  );
};

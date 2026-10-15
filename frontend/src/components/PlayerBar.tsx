import React, { useState } from "react";
import {
  Heart,
  ListMusic,
  ListPlus,
  Maximize2,
  Pause,
  Play,
  Plus,
  PlusCircle,
  Repeat,
  Shuffle,
  SkipBack,
  SkipForward,
  Sparkles,
} from "lucide-react";
import { PlaybackState } from "../types";
import { ArtworkImage } from "./ArtworkImage";
import { RepeatModal } from "./RepeatModal";
import { ProgressSlider } from "./ProgressSlider";
import { VolumeSlider } from "./VolumeSlider";

interface Props {
  state: PlaybackState | null;
  onNext: () => void;
  onPrev: () => void;
  onShuffleMore: () => void;
  onPause: () => void;
  onRepeat: (count: number) => void;
  onOpenNowPlaying: () => void;
  onSeek?: (positionSeconds: number) => void;
  onVolumeChange?: (volume: number) => void;
  onAddToPlaylist?: () => void;
  onOpenLyrics?: () => void;
  onToggleUpNext?: () => void;
}

export const PlayerBar: React.FC<Props> = ({
  state,
  onNext,
  onPrev,
  onShuffleMore,
  onPause,
  onRepeat,
  onOpenNowPlaying,
  onSeek,
  onVolumeChange,
  onAddToPlaylist,
  onOpenLyrics,
  onToggleUpNext,
}) => {
  const [isRepeatModalOpen, setIsRepeatModalOpen] = useState(false);
  const [isLiked, setIsLiked] = useState(false);

  const track = state?.current_track;
  const isRepeating = (state?.repeats_remaining ?? 0) > 0;
  const isPlaying = Boolean(state?.is_playing);
  const position = state?.position_seconds || 0;
  const duration = state?.duration_seconds || (track?.duration || 0);
  const volume = state?.volume ?? 100;
  const aimpConnected = Boolean(state?.aimp_connected);

  const handleFullscreenToggle = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(() => {});
    } else {
      document.exitFullscreen().catch(() => {});
    }
  };

  const getFolderName = (folderPath?: string): string => {
    if (!folderPath) return "";
    const normalized = folderPath.replace(/\\/g, "/").replace(/\/+$/, "");
    const parts = normalized.split("/");
    return parts[parts.length - 1] || "";
  };

  const folderName = getFolderName(track?.folder_path);

  return (
    <>
      <div className="h-28 bg-[#090d16]/98 backdrop-blur-xl border-t border-white/10 px-6 flex items-center justify-between sticky bottom-0 z-40 shadow-2xl select-none">
        {/* Left: Track Information & Add to Playlist */}
        <div className="flex items-center gap-3.5 w-[30%] min-w-0">
          <div
            onClick={onOpenNowPlaying}
            className="cursor-pointer group shrink-0 relative"
            title="Open Now Playing"
          >
            <ArtworkImage
              trackId={track?.id}
              className="w-14 h-14 md:w-16 md:h-16 rounded-xl shrink-0 group-hover:scale-105 transition-transform shadow-lg border border-white/10"
            />
          </div>

          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <h4
                onClick={onOpenNowPlaying}
                className="text-sm md:text-base font-bold text-white truncate cursor-pointer hover:text-indigo-400 transition-colors"
                title={track?.display_title}
              >
                {track ? track.display_title : "No Track Playing"}
              </h4>

              {/* Heart Favorite Toggle */}
              <button
                type="button"
                onClick={() => setIsLiked(!isLiked)}
                title={isLiked ? "Favorited" : "Favorite song"}
                className={`p-1 rounded-full transition-colors ${
                  isLiked
                    ? "text-rose-500 fill-rose-500 hover:text-rose-400"
                    : "text-slate-500 hover:text-slate-300"
                }`}
              >
                <Heart className={`w-4 h-4 ${isLiked ? "fill-current" : ""}`} />
              </button>

              {/* (+) Plus button to add song to playlist */}
              {onAddToPlaylist && (
                <button
                  type="button"
                  onClick={onAddToPlaylist}
                  title="Add to Playlist"
                  className="p-1 rounded-full text-slate-400 hover:text-cyan-400 hover:bg-white/5 transition-colors"
                >
                  <PlusCircle className="w-4 h-4" />
                </button>
              )}
            </div>

            <p className="text-xs text-slate-400 truncate mt-0.5 flex items-center gap-1.5">
              <span>{track ? track.display_artist || "Unknown Artist" : "Select music to begin"}</span>
              {track && folderName && (
                <>
                  <span className="text-slate-600">·</span>
                  <span className="text-cyan-400/90 font-medium">{folderName}</span>
                </>
              )}
            </p>

            {/* Quick text link "+ Add to Playlist" */}
            {onAddToPlaylist && (
              <button
                type="button"
                onClick={onAddToPlaylist}
                className="flex items-center gap-1 text-[11px] text-slate-500 hover:text-indigo-400 transition-colors mt-0.5 font-medium"
              >
                <ListPlus className="w-3 h-3" />
                Add to Playlist
              </button>
            )}
          </div>
        </div>

        {/* Center: Playback Controls & Interactive Seek Slider (Exactly matching Screenshot 1) */}
        <div className="flex flex-col items-center gap-1.5 w-[42%] max-w-2xl px-2">
          {/* Top Control Buttons with Sub-Labels */}
          <div className="flex items-center gap-5 md:gap-7">
            {/* Shuffle Button */}
            <button
              onClick={onShuffleMore}
              title="Shuffle More (Fresh Selection)"
              className="flex flex-col items-center gap-1 group active:scale-95 transition-all"
            >
              <Shuffle className="w-5 h-5 text-cyan-400 group-hover:scale-110 transition-transform shadow-cyan-400/50" />
              <span className="text-[10px] font-semibold text-cyan-400">Shuffle</span>
            </button>

            {/* Previous Song Button */}
            <button
              onClick={onPrev}
              title="Previous Song"
              className="flex flex-col items-center gap-1 group text-slate-300 hover:text-white active:scale-95 transition-all"
            >
              <SkipBack className="w-5 h-5 group-hover:scale-110 transition-transform" />
              <span className="text-[10px] font-semibold text-slate-400 group-hover:text-slate-200">
                Previous Song
              </span>
            </button>

            {/* Large Circular Glowing Play/Pause Button */}
            <button
              onClick={onPause}
              title={isPlaying ? "Pause AIMP" : "Play AIMP"}
              className="w-13 h-13 md:w-14 md:h-14 rounded-full bg-gradient-to-tr from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 text-white flex items-center justify-center shadow-xl shadow-indigo-600/50 hover:shadow-indigo-500/60 active:scale-95 transition-all mx-1 shrink-0 ring-4 ring-indigo-500/20"
            >
              {isPlaying ? (
                <Pause className="w-6 h-6 fill-current" />
              ) : (
                <Play className="w-6 h-6 fill-current ml-0.5" />
              )}
            </button>

            {/* Next Song Button */}
            <button
              onClick={onNext}
              title="Next Song"
              className="flex flex-col items-center gap-1 group text-slate-300 hover:text-white active:scale-95 transition-all"
            >
              <SkipForward className="w-5 h-5 group-hover:scale-110 transition-transform" />
              <span className="text-[10px] font-semibold text-slate-400 group-hover:text-slate-200">
                Next Song
              </span>
            </button>

            {/* Repeat Button */}
            <button
              onClick={() => setIsRepeatModalOpen(true)}
              title="Repeat Current Song"
              className="flex flex-col items-center gap-1 group text-slate-300 hover:text-white active:scale-95 transition-all"
            >
              <Repeat
                className={`w-5 h-5 group-hover:scale-110 transition-transform ${
                  isRepeating ? "text-indigo-400" : ""
                }`}
              />
              <span
                className={`text-[10px] font-semibold ${
                  isRepeating ? "text-indigo-400" : "text-slate-400 group-hover:text-slate-200"
                }`}
              >
                Repeat {isRepeating && `(${state?.repeats_remaining})`}
              </span>
            </button>
          </div>

          {/* Interactive Progress Slider with 0:00 and Duration */}
          <div className="w-full px-1">
            <ProgressSlider
              currentTime={position}
              duration={duration}
              onSeek={(target) => onSeek && onSeek(target)}
              disabled={!track}
              size="sm"
            />
          </div>
        </div>

        {/* Right: Lyrics Button, Queue Toggle & AIMP Volume Slider (Screenshot 1) */}
        <div className="flex items-center justify-end gap-3.5 w-[28%] text-xs">
          {/* Lyrics Button */}
          {onOpenLyrics && (
            <button
              onClick={onOpenLyrics}
              title="View lyrics and Indic romanization"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800/80 hover:bg-slate-700/80 border border-white/10 text-white font-medium text-xs hover:border-cyan-500/40 transition-all shadow-sm active:scale-95"
            >
              <Sparkles className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
              Lyrics
            </button>
          )}

          {/* Up Next Queue Toggle Icon */}
          {onToggleUpNext && (
            <button
              onClick={onToggleUpNext}
              title="Toggle Up Next Queue"
              className="p-2 text-slate-400 hover:text-white hover:bg-white/5 rounded-xl transition-colors active:scale-95"
            >
              <ListMusic className="w-4 h-4" />
            </button>
          )}

          {/* Fullscreen Toggle */}
          <button
            onClick={handleFullscreenToggle}
            title="Toggle Fullscreen"
            className="p-2 text-slate-400 hover:text-white hover:bg-white/5 rounded-xl transition-colors active:scale-95 hidden sm:block"
          >
            <Maximize2 className="w-4 h-4" />
          </button>

          {/* AIMP Volume Control with Label */}
          {onVolumeChange && (
            <div className="flex items-center gap-2 pl-1 border-l border-white/10">
              <span className="text-xs font-semibold text-slate-300 hidden lg:inline">
                AIMP Volume:
              </span>
              <VolumeSlider
                volume={volume}
                onVolumeChange={onVolumeChange}
                disabled={!aimpConnected && !track}
              />
            </div>
          )}
        </div>
      </div>

      <RepeatModal
        isOpen={isRepeatModalOpen}
        trackTitle={track?.display_title || ""}
        onClose={() => setIsRepeatModalOpen(false)}
        onConfirm={onRepeat}
      />
    </>
  );
};

import React, { useState } from "react";
import { Volume1, Volume2, VolumeX } from "lucide-react";

interface Props {
  volume: number;
  onVolumeChange: (volume: number) => void;
  disabled?: boolean;
  className?: string;
}

export const VolumeSlider: React.FC<Props> = ({
  volume,
  onVolumeChange,
  disabled = false,
  className = "",
}) => {
  const [prevVolume, setPrevVolume] = useState<number>(volume || 100);

  const handleToggleMute = () => {
    if (disabled) return;
    if (volume > 0) {
      setPrevVolume(volume);
      onVolumeChange(0);
    } else {
      onVolumeChange(prevVolume > 0 ? prevVolume : 80);
    }
  };

  const Icon = volume === 0 ? VolumeX : volume < 50 ? Volume1 : Volume2;

  return (
    <div className={`flex items-center gap-2 select-none ${className}`}>
      <button
        type="button"
        disabled={disabled}
        onClick={handleToggleMute}
        title={volume === 0 ? "Unmute" : "Mute AIMP"}
        className="text-slate-400 hover:text-white transition-colors p-1 disabled:opacity-40"
      >
        <Icon className="w-4 h-4" />
      </button>

      <div className="relative w-24 flex items-center group cursor-pointer py-2">
        <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden border border-white/5">
          <div
            className="h-full bg-gradient-to-r from-indigo-500 to-cyan-400 rounded-full"
            style={{ width: `${Math.max(0, Math.min(100, volume))}%` }}
          />
        </div>

        <input
          type="range"
          min={0}
          max={100}
          step={1}
          value={volume}
          disabled={disabled}
          onChange={(e) => onVolumeChange(parseInt(e.target.value) || 0)}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer disabled:cursor-not-allowed"
          title={`Volume: ${volume}%`}
        />
      </div>

      <span className="text-[10px] font-mono text-slate-500 w-7 text-right">
        {volume}%
      </span>
    </div>
  );
};

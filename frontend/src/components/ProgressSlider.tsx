import React, { useEffect, useState } from "react";

interface Props {
  currentTime: number;
  duration: number;
  onSeek: (positionSeconds: number) => void;
  disabled?: boolean;
  className?: string;
  size?: "sm" | "md" | "lg";
}

export const ProgressSlider: React.FC<Props> = ({
  currentTime,
  duration,
  onSeek,
  disabled = false,
  className = "",
  size = "md",
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [dragValue, setDragValue] = useState<number>(0);

  // Sync with incoming currentTime unless user is currently scrubbing
  const displayTime = isDragging ? dragValue : currentTime;
  const maxDuration = Math.max(duration, 0.1);
  const progressPercent = Math.min(100, Math.max(0, (displayTime / maxDuration) * 100));

  const formatTime = (seconds: number): string => {
    if (isNaN(seconds) || seconds < 0) return "0:00";
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs < 10 ? "0" : ""}${secs}`;
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setDragValue(parseFloat(e.target.value));
  };

  const handleMouseDown = () => {
    setIsDragging(true);
    setDragValue(currentTime);
  };

  const handleMouseUp = () => {
    if (isDragging) {
      setIsDragging(false);
      onSeek(dragValue);
    }
  };

  const handleTouchEnd = () => {
    if (isDragging) {
      setIsDragging(false);
      onSeek(dragValue);
    }
  };

  const trackHeights = {
    sm: "h-1.5",
    md: "h-2",
    lg: "h-2.5",
  };

  return (
    <div className={`w-full flex items-center gap-3 select-none ${className}`}>
      {/* Current Time */}
      <span className="text-[11px] font-mono text-slate-400 min-w-[38px] text-right">
        {formatTime(displayTime)}
      </span>

      {/* Seek Track Container */}
      <div className="relative flex-1 flex items-center group cursor-pointer py-2">
        {/* Background Track */}
        <div
          className={`w-full ${trackHeights[size]} bg-slate-800 rounded-full overflow-hidden border border-white/5`}
        >
          {/* Active Gradient Fill */}
          <div
            className="h-full bg-gradient-to-r from-indigo-500 via-cyan-400 to-indigo-400 rounded-full transition-all duration-75"
            style={{ width: `${progressPercent}%` }}
          />
        </div>

        {/* HTML5 Range Input Overlay for Accessibility and Smooth Scrubbing */}
        <input
          type="range"
          min={0}
          max={maxDuration}
          step={0.5}
          value={displayTime}
          disabled={disabled || duration <= 0}
          onChange={handleChange}
          onMouseDown={handleMouseDown}
          onMouseUp={handleMouseUp}
          onTouchStart={handleMouseDown}
          onTouchEnd={handleTouchEnd}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer disabled:cursor-not-allowed"
          title={`Seek: ${formatTime(displayTime)} / ${formatTime(duration)}`}
        />

        {/* Visual Thumb Indicator */}
        <div
          className="absolute top-1/2 -translate-y-1/2 -ml-1.5 w-3.5 h-3.5 rounded-full bg-white shadow-[0_0_10px_rgba(255,255,255,0.7)] opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"
          style={{ left: `${progressPercent}%` }}
        />
      </div>

      {/* Duration */}
      <span className="text-[11px] font-mono text-slate-400 min-w-[38px]">
        {formatTime(duration)}
      </span>
    </div>
  );
};

import React, { useState } from "react";
import { Disc3, Music } from "lucide-react";
import { getArtworkUrl } from "../api";

interface Props {
  trackId: number | null | undefined;
  className?: string;
  iconClassName?: string;
  alt?: string;
}

export const ArtworkImage: React.FC<Props> = ({
  trackId,
  className = "w-16 h-16 rounded-xl",
  iconClassName = "w-8 h-8 text-indigo-400",
  alt = "Album Artwork",
}) => {
  const [hasError, setHasError] = useState(false);

  // If no trackId or error loading, show tasteful SVG placeholder
  if (!trackId || hasError) {
    return (
      <div
        className={`bg-slate-800/80 border border-white/5 flex items-center justify-center overflow-hidden shadow-inner ${className}`}
      >
        <div className="relative flex items-center justify-center">
          <Disc3 className={`${iconClassName} opacity-70 animate-pulse`} />
          <Music className="w-3.5 h-3.5 text-indigo-300 absolute" />
        </div>
      </div>
    );
  }

  return (
    <img
      src={getArtworkUrl(trackId)}
      alt={alt}
      onError={() => setHasError(true)}
      className={`object-cover bg-slate-800 border border-white/10 shadow-md transition-opacity duration-300 ${className}`}
      loading="lazy"
    />
  );
};

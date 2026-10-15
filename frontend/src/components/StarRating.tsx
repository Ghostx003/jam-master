import React, { useState } from "react";
import { Star } from "lucide-react";

interface Props {
  rating: number;
  onRate?: (rating: number) => void;
  readonly?: boolean;
  size?: "xs" | "sm" | "md" | "lg";
}

export const StarRating: React.FC<Props> = ({
  rating,
  onRate,
  readonly = false,
  size = "sm",
}) => {
  const [hoverRating, setHoverRating] = useState<number | null>(null);

  const starSizes = {
    xs: "w-3 h-3",
    sm: "w-3.5 h-3.5",
    md: "w-4 h-4",
    lg: "w-5 h-5",
  };

  const current = hoverRating !== null ? hoverRating : rating;

  const handleClick = (e: React.MouseEvent, starIndex: number) => {
    e.stopPropagation();
    if (readonly || !onRate) return;
    const nextRating = rating === starIndex ? 0 : starIndex;
    onRate(nextRating);
  };

  return (
    <div
      className="inline-flex items-center gap-0.5"
      onMouseLeave={() => !readonly && setHoverRating(null)}
      title={readonly ? `Rating: ${rating}/5` : `Rate: ${rating}/5 stars`}
    >
      {[1, 2, 3, 4, 5].map((star) => {
        const isFilled = star <= current;
        return (
          <button
            key={star}
            type="button"
            disabled={readonly}
            onClick={(e) => handleClick(e, star)}
            onMouseEnter={() => !readonly && setHoverRating(star)}
            className={`transition-all duration-150 p-0.5 ${
              readonly
                ? "cursor-default"
                : "cursor-pointer hover:scale-125 focus:outline-none"
            }`}
          >
            <Star
              className={`${starSizes[size]} transition-colors ${
                isFilled
                  ? "text-amber-400 fill-amber-400 drop-shadow-[0_0_6px_rgba(251,191,36,0.5)]"
                  : "text-slate-600 hover:text-amber-300 fill-transparent"
              }`}
            />
          </button>
        );
      })}
    </div>
  );
};

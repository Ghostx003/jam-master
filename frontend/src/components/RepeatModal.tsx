import React, { useState } from "react";
import { Repeat, X } from "lucide-react";

interface Props {
  isOpen: boolean;
  trackTitle: string;
  onClose: () => void;
  onConfirm: (count: number) => void;
}

export const RepeatModal: React.FC<Props> = ({
  isOpen,
  trackTitle,
  onClose,
  onConfirm,
}) => {
  const [count, setCount] = useState<number>(1);

  if (!isOpen) return null;

  const presets = [1, 2, 3, 5];

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (count > 0) {
      onConfirm(count);
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-[#111827] border border-white/10 rounded-2xl w-full max-w-md p-6 shadow-2xl relative animate-in fade-in zoom-in-95 duration-150">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-white p-1 rounded-lg hover:bg-white/5 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-xl bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
            <Repeat className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">Repeat Track</h3>
            <p className="text-xs text-slate-400 line-clamp-1">{trackTitle}</p>
          </div>
        </div>

        <p className="text-sm text-slate-300 mb-4">
          How many <span className="font-semibold text-indigo-300">additional times</span> would
          you like to repeat this song before resuming shuffle?
        </p>

        {/* Quick Presets */}
        <div className="flex gap-2 mb-4">
          {presets.map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => setCount(p)}
              className={`flex-1 py-2 rounded-xl text-sm font-medium border transition-colors ${
                count === p
                  ? "bg-indigo-600 text-white border-indigo-500"
                  : "bg-slate-800 text-slate-300 border-white/5 hover:bg-slate-700"
              }`}
            >
              +{p} {p === 1 ? "time" : "times"}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">
              Custom Repeat Count
            </label>
            <input
              type="number"
              min="1"
              max="99"
              value={count}
              onChange={(e) => setCount(Math.max(1, parseInt(e.target.value) || 1))}
              className="w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:border-indigo-500 text-sm"
            />
          </div>

          <div className="flex gap-3 justify-end pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm text-slate-400 hover:text-white rounded-xl hover:bg-white/5 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-5 py-2 text-sm font-medium bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl shadow-lg shadow-indigo-600/30 transition-all"
            >
              Set Repeat
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

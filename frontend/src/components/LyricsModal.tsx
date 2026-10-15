import React, { useEffect, useState } from "react";
import { Copy, Languages, Loader2, Music, Search, Sparkles, X } from "lucide-react";
import { fetchLyrics } from "../api";
import { LyricsResponse } from "../types";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  artist: string;
}

export const LyricsModal: React.FC<Props> = ({ isOpen, onClose, title, artist }) => {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<LyricsResponse | null>(null);
  const [viewMode, setViewMode] = useState<"romanized" | "original">("romanized");
  const [copied, setCopied] = useState(false);
  const [searchQuery, setSearchQuery] = useState(title);

  const performFetch = (targetTitle: string, targetArtist: string = "") => {
    if (!targetTitle.trim()) return;
    setLoading(true);
    setData(null);
    setViewMode("romanized");
    setCopied(false);

    fetchLyrics(targetArtist, targetTitle.trim())
      .then((res) => {
        setData(res);
        if (res.romanized) {
          setViewMode("romanized");
        } else {
          setViewMode("original");
        }
      })
      .catch((err) => {
        setData({
          found: false,
          artist: targetArtist,
          title: targetTitle,
          lyrics: null,
          romanized: null,
          is_indic: false,
          message: err.message || "Failed to load lyrics.",
        });
      })
      .finally(() => {
        setLoading(false);
      });
  };

  useEffect(() => {
    if (!isOpen || !title) return;
    setSearchQuery(title);
    // Search directly by title to avoid messy YouTube tags/artist channel mismatches
    performFetch(title, artist);
  }, [isOpen, title, artist]);

  const handleManualSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      performFetch(searchQuery.trim(), "");
    }
  };

  if (!isOpen) return null;

  const currentLyricsText =
    viewMode === "romanized" && data?.romanized ? data.romanized : data?.lyrics || "";

  const handleCopy = () => {
    if (!currentLyricsText) return;
    navigator.clipboard.writeText(currentLyricsText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="bg-[#0f172a] border border-white/10 rounded-3xl w-full max-w-2xl max-h-[88vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="p-5 border-b border-white/10 flex items-center justify-between">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 shrink-0">
              <Sparkles className="w-5 h-5 text-cyan-400" />
            </div>
            <div className="min-w-0">
              <span className="text-[10px] font-bold tracking-widest text-cyan-400 uppercase">
                Lyrics & Romanization
              </span>
              <h3 className="text-base font-bold text-white truncate">
                {data?.title || title}
              </h3>
              <p className="text-xs text-slate-400 truncate">
                {data?.artist || artist || "Unknown Artist"}
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-white rounded-xl hover:bg-white/5 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Small In-Modal Exact Title Search Bar */}
        <div className="px-5 py-3 bg-slate-900/90 border-b border-white/5">
          <form onSubmit={handleManualSearch} className="flex items-center gap-2">
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Type exact song title to search lyrics..."
                className="w-full pl-9 pr-3 py-1.5 bg-slate-800/80 border border-white/10 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500/60 transition-colors"
              />
            </div>
            <button
              type="submit"
              disabled={loading || !searchQuery.trim()}
              className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all shrink-0 active:scale-95"
            >
              {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Search className="w-3.5 h-3.5" />}
              Search
            </button>
          </form>
        </div>

        {/* Indic Romanization Toggle & Actions */}
        {data?.found && data.is_indic && data.romanized && (
          <div className="px-6 py-3 bg-slate-900/60 border-b border-white/5 flex items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <Languages className="w-4 h-4 text-cyan-400" />
              <span className="text-xs font-semibold text-slate-300">
                Hindi / Punjabi Detected:
              </span>
            </div>
            <div className="flex items-center bg-slate-800 p-1 rounded-xl border border-white/5 text-xs font-semibold">
              <button
                onClick={() => setViewMode("romanized")}
                className={`px-3 py-1 rounded-lg transition-all ${
                  viewMode === "romanized"
                    ? "bg-gradient-to-r from-indigo-600 to-cyan-500 text-white shadow-sm"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                Romanized (English)
              </button>
              <button
                onClick={() => setViewMode("original")}
                className={`px-3 py-1 rounded-lg transition-all ${
                  viewMode === "original"
                    ? "bg-gradient-to-r from-indigo-600 to-cyan-500 text-white shadow-sm"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                Original Script
              </button>
            </div>
          </div>
        )}

        {/* Content Body */}
        <div className="flex-1 p-6 overflow-y-auto space-y-4">
          {loading && (
            <div className="py-20 flex flex-col items-center justify-center text-center space-y-3">
              <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
              <p className="text-sm text-slate-400">Searching online for lyrics...</p>
            </div>
          )}

          {!loading && !data?.found && (
            <div className="py-20 flex flex-col items-center justify-center text-center space-y-3">
              <div className="w-16 h-16 rounded-2xl bg-slate-800/60 border border-white/5 flex items-center justify-center text-slate-500">
                <Music className="w-8 h-8 opacity-40" />
              </div>
              <p className="text-base font-semibold text-white">Lyrics Not Found</p>
              <p className="text-xs text-slate-400 max-w-sm">
                {data?.message || "Online lyrics are not available for this song title and artist."}
              </p>
            </div>
          )}

          {!loading && data?.found && (
            <div className="space-y-4">
              <div className="flex items-center justify-between text-xs text-slate-400 pb-2 border-b border-white/5">
                <span>
                  {viewMode === "romanized" && data.romanized
                    ? "Romanized English Lyrics"
                    : "Song Lyrics"}
                </span>
                <button
                  onClick={handleCopy}
                  className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors border border-white/5"
                >
                  <Copy className="w-3.5 h-3.5" />
                  {copied ? "Copied!" : "Copy Lyrics"}
                </button>
              </div>

              <pre className="font-sans text-sm md:text-base text-slate-200 leading-relaxed whitespace-pre-wrap select-text selection:bg-indigo-600 selection:text-white">
                {currentLyricsText}
              </pre>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-white/5 bg-slate-900/50 flex justify-end">
          <button
            onClick={onClose}
            className="px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-semibold text-xs border border-white/10 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

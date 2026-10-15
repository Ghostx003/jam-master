import React, { useEffect, useState } from "react";
import {
  Check,
  CheckCircle2,
  Cpu,
  Database,
  FolderTree,
  HardDrive,
  Info,
  Palette,
  RefreshCw,
  Save,
  Sliders,
} from "lucide-react";
import { fetchSettings, scanLibrary, updateSettings } from "../api";
import { SystemSettings } from "../types";

export const SettingsView: React.FC = () => {
  const [settingsData, setSettingsData] = useState<SystemSettings | null>(null);
  const [historyRatio, setHistoryRatio] = useState<number>(0.25);
  const [randomnessFactor, setRandomnessFactor] = useState<number>(0.0);
  const [customAimpPath, setCustomAimpPath] = useState<string>("");
  const [theme, setTheme] = useState<string>(
    () => localStorage.getItem("shuffle_master_theme") || "default"
  );
  const [isSaving, setIsSaving] = useState(false);
  const [isScanning, setIsScanning] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [sliderStatus, setSliderStatus] = useState<string | null>(null);

  const THEMES = [
    {
      id: "default",
      name: "Default Midnight",
      desc: "Deep navy slate with vibrant cyan and indigo accents.",
      colors: ["#0b0f19", "#06b6d4", "#6366f1"],
    },
    {
      id: "black-minimalist",
      name: "Pitch Black Minimalist (OLED)",
      desc: "Pure #000000 true black with clean monochrome styling.",
      colors: ["#000000", "#1a1a1a", "#ffffff"],
    },
    {
      id: "cyberpunk-neon",
      name: "Cyberpunk Neon",
      desc: "Ultra-dark void with electric neon cyan and hot pink accents.",
      colors: ["#060814", "#00f0ff", "#ff007f"],
    },
    {
      id: "emerald-matrix",
      name: "Emerald Matrix",
      desc: "Terminal obsidian with glowing emerald and mint accents.",
      colors: ["#040d08", "#10b981", "#34d399"],
    },
    {
      id: "sunset-velvet",
      name: "Sunset Velvet",
      desc: "Dark mahogany with radiant crimson rose and warm amber glow.",
      colors: ["#12070c", "#f43f5e", "#fb923c"],
    },
    {
      id: "nordic-frost",
      name: "Nordic Frost",
      desc: "Cold arctic slate with icy glacier cyan and steel blue accents.",
      colors: ["#070e17", "#38bdf8", "#7dd3fc"],
    },
    {
      id: "royal-amethyst",
      name: "Royal Amethyst",
      desc: "Deep nocturnal violet with radiant royal purple and lilac.",
      colors: ["#0b0717", "#a855f7", "#c084fc"],
    },
  ];

  const handleThemeChange = (newTheme: string) => {
    setTheme(newTheme);
    localStorage.setItem("shuffle_master_theme", newTheme);
    document.documentElement.className = document.documentElement.className
      .replace(/\btheme-[^\s]+\b/g, "")
      .trim();
    if (newTheme !== "default") {
      document.documentElement.classList.add(`theme-${newTheme}`);
    }
    const tObj = THEMES.find((t) => t.id === newTheme);
    setStatusMessage(`Theme switched to ${tObj?.name || newTheme}.`);
  };

  const loadSettings = async () => {
    try {
      const data = await fetchSettings();
      setSettingsData(data);
      setHistoryRatio(data.shuffle_config.history_ratio ?? 0.25);
      setRandomnessFactor(data.shuffle_config.randomness_factor ?? 0.0);
      setCustomAimpPath(data.settings.custom_aimp_path || data.player.executable_path || "");
    } catch (err: any) {
      setStatusMessage(`Error loading settings: ${err.message}`);
    }
  };

  useEffect(() => {
    loadSettings();
  }, []);

  const autoSaveSliders = async (h?: number, r?: number) => {
    const targetH = h !== undefined ? h : historyRatio;
    const targetR = r !== undefined ? r : randomnessFactor;
    setSliderStatus("Saving to algorithm in real time...");
    try {
      await updateSettings({
        history_ratio: targetH,
        randomness_factor: targetR,
        custom_aimp_path: customAimpPath.trim() || undefined,
      });
      setSliderStatus("Applied to shuffle algorithm in real time!");
      setTimeout(() => setSliderStatus(null), 3000);
    } catch (err: any) {
      setSliderStatus(`Failed to update: ${err.message}`);
      setTimeout(() => setSliderStatus(null), 4000);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setStatusMessage(null);
    try {
      await updateSettings({
        history_ratio: historyRatio,
        randomness_factor: randomnessFactor,
        custom_aimp_path: customAimpPath.trim() || undefined,
      });
      await loadSettings();
      setStatusMessage("All settings updated and saved successfully.");
    } catch (err: any) {
      setStatusMessage(`Failed to save settings: ${err.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  const handleFullRescan = async () => {
    setIsScanning(true);
    setStatusMessage("Rescanning all configured roots...");
    try {
      const res = await scanLibrary();
      await loadSettings();
      setStatusMessage(
        `Rescan complete: ${res.total_found} tracks (${res.new_or_updated} new/updated).`
      );
    } catch (err: any) {
      setStatusMessage(`Rescan failed: ${err.message}`);
    } finally {
      setIsScanning(false);
    }
  };

  return (
    <div className="flex-1 p-6 md:p-8 max-w-5xl mx-auto space-y-6 animate-in fade-in duration-200">
      {/* Top Header */}
      <div className="flex items-center justify-between pb-4 border-b border-white/5">
        <div>
          <span className="text-xs uppercase tracking-widest font-bold text-indigo-400">
            System & Engine
          </span>
          <h2 className="text-2xl font-bold text-white flex items-center gap-2 mt-0.5">
            Settings & Diagnostics
          </h2>
        </div>
      </div>

      {statusMessage && (
        <div className="p-3.5 rounded-xl bg-slate-800/80 border border-emerald-500/30 text-xs text-emerald-300 flex items-center justify-between shadow-lg">
          <span className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            {statusMessage}
          </span>
          <button onClick={() => setStatusMessage(null)} className="text-slate-400 hover:text-white">
            ✕
          </button>
        </div>
      )}

      {/* Main Settings Form */}
      <form onSubmit={handleSave} className="space-y-6">
        {/* Shuffle Engine Tuning */}
        <div className="bg-[#111827] border border-white/5 rounded-2xl p-6 space-y-6 shadow-xl">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-indigo-600/20 text-indigo-400 flex items-center justify-center">
                <Sliders className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white">Shuffle Algorithm Tuning</h3>
                <p className="text-xs text-slate-400">
                  Control how smart and randomized your music playback feels
                </p>
              </div>
            </div>

            {sliderStatus && (
              <span className="text-xs font-semibold px-2.5 py-1 rounded-lg bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 animate-pulse">
                {sliderStatus}
              </span>
            )}
          </div>

          {/* Slider 1: Anti-Repeat Exclusion Window */}
          <div className="space-y-2">
            <div className="flex justify-between items-center text-xs font-semibold">
              <span className="text-slate-200">
                1. Anti-Repeat Song Timeout:{" "}
                <span className="text-cyan-400 font-bold">{Math.round(historyRatio * 100)}%</span> of active pool
              </span>
              <span className="text-slate-500 font-mono text-[11px]">
                Range: 10% – 50%
              </span>
            </div>
            <input
              type="range"
              min="0.10"
              max="0.50"
              step="0.05"
              value={historyRatio}
              onChange={(e) => {
                const val = parseFloat(e.target.value);
                setHistoryRatio(val);
              }}
              onPointerUp={() => autoSaveSliders(historyRatio, randomnessFactor)}
              onKeyUp={() => autoSaveSliders(historyRatio, randomnessFactor)}
              className="w-full accent-cyan-500 bg-slate-800 h-2.5 rounded-lg cursor-pointer"
            />
            <div className="p-3 bg-slate-900/60 rounded-xl border border-white/5 text-xs space-y-1">
              <p className="text-slate-300 font-medium">
                💡 <span className="text-white font-semibold">In Plain English:</span> How long a song stays in cooldown before it can play again.
              </p>
              <p className="text-slate-400 text-[11px] leading-relaxed">
                If set to 25% on a 1,000 song library, the last 250 songs you heard are completely blocked from repeating. Slide lower to hear repeats sooner; slide higher to hear half your library before any track replays.
              </p>
            </div>
          </div>

          {/* Slider 2: Algorithm Randomness */}
          <div className="pt-4 border-t border-white/5 space-y-2">
            <div className="flex justify-between items-center text-xs font-semibold">
              <span className="text-slate-200">
                2. Algorithm Randomness:{" "}
                <span className="text-indigo-400 font-bold">
                  {Math.round(randomnessFactor * 100)}%
                </span>{" "}
                <span className="text-slate-400 font-normal">
                  ({randomnessFactor === 0
                    ? "Smart DJ: Full Anti-Repeat & Star Favorites"
                    : randomnessFactor >= 0.95
                    ? "Pure Coin-Flip Chaos"
                    : "Balanced Shuffle"})
                </span>
              </span>
              <span className="text-slate-500 font-mono text-[11px]">
                Range: 0% – 100%
              </span>
            </div>
            <input
              type="range"
              min="0.0"
              max="1.0"
              step="0.05"
              value={randomnessFactor}
              onChange={(e) => {
                const val = parseFloat(e.target.value);
                setRandomnessFactor(val);
              }}
              onPointerUp={() => autoSaveSliders(historyRatio, randomnessFactor)}
              onKeyUp={() => autoSaveSliders(historyRatio, randomnessFactor)}
              className="w-full accent-indigo-500 bg-slate-800 h-2.5 rounded-lg cursor-pointer"
            />
            <div className="flex justify-between text-[11px] text-slate-500 font-medium px-0.5">
              <span>0% Smart AI DJ</span>
              <span>50% Balanced</span>
              <span>100% Pure Random</span>
            </div>
            <div className="p-3 bg-slate-900/60 rounded-xl border border-white/5 text-xs space-y-1">
              <p className="text-slate-300 font-medium">
                💡 <span className="text-white font-semibold">In Plain English:</span> Smart recommendations vs pure random luck.
              </p>
              <p className="text-slate-400 text-[11px] leading-relaxed">
                <b className="text-slate-300">At 0% (Smart DJ):</b> Boosts your 5-star favorites, brings back unplayed tracks, and penalizes songs you skip.
                <br />
                <b className="text-slate-300">At 100% (Pure Random):</b> Every song has the exact same 50/50 probability like rolling dice, ignoring star ratings and play history.
              </p>
            </div>
          </div>

          {/* Quick Apply Button Right in Algorithm Box */}
          <div className="flex justify-end pt-1">
            <button
              type="button"
              onClick={() => autoSaveSliders(historyRatio, randomnessFactor)}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-md active:scale-95 transition-all"
            >
              <Save className="w-3.5 h-3.5" />
              Apply Algorithm Tuning
            </button>
          </div>
        </div>

        {/* Visual Appearance & Theme */}
        <div className="bg-[#111827] border border-white/5 rounded-2xl p-6 space-y-4 shadow-xl">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-indigo-600/20 text-indigo-400 flex items-center justify-center">
                <Palette className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white">Visual Themes (7 Options)</h3>
                <p className="text-xs text-slate-400">
                  Select your favorite atmosphere, color scheme, and aesthetic
                </p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5 pt-1">
            {THEMES.map((t) => {
              const isSelected = theme === t.id;
              return (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => handleThemeChange(t.id)}
                  className={`p-3.5 rounded-2xl border text-left transition-all relative flex flex-col justify-between h-28 group ${
                    isSelected
                      ? "bg-slate-900 border-indigo-500/80 shadow-lg shadow-indigo-600/20 ring-1 ring-indigo-500"
                      : "bg-slate-900/60 border-white/5 hover:border-white/20 hover:bg-slate-800/80"
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-bold text-xs text-white group-hover:text-cyan-300 transition-colors">
                        {t.name}
                      </span>
                      {isSelected && <Check className="w-3.5 h-3.5 text-cyan-400" />}
                    </div>
                    <p className="text-[11px] text-slate-400 line-clamp-2 leading-relaxed">
                      {t.desc}
                    </p>
                  </div>

                  <div className="flex items-center gap-1.5 pt-2">
                    {t.colors.map((c, idx) => (
                      <span
                        key={idx}
                        className="w-3.5 h-3.5 rounded-full border border-white/20 shadow-sm"
                        style={{ backgroundColor: c }}
                      />
                    ))}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Player & Executable Configuration */}
        <div className="bg-[#111827] border border-white/5 rounded-2xl p-6 space-y-5 shadow-xl">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-indigo-600/20 text-indigo-400 flex items-center justify-center">
              <Cpu className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white">AIMP Integration</h3>
              <p className="text-xs text-slate-400">
                Executable location and process command-line controller
              </p>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">
              AIMP Executable Path
            </label>
            <input
              type="text"
              placeholder="e.g. C:\Program Files\AIMP\AIMP.exe"
              value={customAimpPath}
              onChange={(e) => setCustomAimpPath(e.target.value)}
              className="w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-2.5 text-xs text-white placeholder-slate-500 font-mono focus:outline-none focus:border-indigo-500"
            />
            <p className="text-[11px] text-slate-500 mt-1.5">
              Auto-discovered from standard Windows directories, PATH, and registry by default.
            </p>
          </div>

          <div className="flex justify-end pt-2">
            <button
              type="submit"
              disabled={isSaving}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/30 active:scale-95 transition-all"
            >
              <Save className="w-3.5 h-3.5" />
              Save Settings
            </button>
          </div>
        </div>
      </form>

      {/* Diagnostics & System Card */}
      {settingsData && (
        <div className="bg-[#111827] border border-white/5 rounded-2xl p-6 space-y-4 shadow-xl">
          <div className="flex items-center justify-between pb-3 border-b border-white/5">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-indigo-600/20 text-indigo-400 flex items-center justify-center">
                <Database className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white">Application Diagnostics</h3>
                <p className="text-xs text-slate-400">Local persistent data and player state</p>
              </div>
            </div>

            <button
              onClick={handleFullRescan}
              disabled={isScanning}
              className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-medium border border-white/5"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isScanning ? "animate-spin text-cyan-400" : ""}`} />
              Force Rescan
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
            <div className="bg-slate-900/60 p-3.5 rounded-xl border border-white/5">
              <span className="text-slate-500 block mb-1">SQLite Database</span>
              <span className="font-mono text-white text-[11px] break-all">{settingsData.db_path}</span>
            </div>

            <div className="bg-slate-900/60 p-3.5 rounded-xl border border-white/5">
              <span className="text-slate-500 block mb-1">App Data Directory</span>
              <span className="font-mono text-white text-[11px] break-all">{settingsData.app_data_dir}</span>
            </div>

            <div className="bg-slate-900/60 p-3.5 rounded-xl border border-white/5">
              <span className="text-slate-500 block mb-1">Total Indexed Tracks</span>
              <span className="text-emerald-400 font-bold text-sm">{settingsData.total_tracks} available</span>
            </div>

            <div className="bg-slate-900/60 p-3.5 rounded-xl border border-white/5">
              <span className="text-slate-500 block mb-1">Total Playlists</span>
              <span className="text-cyan-400 font-bold text-sm">{settingsData.total_playlists} saved</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

import React from "react";
import {
  Compass,
  FolderTree,
  History,
  ListMusic,
  Radio,
  Settings as SettingsIcon,
  UploadCloud,
} from "lucide-react";
import { PlayerStatus } from "../types";

export type ViewTab =
  | "now-playing"
  | "library"
  | "playlists"
  | "history"
  | "import-export"
  | "settings";

interface Props {
  currentTab: ViewTab;
  onTabChange: (tab: ViewTab) => void;
  playerStatus?: PlayerStatus;
}

export const Navigation: React.FC<Props> = ({
  currentTab,
  onTabChange,
  playerStatus,
}) => {
  const navItems = [
    { id: "now-playing", label: "Now Playing", icon: Radio },
    { id: "playlists", label: "Playlists", icon: ListMusic },
    { id: "history", label: "Recently Played", icon: History },
    { id: "import-export", label: "Import / Export", icon: UploadCloud },
    { id: "library", label: "Music Library", icon: FolderTree },
    { id: "settings", label: "Settings", icon: SettingsIcon },
  ];

  return (
    <aside className="w-64 bg-[#0d1322] border-r border-white/5 flex flex-col justify-between p-4 shrink-0 h-screen sticky top-0">
      <div>
        {/* App Logo / Brand */}
        <div className="flex items-center gap-3 px-3 py-4 mb-6">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-cyan-500 flex items-center justify-center shadow-lg shadow-indigo-600/30">
            <Compass className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="font-bold text-base tracking-wide text-white">
              Shuffle Master
            </h1>
            <p className="text-[11px] text-cyan-400 font-medium">Local AIMP Edition</p>
          </div>
        </div>

        {/* Nav Links */}
        <nav className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onTabChange(item.id as ViewTab)}
                className={`w-full flex items-center gap-3.5 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all ${
                  isActive
                    ? "bg-indigo-600/15 text-indigo-400 border border-indigo-500/30 shadow-sm"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 border border-transparent"
                }`}
              >
                <Icon
                  className={`w-4 h-4 ${
                    isActive ? "text-indigo-400" : "text-slate-400 group-hover:text-slate-200"
                  }`}
                />
                {item.label}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Player Status Footer Card */}
      <div className="bg-slate-900/60 border border-white/5 rounded-2xl p-3.5 text-xs">
        <div className="flex items-center justify-between mb-2">
          <span className="text-slate-400 font-medium">AIMP Integration</span>
          <span
            className={`w-2 h-2 rounded-full ${
              playerStatus?.is_running
                ? "bg-emerald-400 shadow-sm shadow-emerald-400/50 animate-pulse"
                : playerStatus?.is_installed
                ? "bg-amber-400"
                : "bg-rose-400"
            }`}
          />
        </div>
        <div className="text-slate-300 font-medium flex items-center justify-between">
          <span>{playerStatus?.player_type || "AIMP"}</span>
          <span className="text-[11px] text-slate-400">
            {playerStatus?.is_running
              ? "Running"
              : playerStatus?.is_installed
              ? "Standby"
              : "Fallback"}
          </span>
        </div>
        {playerStatus?.last_error && (
          <p className="text-[10px] text-amber-400/80 mt-1.5 truncate" title={playerStatus.last_error}>
            {playerStatus.last_error}
          </p>
        )}
      </div>
    </aside>
  );
};

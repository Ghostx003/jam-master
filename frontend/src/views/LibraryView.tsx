import React, { useEffect, useState } from "react";
import {
  CheckSquare,
  FolderPlus,
  FolderTree,
  HardDrive,
  ListPlus,
  Loader2,
  Music,
  Play,
  Plus,
  RefreshCw,
  Search,
  Square,
  Trash2,
} from "lucide-react";
import {
  addRoot,
  addTracksToPlaylist,
  createPlaylist,
  fetchEligibleFolders,
  fetchPlaylists,
  fetchRoots,
  fetchTracks,
  pickFolderDialog,
  playFolders,
  playTrack,
  removeRoot,
  scanLibrary,
  setTrackRating,
} from "../api";
import { FolderSummary, MusicRoot, Playlist, Track } from "../types";
import { ArtworkImage } from "../components/ArtworkImage";
import { StarRating } from "../components/StarRating";
import { AddToPlaylistModal } from "../components/AddToPlaylistModal";

interface Props {
  onStateUpdate: () => void;
}

export const LibraryView: React.FC<Props> = ({ onStateUpdate }) => {
  const [roots, setRoots] = useState<MusicRoot[]>([]);
  const [folders, setFolders] = useState<FolderSummary[]>([]);
  const [selectedFolderPaths, setSelectedFolderPaths] = useState<Set<string>>(() => {
    try {
      const saved = localStorage.getItem("shuffle_master_selected_folders");
      if (saved) {
        const arr = JSON.parse(saved);
        if (Array.isArray(arr)) return new Set(arr);
      }
    } catch {}
    return new Set();
  });
  const [playlists, setPlaylists] = useState<Playlist[]>([]);
  const [targetTrack, setTargetTrack] = useState<{ id: number; title: string } | null>(null);
  const [isAddToPlaylistOpen, setIsAddToPlaylistOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchedTracks, setSearchedTracks] = useState<Track[]>([]);
  const [isScanning, setIsScanning] = useState(false);
  const [isPicking, setIsPicking] = useState(false);
  const [manualPath, setManualPath] = useState("");
  const [activeTab, setActiveTab] = useState<"folders" | "tracks">("folders");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  useEffect(() => {
    try {
      localStorage.setItem(
        "shuffle_master_selected_folders",
        JSON.stringify(Array.from(selectedFolderPaths))
      );
    } catch {}
  }, [selectedFolderPaths]);

  const loadData = async () => {
    try {
      const [r, f] = await Promise.all([fetchRoots(), fetchEligibleFolders()]);
      setRoots(r);
      setFolders(f);
    } catch (err: any) {
      setStatusMessage(`Error loading library: ${err.message}`);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Search tracks on query change
  useEffect(() => {
    if (searchQuery.trim().length > 1) {
      setActiveTab("tracks");
      fetchTracks({ q: searchQuery.trim(), limit: 100 })
        .then(setSearchedTracks)
        .catch(() => {});
    }
  }, [searchQuery]);

  const handlePickFolder = async () => {
    setIsPicking(true);
    setStatusMessage(null);
    try {
      const res = await pickFolderDialog();
      if (res.folder_path) {
        setStatusMessage(`Scanning selected folder: ${res.folder_path}`);
        await addRoot(res.folder_path);
        await loadData();
        setStatusMessage("Folder scanned and added to library successfully.");
      }
    } catch (err: any) {
      setStatusMessage(`Failed to pick folder: ${err.message}`);
    } finally {
      setIsPicking(false);
    }
  };

  const handleManualAddRoot = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualPath.trim()) return;
    setIsScanning(true);
    try {
      await addRoot(manualPath.trim());
      setManualPath("");
      await loadData();
      setStatusMessage("Folder added and indexed successfully.");
    } catch (err: any) {
      setStatusMessage(`Failed to add folder: ${err.message}`);
    } finally {
      setIsScanning(false);
    }
  };

  const handleRemoveRoot = async (rootId: number) => {
    try {
      await removeRoot(rootId);
      await loadData();
      setStatusMessage("Music root removed. Playlists and history preserved.");
    } catch (err: any) {
      setStatusMessage(`Failed to remove root: ${err.message}`);
    }
  };

  const handleScanLibrary = async () => {
    setIsScanning(true);
    setStatusMessage("Scanning all music roots for new and updated audio...");
    try {
      const res = await scanLibrary();
      await loadData();
      setStatusMessage(
        `Library refreshed: ${res.total_found} tracks found (${res.new_or_updated} new/updated, ${res.unavailable_marked} missing).`
      );
    } catch (err: any) {
      setStatusMessage(`Scan failed: ${err.message}`);
    } finally {
      setIsScanning(false);
    }
  };

  const toggleFolderSelection = (folderPath: string) => {
    setSelectedFolderPaths((prev) => {
      const next = new Set(prev);
      if (next.has(folderPath)) {
        next.delete(folderPath);
      } else {
        next.add(folderPath);
      }
      return next;
    });
  };

  const selectAllFolders = () => {
    if (selectedFolderPaths.size === folders.length) {
      setSelectedFolderPaths(new Set());
    } else {
      setSelectedFolderPaths(new Set(folders.map((f) => f.folder_path)));
    }
  };

  const handleStartJamming = async () => {
    const paths = Array.from(selectedFolderPaths);
    if (paths.length === 0) {
      setStatusMessage("Please select at least one folder to start jamming.");
      return;
    }
    try {
      await playFolders(paths);
      onStateUpdate();
    } catch (err: any) {
      setStatusMessage(`Playback error: ${err.message}`);
    }
  };

  const handlePlaySingleTrack = async (trackId: number) => {
    try {
      await playTrack(trackId);
      onStateUpdate();
    } catch (err: any) {
      setStatusMessage(`Playback error: ${err.message}`);
    }
  };

  const handleRate = async (trackId: number, rating: number) => {
    try {
      await setTrackRating(trackId, rating);
      setSearchedTracks((prev) =>
        prev.map((t) => (t.id === trackId ? { ...t, rating } : t))
      );
    } catch (err: any) {
      setStatusMessage(`Failed to set rating: ${err.message}`);
    }
  };

  const handleAddToPlaylistClick = async (track: { id: number; title: string }) => {
    try {
      const currentPlaylists = await fetchPlaylists();
      setPlaylists(currentPlaylists);

      if (currentPlaylists.length === 0) {
        const created = await createPlaylist("My Playlist");
        await addTracksToPlaylist(created.id, [track.id]);
        setStatusMessage(`Created 'My Playlist' and added "${track.title}".`);
      } else if (currentPlaylists.length === 1) {
        const pl = currentPlaylists[0];
        await addTracksToPlaylist(pl.id, [track.id]);
        setStatusMessage(`Added "${track.title}" to ${pl.name}.`);
      } else {
        setTargetTrack(track);
        setIsAddToPlaylistOpen(true);
      }
    } catch (err: any) {
      const msg = err.message || "";
      setStatusMessage(
        msg.toLowerCase().includes("already exists")
          ? "Song already exists in playlist."
          : `Failed to add track: ${msg}`
      );
    }
  };

  const handleConfirmAddToPlaylist = async (playlistId: number) => {
    if (!targetTrack) return;
    try {
      await addTracksToPlaylist(playlistId, [targetTrack.id]);
      const targetPl = playlists.find((p) => p.id === playlistId);
      setStatusMessage(`Added "${targetTrack.title}" to ${targetPl?.name || "playlist"}.`);
    } catch (err: any) {
      const msg = err.message || "";
      setStatusMessage(
        msg.toLowerCase().includes("already exists")
          ? "Song already exists in playlist."
          : `Failed to add track: ${msg}`
      );
    }
  };

  return (
    <div className="flex-1 p-8 max-w-6xl mx-auto space-y-6 animate-in fade-in duration-200">
      {/* Top Header Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-white/5">
        <div>
          <span className="text-xs uppercase tracking-widest font-bold text-indigo-400">
            Music Library
          </span>
          <h2 className="text-2xl font-bold text-white flex items-center gap-2 mt-0.5">
            Discover & Index
          </h2>
        </div>

        {/* Action Buttons: Native Windows Folder Picker & Rescan */}
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={handlePickFolder}
            disabled={isPicking}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-semibold text-sm shadow-lg shadow-indigo-600/30 active:scale-95 transition-all"
          >
            {isPicking ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <FolderPlus className="w-4 h-4" />
            )}
            Select Music Folder
          </button>

          <button
            onClick={handleScanLibrary}
            disabled={isScanning}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 text-sm font-medium border border-white/5 active:scale-95 transition-all"
          >
            <RefreshCw className={`w-4 h-4 ${isScanning ? "animate-spin text-cyan-400" : ""}`} />
            Refresh Library
          </button>
        </div>
      </div>

      {/* Status banner */}
      {statusMessage && (
        <div className="p-3.5 rounded-xl bg-slate-800/80 border border-indigo-500/30 text-xs text-indigo-300 flex items-center justify-between">
          <span>{statusMessage}</span>
          <button
            onClick={() => setStatusMessage(null)}
            className="text-slate-400 hover:text-white ml-2"
          >
            ✕
          </button>
        </div>
      )}

      {/* Configured Roots Section */}
      <div className="bg-[#111827]/60 border border-white/5 rounded-2xl p-5 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <HardDrive className="w-4 h-4 text-cyan-400" />
            Configured Music Roots ({roots.length})
          </h3>
        </div>

        {roots.length === 0 ? (
          <p className="text-xs text-slate-400">
            No music folders configured yet. Click "Select Music Folder" above to choose your music library.
          </p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {roots.map((root) => (
              <div
                key={root.id}
                className="bg-slate-900/60 border border-white/5 rounded-xl p-3.5 flex items-center justify-between group hover:border-white/10 transition-colors"
              >
                <div className="min-w-0 pr-3">
                  <p className="text-sm font-semibold text-white truncate">
                    {root.display_name}
                  </p>
                  <p className="text-[11px] text-slate-400 truncate" title={root.path}>
                    {root.path}
                  </p>
                </div>
                <button
                  onClick={() => handleRemoveRoot(root.id)}
                  title="Remove root from scanning"
                  className="p-1.5 text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-colors shrink-0"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Manual Path Entry Option */}
        <form onSubmit={handleManualAddRoot} className="flex gap-2 pt-2">
          <input
            type="text"
            placeholder="Or enter path manually (e.g. D:\MyMusic)..."
            value={manualPath}
            onChange={(e) => setManualPath(e.target.value)}
            className="flex-1 bg-slate-900 border border-white/10 rounded-xl px-4 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
          <button
            type="submit"
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-medium border border-white/5 shrink-0"
          >
            Add Path
          </button>
        </form>
      </div>

      {/* Search and Tabs */}
      <div className="flex flex-col md:flex-row items-center justify-between gap-4">
        {/* Search Input */}
        <div className="relative w-full md:w-96">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
          <input
            type="text"
            placeholder="Search by title, artist, album, or filename..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-[#111827] border border-white/10 rounded-xl pl-10 pr-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition-colors"
          />
        </div>

        {/* Tab Toggle */}
        <div className="flex items-center gap-2 bg-slate-900 p-1 rounded-xl border border-white/5">
          <button
            onClick={() => setActiveTab("folders")}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              activeTab === "folders"
                ? "bg-indigo-600 text-white"
                : "text-slate-400 hover:text-white"
            }`}
          >
            Folders ({folders.length})
          </button>
          <button
            onClick={() => setActiveTab("tracks")}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              activeTab === "tracks"
                ? "bg-indigo-600 text-white"
                : "text-slate-400 hover:text-white"
            }`}
          >
            Tracks Search
          </button>
        </div>
      </div>

      {/* Main Table View: Folders */}
      {activeTab === "folders" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <button
                onClick={selectAllFolders}
                className="flex items-center gap-2 text-xs font-medium text-slate-400 hover:text-white transition-colors"
              >
                {selectedFolderPaths.size === folders.length && folders.length > 0 ? (
                  <CheckSquare className="w-4 h-4 text-indigo-400" />
                ) : (
                  <Square className="w-4 h-4 text-slate-500" />
                )}
                Select All ({selectedFolderPaths.size}/{folders.length})
              </button>
            </div>

            {selectedFolderPaths.size > 0 && (
              <button
                onClick={handleStartJamming}
                className="flex items-center gap-2 px-5 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold shadow-lg shadow-cyan-600/30 active:scale-95 transition-all"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                Start Jamming ({selectedFolderPaths.size} folders)
              </button>
            )}
          </div>

          {folders.length === 0 ? (
            <div className="bg-[#111827]/40 border border-white/5 rounded-2xl p-12 text-center">
              <FolderTree className="w-12 h-12 text-slate-600 mx-auto mb-3" />
              <p className="text-white font-medium">No playable audio folders discovered yet.</p>
              <p className="text-xs text-slate-500 mt-1">
                Use the "Select Music Folder" button above to choose a directory containing audio files.
              </p>
            </div>
          ) : (
            <div className="bg-[#111827] border border-white/5 rounded-2xl overflow-hidden shadow-lg">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-900/80 border-b border-white/5 text-slate-400 text-xs">
                  <tr>
                    <th className="py-3 px-4 w-12 text-center">Select</th>
                    <th className="py-3 px-4 font-semibold">Folder Path / Name</th>
                    <th className="py-3 px-4 font-semibold text-right">Tracks</th>
                    <th className="py-3 px-4 font-semibold text-right">Duration</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5 text-slate-300">
                  {folders.map((f) => {
                    const isSelected = selectedFolderPaths.has(f.folder_path);
                    return (
                      <tr
                        key={f.folder_path}
                        onClick={() => toggleFolderSelection(f.folder_path)}
                        className={`hover:bg-white/[0.03] cursor-pointer transition-colors ${
                          isSelected ? "bg-indigo-600/10" : ""
                        }`}
                      >
                        <td className="py-3 px-4 text-center">
                          {isSelected ? (
                            <CheckSquare className="w-4 h-4 text-indigo-400 inline" />
                          ) : (
                            <Square className="w-4 h-4 text-slate-600 inline" />
                          )}
                        </td>
                        <td className="py-3 px-4">
                          <p className="font-semibold text-white">{f.display_name}</p>
                          <p className="text-xs text-slate-500 truncate max-w-xl">
                            {f.folder_path}
                          </p>
                        </td>
                        <td className="py-3 px-4 text-right font-medium text-emerald-400">
                          {f.track_count}
                        </td>
                        <td className="py-3 px-4 text-right text-xs text-slate-400">
                          {f.formatted_duration}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Tracks Search Tab */}
      {activeTab === "tracks" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>
              {searchedTracks.length} tracks matching "{searchQuery}"
            </span>
          </div>

          {searchedTracks.length === 0 ? (
            <div className="bg-[#111827]/40 border border-white/5 rounded-2xl p-8 text-center text-slate-500">
              <Music className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>No tracks found matching your query.</p>
            </div>
          ) : (
            <div className="bg-[#111827] border border-white/5 rounded-2xl overflow-hidden shadow-lg">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-900/80 border-b border-white/5 text-slate-400 text-xs">
                  <tr>
                    <th className="py-3 px-4 w-12">#</th>
                    <th className="py-3 px-4 font-semibold">Title</th>
                    <th className="py-3 px-4 font-semibold">Artist</th>
                    <th className="py-3 px-4 font-semibold">Album</th>
                    <th className="py-3 px-4 font-semibold text-center w-32">Rating</th>
                    <th className="py-3 px-4 font-semibold text-right">Duration</th>
                    <th className="py-3 px-4 text-center w-28">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5 text-slate-300">
                  {searchedTracks.map((t, idx) => (
                    <tr key={t.id} className="hover:bg-white/[0.03] transition-colors">
                      <td className="py-3 px-4 text-slate-500 text-xs">{idx + 1}</td>
                      <td className="py-3 px-4 flex items-center gap-3">
                        <ArtworkImage
                          trackId={t.id}
                          className="w-8 h-8 rounded-lg shrink-0"
                          iconClassName="w-4 h-4 text-indigo-400"
                        />
                        <span className="font-medium text-white">{t.display_title}</span>
                      </td>
                      <td className="py-3 px-4 text-slate-400 text-xs">
                        {t.display_artist || "--"}
                      </td>
                      <td className="py-3 px-4 text-slate-400 text-xs">
                        {t.album || "--"}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <StarRating
                          rating={t.rating || 0}
                          size="xs"
                          onRate={(r) => handleRate(t.id, r)}
                        />
                      </td>
                      <td className="py-3 px-4 text-right text-xs text-slate-400">
                        {t.display_duration}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <div className="flex items-center justify-center gap-1.5">
                          <button
                            onClick={() => handlePlaySingleTrack(t.id)}
                            className="p-1.5 bg-indigo-600/20 hover:bg-indigo-600 text-indigo-300 hover:text-white rounded-lg transition-colors inline-flex items-center justify-center"
                            title="Play Track"
                          >
                            <Play className="w-3.5 h-3.5 fill-current" />
                          </button>
                          <button
                            onClick={() =>
                              handleAddToPlaylistClick({
                                id: t.id,
                                title: t.display_title,
                              })
                            }
                            className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white rounded-lg transition-colors inline-flex items-center justify-center"
                            title="Add to Playlist"
                          >
                            <ListPlus className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      <AddToPlaylistModal
        isOpen={isAddToPlaylistOpen}
        trackTitle={targetTrack?.title || ""}
        playlists={playlists}
        onClose={() => setIsAddToPlaylistOpen(false)}
        onSelectPlaylist={handleConfirmAddToPlaylist}
      />
    </div>
  );
};

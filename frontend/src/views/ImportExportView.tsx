import React, { useEffect, useState } from "react";
import {
  AlertCircle,
  Archive,
  CheckCircle2,
  CheckSquare,
  Copy,
  Download,
  FileArchive,
  FolderOpen,
  FolderPlus,
  FolderSearch,
  Loader2,
  Package,
  Square,
  Upload,
} from "lucide-react";
import {
  commitImportZip,
  copyPlaylistFolder,
  exportPlaylistRar,
  exportPlaylists,
  fetchPlaylists,
  pickFolderDialog,
  previewImportZip,
} from "../api";
import { ImportPreview, Playlist } from "../types";

export const ImportExportView: React.FC = () => {
  const [activeTab, setActiveTab] = useState<"export" | "import">("export");
  const [playlists, setPlaylists] = useState<Playlist[]>([]);
  const [selectedPlaylistIds, setSelectedPlaylistIds] = useState<Set<number>>(new Set());

  // Import State
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [conflictPolicy, setConflictPolicy] = useState<string>("rename");
  const [relinkFolder, setRelinkFolder] = useState<string>("");
  const [isCommitting, setIsCommitting] = useState(false);
  const [importResult, setImportResult] = useState<any | null>(null);

  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    fetchPlaylists()
      .then(setPlaylists)
      .catch((err) => setErrorMessage(`Failed to fetch playlists: ${err.message}`));
  }, []);

  const toggleSelectPlaylist = (id: number) => {
    setSelectedPlaylistIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAllPlaylists = () => {
    if (selectedPlaylistIds.size === playlists.length) {
      setSelectedPlaylistIds(new Set());
    } else {
      setSelectedPlaylistIds(new Set(playlists.map((p) => p.id)));
    }
  };

  const handleExport = async () => {
    const ids = Array.from(selectedPlaylistIds);
    if (ids.length === 0) {
      setErrorMessage("Please select at least one playlist to export.");
      return;
    }
    setErrorMessage(null);
    setStatusMessage("Generating ZIP archive...");
    try {
      const blob = await exportPlaylists(ids);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `playlists_export_${Date.now()}.zip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      setStatusMessage(`Exported ${ids.length} playlist(s) successfully.`);
    } catch (err: any) {
      setErrorMessage(`Export failed: ${err.message}`);
    }
  };

  const [isOperating, setIsOperating] = useState(false);

  const handlePhysicalCopy = async (playlistId?: number) => {
    let targetId = playlistId;
    if (!targetId) {
      const ids = Array.from(selectedPlaylistIds);
      if (ids.length === 1) targetId = ids[0];
      else {
        setErrorMessage("Please select a playlist to copy physically.");
        return;
      }
    }

    try {
      setIsOperating(true);
      setErrorMessage(null);
      setStatusMessage("Opening Windows folder picker to choose destination...");
      const pickRes = await pickFolderDialog();
      if (!pickRes.folder_path) {
        setStatusMessage(null);
        setIsOperating(false);
        return;
      }

      setStatusMessage(`Copying audio files to '${pickRes.folder_path}'...`);
      const res = await copyPlaylistFolder(targetId, pickRes.folder_path);
      setStatusMessage(
        `Successfully copied ${res.copied_count} song(s) into folder '${res.destination_folder}'!`
      );
    } catch (err: any) {
      setErrorMessage(`Physical copy error: ${err.message}`);
    } finally {
      setIsOperating(false);
    }
  };

  const handleRarExport = async (playlistId?: number) => {
    let targetId = playlistId;
    if (!targetId) {
      const ids = Array.from(selectedPlaylistIds);
      if (ids.length === 1) targetId = ids[0];
      else {
        setErrorMessage("Please select a playlist to export as RAR.");
        return;
      }
    }

    try {
      setIsOperating(true);
      setErrorMessage(null);
      setStatusMessage("Opening Windows folder picker to choose destination for RAR...");
      const pickRes = await pickFolderDialog();
      if (!pickRes.folder_path) {
        setStatusMessage(null);
        setIsOperating(false);
        return;
      }

      setStatusMessage(`Packaging tracks into RAR archive in '${pickRes.folder_path}'...`);
      const res = await exportPlaylistRar(targetId, pickRes.folder_path);
      setStatusMessage(
        `Successfully created RAR archive '${res.archive_path}' with ${res.total_tracks} tracks!`
      );
    } catch (err: any) {
      setErrorMessage(`RAR export error: ${err.message}`);
    } finally {
      setIsOperating(false);
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setSelectedFile(file);
    setPreview(null);
    setImportResult(null);
    setErrorMessage(null);
    setIsPreviewing(true);

    try {
      const data = await previewImportZip(file);
      setPreview(data);
    } catch (err: any) {
      setErrorMessage(`Invalid archive: ${err.message}`);
    } finally {
      setIsPreviewing(false);
    }
  };

  const handlePickRelinkFolder = async () => {
    try {
      const res = await pickFolderDialog();
      if (res.folder_path) {
        setRelinkFolder(res.folder_path);
      }
    } catch (err: any) {
      setErrorMessage(`Failed to pick folder: ${err.message}`);
    }
  };

  const handleCommitImport = async () => {
    if (!selectedFile) return;
    setIsCommitting(true);
    setErrorMessage(null);
    try {
      const res = await commitImportZip(
        selectedFile,
        conflictPolicy,
        relinkFolder.trim() || undefined
      );
      setImportResult(res);
      setStatusMessage(`Successfully imported ${res.imported_playlists} playlist(s).`);
      // Refresh playlists
      fetchPlaylists().then(setPlaylists);
    } catch (err: any) {
      setErrorMessage(`Import commit failed: ${err.message}`);
    } finally {
      setIsCommitting(false);
    }
  };

  return (
    <div className="flex-1 p-8 max-w-5xl mx-auto space-y-6 animate-in fade-in duration-200">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-white/5">
        <div>
          <span className="text-xs uppercase tracking-widest font-bold text-indigo-400">
            Portability & Backup
          </span>
          <h2 className="text-2xl font-bold text-white flex items-center gap-2 mt-0.5">
            ZIP Import / Export
          </h2>
        </div>

        {/* Tab Toggle */}
        <div className="flex items-center gap-2 bg-slate-900 p-1 rounded-xl border border-white/5">
          <button
            onClick={() => setActiveTab("export")}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-colors ${
              activeTab === "export"
                ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/20"
                : "text-slate-400 hover:text-white"
            }`}
          >
            <Download className="w-3.5 h-3.5" />
            Export Playlists
          </button>
          <button
            onClick={() => setActiveTab("import")}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-colors ${
              activeTab === "import"
                ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/20"
                : "text-slate-400 hover:text-white"
            }`}
          >
            <Upload className="w-3.5 h-3.5" />
            Import Playlists
          </button>
        </div>
      </div>

      {statusMessage && (
        <div className="p-3.5 rounded-xl bg-slate-800/80 border border-emerald-500/30 text-xs text-emerald-300 flex items-center justify-between">
          <span className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            {statusMessage}
          </span>
          <button onClick={() => setStatusMessage(null)} className="text-slate-400 hover:text-white">
            ✕
          </button>
        </div>
      )}

      {errorMessage && (
        <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-xs text-rose-300 flex items-center justify-between">
          <span className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-400" />
            {errorMessage}
          </span>
          <button onClick={() => setErrorMessage(null)} className="text-slate-400 hover:text-white">
            ✕
          </button>
        </div>
      )}

      {/* EXPORT TAB */}
      {activeTab === "export" && (
        <div className="bg-[#111827] border border-white/5 rounded-2xl p-6 space-y-6 shadow-xl">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h3 className="text-base font-bold text-white">Select Playlists to Export or Copy</h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Export to ZIP manifest, physically copy audio files into a dedicated folder, or archive directly into a RAR file.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={selectAllPlaylists}
                className="flex items-center gap-2 text-xs font-medium text-slate-400 hover:text-white transition-colors mr-1"
              >
                {selectedPlaylistIds.size === playlists.length && playlists.length > 0 ? (
                  <CheckSquare className="w-4 h-4 text-indigo-400" />
                ) : (
                  <Square className="w-4 h-4 text-slate-600" />
                )}
                Select All ({selectedPlaylistIds.size}/{playlists.length})
              </button>

              {selectedPlaylistIds.size === 1 && (
                <>
                  <button
                    onClick={() => handlePhysicalCopy()}
                    disabled={isOperating}
                    title="Choose a destination folder to copy physical song files"
                    className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-indigo-300 font-semibold text-xs border border-indigo-500/30 active:scale-95 transition-all"
                  >
                    <FolderPlus className="w-3.5 h-3.5" />
                    Copy to Folder
                  </button>
                  <button
                    onClick={() => handleRarExport()}
                    disabled={isOperating}
                    title="Package playlist into a .rar file using WinRAR"
                    className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-purple-300 font-semibold text-xs border border-purple-500/30 active:scale-95 transition-all"
                  >
                    <Archive className="w-3.5 h-3.5" />
                    Save as RAR
                  </button>
                </>
              )}

              <button
                onClick={handleExport}
                disabled={selectedPlaylistIds.size === 0 || isOperating}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white font-semibold text-xs shadow-lg shadow-indigo-600/30 active:scale-95 transition-all"
              >
                <Download className="w-3.5 h-3.5" />
                Export to ZIP ({selectedPlaylistIds.size})
              </button>
            </div>
          </div>

          {playlists.length === 0 ? (
            <div className="p-12 text-center text-slate-500 text-xs">
              No playlists found in the database.
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-3 pt-2">
              {playlists.map((p) => {
                const isSelected = selectedPlaylistIds.has(p.id);
                return (
                  <div
                    key={p.id}
                    onClick={() => toggleSelectPlaylist(p.id)}
                    className={`p-4 rounded-xl border cursor-pointer transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
                      isSelected
                        ? "bg-indigo-600/15 border-indigo-500/40 text-white"
                        : "bg-slate-900/60 border-white/5 hover:border-white/10 text-slate-300"
                    }`}
                  >
                    <div className="flex items-center gap-3 min-w-0 pr-2">
                      <div className="text-slate-400 shrink-0">
                        {isSelected ? (
                          <CheckSquare className="w-4 h-4 text-indigo-400" />
                        ) : (
                          <Square className="w-4 h-4 text-slate-600" />
                        )}
                      </div>
                      <div className="min-w-0">
                        <p className="font-semibold text-sm truncate">{p.name}</p>
                        <p className="text-[11px] text-slate-500 truncate">
                          {p.track_count} tracks •{" "}
                          {p.total_duration > 0
                            ? `${Math.round(p.total_duration / 60)} mins`
                            : "0 mins"}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0 self-end sm:self-auto">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handlePhysicalCopy(p.id);
                        }}
                        disabled={isOperating}
                        title="Pick a location to make a physical copy of this playlist"
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-indigo-600/30 text-indigo-300 hover:text-white text-xs font-medium border border-indigo-500/20 active:scale-95 transition-all"
                      >
                        <FolderPlus className="w-3.5 h-3.5" />
                        Copy to Folder
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRarExport(p.id);
                        }}
                        disabled={isOperating}
                        title="Export this playlist as a .rar archive"
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-purple-600/30 text-purple-300 hover:text-white text-xs font-medium border border-purple-500/20 active:scale-95 transition-all"
                      >
                        <Archive className="w-3.5 h-3.5" />
                        Save as RAR
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Quick Info Feature Guide */}
          <div className="p-4 rounded-xl bg-slate-900/60 border border-white/5 text-xs text-slate-400 space-y-1.5">
            <p className="font-semibold text-slate-300">Export & Backup Features:</p>
            <ul className="list-disc list-inside space-y-1 text-[11px]">
              <li>
                <span className="text-indigo-300 font-medium">Physical Copy to Folder:</span> Opens a native Windows folder selector, creates a subfolder named after the playlist, and physically copy-pastes the song files there.
              </li>
              <li>
                <span className="text-purple-300 font-medium">Save as RAR:</span> Prompts for a folder and packages the playlist's music files directly into a <code className="text-white">.rar</code> archive via WinRAR.
              </li>
              <li>
                <span className="text-cyan-300 font-medium">ZIP Archive:</span> Backs up playlists into a portable, lightweight manifest ZIP that can be imported anytime.
              </li>
            </ul>
          </div>
        </div>
      )}

      {/* IMPORT TAB */}
      {activeTab === "import" && (
        <div className="bg-[#111827] border border-white/5 rounded-2xl p-6 space-y-6 shadow-xl">
          <div>
            <h3 className="text-base font-bold text-white">Import Playlists from ZIP Archive</h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Select a valid ZIP archive containing exported playlist manifests.
            </p>
          </div>

          {/* Upload Dropzone */}
          <div className="border-2 border-dashed border-white/10 hover:border-indigo-500/50 rounded-2xl p-8 text-center bg-slate-900/40 transition-colors">
            <input
              type="file"
              accept=".zip,application/zip"
              onChange={handleFileChange}
              id="zip-upload"
              className="hidden"
            />
            <label htmlFor="zip-upload" className="cursor-pointer block space-y-3">
              <div className="w-12 h-12 rounded-2xl bg-indigo-600/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center mx-auto">
                <FileArchive className="w-6 h-6" />
              </div>
              <div className="text-sm font-semibold text-white">
                {selectedFile ? selectedFile.name : "Click to select a ZIP archive"}
              </div>
              <p className="text-xs text-slate-500">
                Supports archives exported from Shuffle Master / JAM//ENGINE
              </p>
            </label>
          </div>

          {isPreviewing && (
            <div className="flex items-center justify-center gap-2 p-6 text-sm text-indigo-400">
              <Loader2 className="w-4 h-4 animate-spin" />
              Analyzing and verifying archive contents...
            </div>
          )}

          {/* Preview Details */}
          {preview && (
            <div className="space-y-6 pt-2">
              <div className="bg-slate-900/80 border border-white/5 rounded-xl p-4 flex flex-wrap items-center justify-between gap-4 text-xs">
                <div>
                  <span className="text-slate-400 font-medium">Archive Version:</span>{" "}
                  <span className="text-white font-semibold">{preview.format_version}</span>
                </div>
                <div>
                  <span className="text-slate-400 font-medium">Playlists:</span>{" "}
                  <span className="text-white font-semibold">{preview.playlist_count}</span>
                </div>
                <div>
                  <span className="text-slate-400 font-medium">Total Tracks:</span>{" "}
                  <span className="text-white font-semibold">{preview.total_tracks}</span>
                </div>
                <div>
                  <span className="text-slate-400 font-medium">Matched Locally:</span>{" "}
                  <span className="text-emerald-400 font-semibold">{preview.matched_tracks}</span>
                </div>
                <div>
                  <span className="text-slate-400 font-medium">Missing:</span>{" "}
                  <span className="text-amber-400 font-semibold">{preview.missing_tracks}</span>
                </div>
              </div>

              {/* Playlists in archive */}
              <div className="space-y-2">
                <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                  Playlists in Archive
                </h4>
                <div className="space-y-2">
                  {preview.playlists.map((pl, idx) => (
                    <div
                      key={idx}
                      className="bg-slate-900/50 border border-white/5 rounded-xl p-3 flex items-center justify-between"
                    >
                      <div>
                        <p className="font-semibold text-white text-sm flex items-center gap-2">
                          {pl.name}
                          {pl.has_name_conflict && (
                            <span className="text-[10px] px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 font-medium border border-amber-500/30">
                              Name Conflict
                            </span>
                          )}
                        </p>
                        <p className="text-[11px] text-slate-500">
                          {pl.track_count} tracks ({pl.matched_count} matched locally)
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Configuration: Conflict Policy & Relink Folder */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                <div>
                  <label className="block text-xs font-semibold text-slate-400 mb-1.5">
                    Duplicate Name Conflict Policy
                  </label>
                  <select
                    value={conflictPolicy}
                    onChange={(e) => setConflictPolicy(e.target.value)}
                    className="w-full bg-slate-900 border border-white/10 rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="rename">Rename duplicates (e.g. "Name (1)")</option>
                    <option value="replace">Replace existing playlists</option>
                    <option value="skip">Skip existing playlists</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-400 mb-1.5">
                    Relink Folder (Optional: if songs moved to a new drive/path)
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      placeholder="e.g. E:\Music or leave blank..."
                      value={relinkFolder}
                      onChange={(e) => setRelinkFolder(e.target.value)}
                      className="flex-1 bg-slate-900 border border-white/10 rounded-xl px-3.5 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                    />
                    <button
                      type="button"
                      onClick={handlePickRelinkFolder}
                      className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-medium border border-white/5 shrink-0"
                    >
                      Browse
                    </button>
                  </div>
                </div>
              </div>

              {/* Confirm Import Button */}
              <div className="flex justify-end pt-4 border-t border-white/5">
                <button
                  onClick={handleCommitImport}
                  disabled={isCommitting}
                  className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-semibold text-sm shadow-lg shadow-emerald-600/30 active:scale-95 transition-all"
                >
                  {isCommitting ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Upload className="w-4 h-4" />
                  )}
                  Commit Import
                </button>
              </div>
            </div>
          )}

          {/* Import Result Banner */}
          {importResult && (
            <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-xs text-emerald-300 space-y-1">
              <p className="font-semibold text-sm">Import Completed Successfully!</p>
              <p>Imported: {importResult.imported_playlists} playlist(s)</p>
              {importResult.skipped_playlists > 0 && (
                <p>Skipped: {importResult.skipped_playlists} conflicting playlist(s)</p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

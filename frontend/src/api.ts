import {
  FolderSummary,
  HistoryItem,
  ImportPreview,
  LyricsResponse,
  MusicRoot,
  PlaybackState,
  Playlist,
  PlaylistDetails,
  SystemSettings,
  Track,
} from "./types";

const API_BASE = "/api";

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`, options);
  if (!res.ok) {
    let errorMsg = `Request failed: ${res.status}`;
    try {
      const data = await res.json();
      if (data && data.detail) {
        errorMsg = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
      }
    } catch {
      // fallback
    }
    throw new Error(errorMsg);
  }
  return res.json();
}

// ----------------------------------------------------------------------------
// Playback API
// ----------------------------------------------------------------------------

export async function fetchPlaybackState(): Promise<PlaybackState> {
  return request<PlaybackState>("/playback/state");
}

export async function playbackNext(wasSkipped = false): Promise<PlaybackState> {
  return request<PlaybackState>(`/playback/next?was_skipped=${wasSkipped}`, {
    method: "POST",
  });
}

export async function playbackPrev(): Promise<PlaybackState> {
  return request<PlaybackState>("/playback/prev", { method: "POST" });
}

export async function playbackShuffleMore(): Promise<PlaybackState> {
  return request<PlaybackState>("/playback/shuffle-more", { method: "POST" });
}

export async function playbackPause(): Promise<{ success: boolean }> {
  return request<{ success: boolean }>("/playback/pause", { method: "POST" });
}

export async function playbackResume(): Promise<{ success: boolean }> {
  return request<{ success: boolean }>("/playback/resume", { method: "POST" });
}

export async function playbackSeek(position: number): Promise<{
  success: boolean;
  position: number;
  duration: number;
}> {
  return request("/playback/seek", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ position }),
  });
}

export async function playbackVolume(volume: number): Promise<{
  success: boolean;
  volume: number;
}> {
  return request("/playback/volume", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ volume }),
  });
}

export async function playbackRepeat(repeats: number): Promise<PlaybackState> {
  return request<PlaybackState>("/playback/repeat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repeats }),
  });
}

export async function playTrack(trackId: number): Promise<PlaybackState> {
  return request<PlaybackState>(`/playback/play-track/${trackId}`, { method: "POST" });
}

export async function playLibrary(folderPaths?: string[]): Promise<PlaybackState> {
  return request<PlaybackState>("/playback/play-library", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(folderPaths ? { folder_paths: folderPaths } : {}),
  });
}

export async function playFolders(folderPaths: string[]): Promise<PlaybackState> {
  return request<PlaybackState>("/playback/play-folders", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ folder_paths: folderPaths }),
  });
}

export async function playPlaylist(playlistId: number): Promise<PlaybackState> {
  return request<PlaybackState>(`/playback/play-playlist/${playlistId}`, {
    method: "POST",
  });
}

export async function fetchUpNext(limit?: number): Promise<Track[]> {
  const q = limit ? `?limit=${limit}` : "";
  const res = await request<{ up_next: Track[] }>(`/playback/up-next${q}`);
  return res.up_next;
}

export async function reshuffleUpNext(limit?: number): Promise<Track[]> {
  const q = limit ? `?limit=${limit}` : "";
  const res = await request<{ up_next: Track[] }>(`/playback/reshuffle-up-next${q}`, {
    method: "POST",
  });
  return res.up_next;
}

export async function fetchLyrics(artist: string, title: string): Promise<LyricsResponse> {
  const params = new URLSearchParams({ artist, title });
  return request<LyricsResponse>(`/lyrics?${params.toString()}`);
}

// ----------------------------------------------------------------------------
// Library API
// ----------------------------------------------------------------------------

export async function fetchRoots(): Promise<MusicRoot[]> {
  return request<MusicRoot[]>("/library/roots");
}

export async function addRoot(path: string, displayName?: string): Promise<MusicRoot> {
  return request<MusicRoot>("/library/roots", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path, display_name: displayName }),
  });
}

export async function removeRoot(rootId: number): Promise<{ success: boolean }> {
  return request<{ success: boolean }>(`/library/roots/${rootId}`, {
    method: "DELETE",
  });
}

export async function pickFolderDialog(): Promise<{ folder_path: string | null }> {
  return request<{ folder_path: string | null }>("/library/pick-folder", {
    method: "POST",
  });
}

export async function scanLibrary(rootId?: number): Promise<{
  total_found: number;
  new_or_updated: number;
  unavailable_marked: number;
}> {
  const url = rootId ? `/library/scan?root_id=${rootId}` : "/library/scan";
  return request(url, { method: "POST" });
}

export async function fetchEligibleFolders(): Promise<FolderSummary[]> {
  return request<FolderSummary[]>("/library/folders");
}

export async function fetchTracks(params?: {
  q?: string;
  folder?: string;
  limit?: number;
}): Promise<Track[]> {
  const query = new URLSearchParams();
  if (params?.q) query.set("q", params.q);
  if (params?.folder) query.set("folder", params.folder);
  if (params?.limit) query.set("limit", params.limit.toString());
  return request<Track[]>(`/library/tracks?${query.toString()}`);
}

export function getArtworkUrl(trackId: number): string {
  return `${API_BASE}/library/track/${trackId}/artwork`;
}

// ----------------------------------------------------------------------------
// Playlists API
// ----------------------------------------------------------------------------

export async function fetchPlaylists(): Promise<Playlist[]> {
  return request<Playlist[]>("/playlists");
}

export async function createPlaylist(name: string, description = ""): Promise<Playlist> {
  return request<Playlist>("/playlists", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, description }),
  });
}

export async function fetchPlaylistDetails(id: number): Promise<PlaylistDetails> {
  return request<PlaylistDetails>(`/playlists/${id}`);
}

export async function renamePlaylist(id: number, name: string): Promise<{ success: boolean }> {
  return request<{ success: boolean }>(`/playlists/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
}

export async function deletePlaylist(id: number): Promise<{ success: boolean }> {
  return request<{ success: boolean }>(`/playlists/${id}`, { method: "DELETE" });
}

export async function addTracksToPlaylist(
  playlistId: number,
  trackIds: number[]
): Promise<{ added_count: number }> {
  return request<{ added_count: number }>(`/playlists/${playlistId}/tracks`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ track_ids: trackIds }),
  });
}

export async function removePlaylistEntry(
  playlistId: number,
  entryId: number
): Promise<{ success: boolean }> {
  return request<{ success: boolean }>(`/playlists/${playlistId}/entries/${entryId}`, {
    method: "DELETE",
  });
}

export async function reorderPlaylist(
  playlistId: number,
  entryIds: number[]
): Promise<{ success: boolean }> {
  return request<{ success: boolean }>(`/playlists/${playlistId}/reorder`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ entry_ids: entryIds }),
  });
}

// ----------------------------------------------------------------------------
// History API
// ----------------------------------------------------------------------------

export async function fetchHistory(limit = 50): Promise<HistoryItem[]> {
  return request<HistoryItem[]>(`/history?limit=${limit}`);
}

// ----------------------------------------------------------------------------
// Import / Export API
// ----------------------------------------------------------------------------

export async function exportPlaylists(playlistIds: number[]): Promise<Blob> {
  const res = await fetch(`${API_BASE}/export`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ playlist_ids: playlistIds }),
  });
  if (!res.ok) {
    throw new Error(`Export failed: ${res.statusText}`);
  }
  return res.blob();
}

export async function previewImportZip(file: File): Promise<ImportPreview> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/import/preview`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || "Failed to preview ZIP archive.");
  }
  return res.json();
}

export async function commitImportZip(
  file: File,
  conflictPolicy = "rename",
  relinkRoot?: string
): Promise<{
  imported_playlists: number;
  skipped_playlists: number;
  playlists: Array<{ id: number; name: string; tracks_imported: number }>;
}> {
  const formData = new FormData();
  formData.append("file", file);

  const query = new URLSearchParams({ conflict_policy: conflictPolicy });
  if (relinkRoot) query.set("relink_root", relinkRoot);

  const res = await fetch(`${API_BASE}/import/commit?${query.toString()}`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || "Failed to import playlists.");
  }
  return res.json();
}

// ----------------------------------------------------------------------------
// Settings API
// ----------------------------------------------------------------------------

export async function fetchSettings(): Promise<SystemSettings> {
  return request<SystemSettings>("/settings");
}

export async function updateSettings(params: {
  history_ratio?: number;
  min_history_window?: number;
  max_history_window?: number;
  randomness_factor?: number;
  custom_aimp_path?: string;
}): Promise<{ status: string; shuffle_config: any }> {
  return request("/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
}

// ----------------------------------------------------------------------------
// Track Rating & New Capabilities API
// ----------------------------------------------------------------------------

export async function setTrackRating(
  trackId: number,
  rating: number
): Promise<{ success: boolean; track_id: number; rating: number }> {
  return request(`/tracks/${trackId}/rating`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rating }),
  });
}

export const rateTrack = setTrackRating;

export async function toggleWholeDeck(enable?: boolean): Promise<PlaybackState> {
  return request<PlaybackState>("/playback/toggle-whole-deck", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enable }),
  });
}

export async function generateRandomPlaylist(
  name: string,
  limit: number,
  folderPaths?: string[]
): Promise<PlaylistDetails> {
  return request<PlaylistDetails>("/playlists/generate-random", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, limit, folder_paths: folderPaths }),
  });
}

export async function refillPlaylist(
  playlistId: number,
  folderPaths?: string[]
): Promise<{ added_count: number; message: string; details: PlaylistDetails }> {
  return request(`/playlists/${playlistId}/refill`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ folder_paths: folderPaths }),
  });
}

export async function copyPlaylistFolder(
  playlistId: number,
  destinationFolder: string
): Promise<{
  success: boolean;
  playlist_name: string;
  destination_folder: string;
  copied_count: number;
  total_entries: number;
  skipped_count: number;
}> {
  return request("/export/playlist/copy-folder", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ playlist_id: playlistId, destination_folder: destinationFolder }),
  });
}

export async function exportPlaylistRar(
  playlistId: number,
  destinationFolder: string
): Promise<{
  success: boolean;
  playlist_name: string;
  archive_path: string;
  total_tracks: number;
  used_winrar: boolean;
}> {
  return request("/export/playlist/rar", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ playlist_id: playlistId, destination_folder: destinationFolder }),
  });
}

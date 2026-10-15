export interface Track {
  id: number;
  canonical_path: string;
  folder_path: string;
  filename: string;
  file_size: number;
  mtime: number;
  title: string | null;
  artist: string | null;
  album: string | null;
  genre: string | null;
  duration: number;
  display_title: string;
  display_artist: string;
  display_duration: string;
  play_count: number;
  last_played_at: number | null;
  skip_count: number;
  is_available: boolean;
  rating: number;
}

export interface PlayerStatus {
  player_type: string;
  executable_path: string | null;
  is_installed: boolean;
  is_running: boolean;
  last_error: string | null;
  aimp_connected?: boolean;
  position?: number;
  duration?: number;
  volume?: number;
  state?: string;
}

export interface PlaybackState {
  current_track: Track | null;
  mode: string;
  repeats_remaining: number;
  pool_size: number;
  deck_remaining: number;
  recent_history_size: number;
  context_name: string;
  player: PlayerStatus;
  shuffle_whole_deck?: boolean;
  position_seconds?: number;
  duration_seconds?: number;
  is_playing?: boolean;
  volume?: number;
  aimp_connected?: boolean;
  active_playlist_id?: number | null;
}

export interface MusicRoot {
  id: number;
  path: string;
  display_name: string;
  created_at: number;
  last_scanned_at: number | null;
}

export interface FolderSummary {
  folder_path: string;
  display_name: string;
  track_count: number;
  total_duration: number;
  formatted_duration: string;
}

export interface Playlist {
  id: number;
  name: string;
  description: string;
  created_at: number;
  updated_at: number;
  track_count: number;
  total_duration: number;
  target_capacity?: number | null;
}

export interface PlaylistEntry {
  id: number;
  playlist_id: number;
  track_id: number;
  position: number;
  added_at: number;
  track: Track | null;
}

export interface PlaylistDetails extends Playlist {
  entries: PlaylistEntry[];
}

export interface HistoryItem {
  history_id: number;
  played_at: number;
  was_skipped: boolean;
  track: Track;
}

export interface ImportPreviewPlaylist {
  name: string;
  description: string;
  track_count: number;
  matched_count: number;
  missing_count: number;
  has_name_conflict: boolean;
  data_file: string;
}

export interface ImportPreview {
  format_version: string;
  exported_at: number;
  playlist_count: number;
  total_tracks: number;
  matched_tracks: number;
  missing_tracks: number;
  playlists: ImportPreviewPlaylist[];
}

export interface SystemSettings {
  settings: Record<string, string>;
  shuffle_config: {
    history_ratio: number;
    min_history_window: number;
    max_history_window: number;
    discovery_boost: number;
    frequency_dampening: number;
    skip_penalty: number;
    min_skip_factor: number;
    skip_decay_plays: number;
    recency_half_life: number;
    max_recency_boost: number;
    randomness_factor?: number;
  };
  player: PlayerStatus;
  roots: MusicRoot[];
  app_data_dir: string;
  db_path: string;
  total_tracks: number;
  total_playlists: number;
}

export interface LyricsResponse {
  found: boolean;
  artist: string;
  title: string;
  lyrics: string | null;
  romanized: string | null;
  is_indic: boolean;
  message: string | null;
}

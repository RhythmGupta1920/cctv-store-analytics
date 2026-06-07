export interface Summary {
  camera_id: string
  unique_visitors: number
  total_events: number
  busiest_zone: string | null
  avg_dwell_sec: number
  anomalies_count: number
}

export interface Footfall {
  camera_id: string
  unique_visitors: number
  total_track_records: number
  duration_sec: number
  visitors: number[]
}

export interface ZoneStat {
  zone: string
  zone_label: string
  frame_count: number
  unique_visitors: number
  total_dwell_sec: number
}

export interface ZoneAnalytics {
  camera_id: string
  zones: ZoneStat[]
}

export interface ZoneEvent {
  event_type: 'zone_entered' | 'zone_exited'
  camera_id: string
  track_id: number
  zone: string
  zone_label: string
  timestamp_sec: number
  frame: number
  dwell_sec?: number | null
}

export interface TrackSummary {
  track_id: number
  zones_visited: string[]
  total_frames: number
  first_seen_sec: number
  last_seen_sec: number
}

export interface Anomaly {
  anomaly_type: string
  severity: 'low' | 'medium' | 'high'
  message: string
  track_id?: number | null
  zone?: string | null
  timestamp_sec?: number | null
  value?: number | null
}

export interface DashboardData {
  summary: Summary
  footfall: Footfall
  zones: ZoneAnalytics
  events: ZoneEvent[]
  tracks: TrackSummary[]
  anomalies: Anomaly[]
}

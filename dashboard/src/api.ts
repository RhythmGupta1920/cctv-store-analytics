import type {
  Anomaly,
  DashboardData,
  Footfall,
  Summary,
  TrackSummary,
  ZoneAnalytics,
  ZoneEvent,
} from './types'

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`)
  if (!response.ok) {
    throw new Error(`API error ${response.status}: ${path}`)
  }
  return response.json() as Promise<T>
}

export async function fetchDashboardData(): Promise<DashboardData> {
  const [summary, footfall, zones, events, tracks, anomalies] = await Promise.all([
    get<Summary>('/analytics/summary'),
    get<Footfall>('/analytics/footfall'),
    get<ZoneAnalytics>('/analytics/zones'),
    get<ZoneEvent[]>('/events'),
    get<TrackSummary[]>('/tracks'),
    get<Anomaly[]>('/anomalies'),
  ])

  return { summary, footfall, zones, events, tracks, anomalies }
}

export { API_BASE }

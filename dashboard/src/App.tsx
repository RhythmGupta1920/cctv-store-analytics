import { useEffect, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { fetchDashboardData } from './api'
import type { DashboardData } from './types'
import './index.css'

function StatCard({
  label,
  value,
  hint,
}: {
  label: string
  value: string | number
  hint?: string
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-5 backdrop-blur">
      <p className="text-sm text-slate-400">{label}</p>
      <p className="mt-2 text-3xl font-semibold text-white">{value}</p>
      {hint ? <p className="mt-1 text-xs text-slate-500">{hint}</p> : null}
    </div>
  )
}

function severityColor(severity: string) {
  if (severity === 'high') return 'text-red-400 bg-red-400/10 border-red-400/20'
  if (severity === 'medium') return 'text-amber-400 bg-amber-400/10 border-amber-400/20'
  return 'text-sky-400 bg-sky-400/10 border-sky-400/20'
}

export default function App() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true

    async function load() {
      try {
        const next = await fetchDashboardData()
        if (active) {
          setData(next)
          setError(null)
        }
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : 'Failed to load dashboard')
        }
      } finally {
        if (active) setLoading(false)
      }
    }

    load()
    const timer = window.setInterval(load, 5000)
    return () => {
      active = false
      window.clearInterval(timer)
    }
  }, [])

  const chartData =
    data?.zones.zones.map((zone) => ({
      name: zone.zone_label.split(' ')[0],
      fullName: zone.zone_label,
      visitors: zone.unique_visitors,
      dwell: zone.total_dwell_sec,
    })) ?? []

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_#1e293b_0%,_#0b0f17_45%)] px-6 py-8">
      <div className="mx-auto max-w-7xl">
        <header className="mb-8 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.2em] text-violet-300">
              Store Intelligence
            </p>
            <h1 className="text-3xl font-bold text-white md:text-4xl">
              Brigade Bangalore — Live Analytics
            </h1>
            <p className="mt-2 text-slate-400">
              CCTV pipeline → tracking → zones → API → dashboard
            </p>
          </div>
          <div className="rounded-full border border-emerald-400/20 bg-emerald-400/10 px-4 py-2 text-sm text-emerald-300">
            {loading ? 'Connecting…' : error ? 'API offline' : 'Live · refreshes every 5s'}
          </div>
        </header>

        {error ? (
          <div className="mb-6 rounded-2xl border border-red-400/20 bg-red-400/10 p-5 text-red-200">
            <p className="font-medium">Could not reach the API</p>
            <p className="mt-2 text-sm">{error}</p>
            <p className="mt-3 text-sm text-red-100/80">
              Start the backend first:{' '}
              <code className="rounded bg-black/30 px-2 py-1">
                uvicorn api.main:app --reload --port 8000
              </code>
            </p>
          </div>
        ) : null}

        {data ? (
          <>
            <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <StatCard
                label="Unique visitors"
                value={data.summary.unique_visitors}
                hint={`Track IDs: ${data.footfall.visitors.join(', ')}`}
              />
              <StatCard
                label="Zone events"
                value={data.summary.total_events}
                hint={`Camera: ${data.summary.camera_id}`}
              />
              <StatCard
                label="Busiest zone"
                value={data.summary.busiest_zone ?? '—'}
                hint="Highest frame occupancy"
              />
              <StatCard
                label="Anomalies"
                value={data.summary.anomalies_count}
                hint={`Avg dwell ${data.summary.avg_dwell_sec}s`}
              />
            </section>

            <section className="mt-6 grid gap-6 xl:grid-cols-3">
              <div className="rounded-2xl border border-white/10 bg-white/5 p-5 xl:col-span-2">
                <h2 className="mb-4 text-lg font-semibold text-white">Zone activity</h2>
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                      <XAxis dataKey="name" stroke="#94a3b8" />
                      <YAxis stroke="#94a3b8" />
                      <Tooltip
                        contentStyle={{
                          background: '#111827',
                          border: '1px solid #334155',
                          borderRadius: '12px',
                        }}
                      />
                      <Bar dataKey="dwell" fill="#8b5cf6" name="Dwell (sec)" radius={[8, 8, 0, 0]} />
                      <Bar dataKey="visitors" fill="#22d3ee" name="Visitors" radius={[8, 8, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
                <h2 className="mb-4 text-lg font-semibold text-white">Alerts</h2>
                <div className="space-y-3">
                  {data.anomalies.length === 0 ? (
                    <p className="text-sm text-slate-400">No anomalies detected.</p>
                  ) : (
                    data.anomalies.map((item, index) => (
                      <div
                        key={`${item.anomaly_type}-${index}`}
                        className={`rounded-xl border px-4 py-3 text-sm ${severityColor(item.severity)}`}
                      >
                        <p className="font-medium capitalize">{item.anomaly_type.replace('_', ' ')}</p>
                        <p className="mt-1 opacity-90">{item.message}</p>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </section>

            <section className="mt-6 grid gap-6 xl:grid-cols-2">
              <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
                <h2 className="mb-4 text-lg font-semibold text-white">Recent zone events</h2>
                <div className="overflow-x-auto">
                  <table className="min-w-full text-left text-sm">
                    <thead className="text-slate-400">
                      <tr>
                        <th className="pb-3 pr-4">Time</th>
                        <th className="pb-3 pr-4">Event</th>
                        <th className="pb-3 pr-4">Track</th>
                        <th className="pb-3">Zone</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.events.map((event, index) => (
                        <tr key={`${event.frame}-${event.track_id}-${index}`} className="border-t border-white/5">
                          <td className="py-3 pr-4 text-slate-300">{event.timestamp_sec.toFixed(1)}s</td>
                          <td className="py-3 pr-4 capitalize text-violet-300">
                            {event.event_type.replace('_', ' ')}
                          </td>
                          <td className="py-3 pr-4">#{event.track_id}</td>
                          <td className="py-3">{event.zone_label}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
                <h2 className="mb-4 text-lg font-semibold text-white">Visitor journeys</h2>
                <div className="space-y-4">
                  {data.tracks.map((track) => (
                    <div
                      key={track.track_id}
                      className="rounded-xl border border-white/10 bg-black/20 p-4"
                    >
                      <div className="flex items-center justify-between">
                        <p className="font-medium text-white">Visitor #{track.track_id}</p>
                        <p className="text-xs text-slate-400">
                          {track.first_seen_sec.toFixed(1)}s – {track.last_seen_sec.toFixed(1)}s
                        </p>
                      </div>
                      <p className="mt-2 text-sm text-slate-300">
                        Zones: {track.zones_visited.join(' → ') || 'none'}
                      </p>
                      <p className="mt-1 text-xs text-slate-500">
                        {track.total_frames} tracked frames
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </section>
          </>
        ) : loading ? (
          <div className="rounded-2xl border border-white/10 bg-white/5 p-10 text-center text-slate-400">
            Loading dashboard…
          </div>
        ) : null}
      </div>
    </div>
  )
}

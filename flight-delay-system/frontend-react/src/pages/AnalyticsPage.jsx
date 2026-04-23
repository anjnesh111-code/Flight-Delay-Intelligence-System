import { useEffect, useMemo, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { getAirlinePerformance } from '../api/client'
import LoadingState from '../components/LoadingState'
import ErrorAlert from '../components/ErrorAlert'

export default function AnalyticsPage() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [analytics, setAnalytics] = useState(null)

  useEffect(() => {
    async function loadAnalytics() {
      setLoading(true)
      setError('')
      try {
        const data = await getAirlinePerformance()
        setAnalytics(data)
      } catch (requestError) {
        const apiMessage =
          requestError?.response?.data?.message || requestError?.response?.data?.detail || requestError.message
        setError(apiMessage || 'Unable to load analytics.')
      } finally {
        setLoading(false)
      }
    }
    loadAnalytics()
  }, [])

  const hourlyData = useMemo(() => {
    const rows = analytics?.hourly_heatmap || []
    const byHour = rows.reduce((acc, row) => {
      const hour = Number(row.dep_hour)
      const delay = Number(row.avg_delay)
      if (!acc[hour]) {
        acc[hour] = { dep_hour: hour, total: 0, count: 0 }
      }
      acc[hour].total += delay
      acc[hour].count += 1
      return acc
    }, {})
    return Object.values(byHour)
      .map((row) => ({ dep_hour: row.dep_hour, avg_delay: Number((row.total / row.count).toFixed(2)) }))
      .sort((a, b) => a.dep_hour - b.dep_hour)
  }, [analytics])

  const airlineData = useMemo(
    () => [...(analytics?.airline_performance || [])].sort((a, b) => Number(b.on_time_pct) - Number(a.on_time_pct)),
    [analytics],
  )

  const routeData = useMemo(
    () => [...(analytics?.top_delayed_routes || [])].sort((a, b) => Number(b.avg_delay) - Number(a.avg_delay)),
    [analytics],
  )

  if (loading) return <LoadingState label="Loading airline analytics..." />
  if (error) return <ErrorAlert message={error} />
  if (!analytics) return null

  return (
    <div className="space-y-5">
      <section className="grid gap-4 md:grid-cols-2">
        <InsightCard title="🏆 Best airline today" value={analytics.best_airline_today || 'N/A'} />
        <InsightCard title="⚠️ Worst airline today" value={analytics.worst_airline_today || 'N/A'} />
      </section>

      <ChartCard title="Average Delay by Departure Hour">
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={hourlyData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="dep_hour" stroke="#94a3b8" />
            <YAxis stroke="#94a3b8" />
            <Tooltip />
            <Legend />
            <Bar dataKey="avg_delay" name="Avg delay (min)" fill="#6366f1" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard title="Airline On-time Performance">
        <ResponsiveContainer width="100%" height={330}>
          <BarChart data={airlineData} layout="vertical" margin={{ left: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis type="number" stroke="#94a3b8" />
            <YAxis dataKey="airline_iata" type="category" width={70} stroke="#94a3b8" />
            <Tooltip />
            <Legend />
            <Bar dataKey="on_time_pct" name="On-time %" radius={[0, 6, 6, 0]}>
              {airlineData.map((entry) => (
                <Cell key={entry.airline_iata} fill={entry.ranking <= 3 ? '#10b981' : '#3b82f6'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard title="Top 10 Most-Delayed Routes">
        <ResponsiveContainer width="100%" height={330}>
          <BarChart data={routeData} layout="vertical" margin={{ left: 40 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis type="number" stroke="#94a3b8" />
            <YAxis dataKey="route" type="category" width={90} stroke="#94a3b8" />
            <Tooltip />
            <Legend />
            <Bar dataKey="avg_delay" name="Average delay (min)" fill="#f97316" radius={[0, 6, 6, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>
    </div>
  )
}

function InsightCard({ title, value }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4 shadow-lg shadow-black/20">
      <p className="text-sm text-slate-400">{title}</p>
      <p className="mt-2 text-2xl font-bold text-white">{value}</p>
    </div>
  )
}

function ChartCard({ title, children }) {
  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900 p-4 shadow-lg shadow-black/20">
      <h2 className="mb-3 text-lg font-semibold text-white">{title}</h2>
      {children}
    </section>
  )
}


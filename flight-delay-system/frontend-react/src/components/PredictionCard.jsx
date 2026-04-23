import { probabilityColor, riskBadgeClass, sourceBadgeClass } from '../utils/format'

export default function PredictionCard({ result }) {
  const probability = Number(result.delay_probability || 0)
  const progressClass = probabilityColor(probability)
  const riskClass = riskBadgeClass(result.risk_level)
  const sourceClass = sourceBadgeClass(result.data_source)
  const probabilityPct = Math.max(0, Math.min(100, probability * 100))

  return (
    <section className="space-y-4 rounded-2xl border border-slate-800 bg-slate-900 p-5 shadow-lg shadow-black/20">
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="text-xl font-semibold text-white">Prediction Result</h2>
        <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ${sourceClass}`}>
          {result.data_source === 'live' ? 'Live data' : 'Simulated data'}
        </span>
      </div>

      <div className="h-3 overflow-hidden rounded-full bg-slate-800">
        <div className={`h-full ${progressClass}`} style={{ width: `${probabilityPct.toFixed(1)}%` }} />
      </div>
      <p className="text-sm text-slate-300">Delay probability: {probabilityPct.toFixed(1)}%</p>

      <div className="grid gap-3 md:grid-cols-3">
        <Metric title="Expected delay" value={`${result.expected_delay_minutes ?? 0} min`} />
        <Metric title="Traffic condition" value={(result.traffic_condition || 'low').toUpperCase()} />
        <Metric title="Model confidence" value={`${((result.confidence_score || 0) * 100).toFixed(0)}%`} />
      </div>

      <div className="rounded-xl border border-slate-700 bg-slate-950 p-4">
        <div className="mb-2 flex items-center gap-2">
          <span className="text-lg">🧠</span>
          <h3 className="font-semibold text-white">Decision Engine</h3>
          <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ${riskClass}`}>
            Risk: {(result.risk_level || 'low').toUpperCase()}
          </span>
        </div>
        <p className="text-sm text-slate-200">{result.recommendation}</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-xl border border-slate-700 bg-slate-950 p-4">
          <h3 className="mb-2 font-semibold text-white">📌 Primary reasons</h3>
          <div className="flex flex-wrap gap-2">
            {(result.reasons || []).map((reason) => (
              <span key={reason} className="rounded-full bg-slate-800 px-3 py-1 text-xs text-slate-200">
                {reason}
              </span>
            ))}
          </div>
        </div>

        <div className="rounded-xl border border-slate-700 bg-slate-950 p-4">
          <h3 className="mb-2 font-semibold text-white">🌤 Weather</h3>
          <p className="text-sm text-slate-300">
            Condition: <span className="font-medium text-white">{result.weather?.condition || 'unknown'}</span>
          </p>
          <p className="text-sm text-slate-300">
            Wind: <span className="font-medium text-white">{result.weather?.wind_kph ?? 0} kph</span>
          </p>
          <p className="text-sm text-slate-300">
            Visibility: <span className="font-medium text-white">{result.weather?.visibility_km ?? 0} km</span>
          </p>
        </div>
      </div>

      <details className="rounded-xl border border-slate-700 bg-slate-950 p-4">
        <summary className="cursor-pointer font-semibold text-white">🔍 Why this prediction?</summary>
        <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-slate-300">
          {(result.top_factors || []).map((factor) => (
            <li key={factor}>{factor}</li>
          ))}
        </ul>
      </details>
    </section>
  )
}

function Metric({ title, value }) {
  return (
    <div className="rounded-xl border border-slate-700 bg-slate-950 p-3">
      <p className="text-xs uppercase tracking-wide text-slate-400">{title}</p>
      <p className="mt-1 text-lg font-semibold text-white">{value}</p>
    </div>
  )
}


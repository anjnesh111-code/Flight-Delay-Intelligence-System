import { useMemo, useState } from 'react'
import { predictFlight } from '../api/client'
import LoadingState from '../components/LoadingState'
import ErrorAlert from '../components/ErrorAlert'
import PredictionCard from '../components/PredictionCard'

const EXAMPLE_FLIGHTS = ['AA123', 'UA456', 'DL789']

export default function PredictPage() {
  const [flightNumber, setFlightNumber] = useState('AA123')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [prediction, setPrediction] = useState(null)

  const canSubmit = useMemo(() => /^[A-Z0-9]{2,3}\d{1,4}$/i.test(flightNumber), [flightNumber])

  async function onPredict(event) {
    event.preventDefault()
    if (!canSubmit) {
      setError('Enter a valid flight number like AA123.')
      return
    }
    setLoading(true)
    setError('')
    try {
      const data = await predictFlight(flightNumber.toUpperCase())
      setPrediction(data)
    } catch (requestError) {
      const apiMessage =
        requestError?.response?.data?.message || requestError?.response?.data?.detail || requestError.message
      setError(apiMessage || 'Prediction request failed.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-5">
      <section className="rounded-2xl border border-slate-800 bg-slate-900 p-5 shadow-lg shadow-black/20">
        <h2 className="text-xl font-semibold text-white">Flight lookup</h2>
        <p className="mt-1 text-sm text-slate-400">Search a flight and get actionable delay guidance in real time.</p>
        <form className="mt-4 space-y-3" onSubmit={onPredict}>
          <div className="flex flex-col gap-3 md:flex-row">
            <input
              type="text"
              value={flightNumber}
              onChange={(event) => setFlightNumber(event.target.value.toUpperCase())}
              placeholder="AA123"
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-2 text-sm text-white outline-none ring-indigo-500 placeholder:text-slate-500 focus:ring-2"
            />
            <button
              type="submit"
              disabled={loading}
              className="rounded-lg bg-indigo-600 px-5 py-2 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? 'Predicting...' : 'Predict Delay'}
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            {EXAMPLE_FLIGHTS.map((example) => (
              <button
                key={example}
                type="button"
                onClick={() => setFlightNumber(example)}
                className="rounded-full border border-slate-700 bg-slate-950 px-3 py-1 text-xs text-slate-300 transition hover:border-indigo-400 hover:text-white"
              >
                {example}
              </button>
            ))}
          </div>
        </form>
      </section>

      {loading && <LoadingState label="Fetching prediction from FastAPI..." />}
      {error && <ErrorAlert message={error} />}
      {prediction && <PredictionCard result={prediction} />}
    </div>
  )
}


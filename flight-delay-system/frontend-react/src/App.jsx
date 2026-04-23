import { NavLink, Route, Routes } from 'react-router-dom'
import PredictPage from './pages/PredictPage'
import AnalyticsPage from './pages/AnalyticsPage'

const navClass = ({ isActive }) =>
  `rounded-lg px-3 py-2 text-sm font-medium transition ${
    isActive ? 'bg-indigo-600 text-white' : 'text-slate-300 hover:bg-slate-800 hover:text-white'
  }`

export default function App() {
  return (
    <div className="mx-auto flex min-h-screen w-full max-w-7xl flex-col px-4 py-6 md:px-8">
      <header className="mb-6 rounded-2xl border border-slate-800 bg-slate-900/80 p-5 shadow-lg shadow-black/20">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white md:text-3xl">Flight Delay Decision Intelligence</h1>
            <p className="mt-1 text-sm text-slate-400">Real-time prediction, explainability, and action guidance</p>
          </div>
          <nav className="flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-950 p-1">
            <NavLink to="/" end className={navClass}>
              Predict
            </NavLink>
            <NavLink to="/analytics" className={navClass}>
              Analytics
            </NavLink>
          </nav>
        </div>
      </header>

      <main className="pb-8">
        <Routes>
          <Route path="/" element={<PredictPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
        </Routes>
      </main>
    </div>
  )
}


export default function LoadingState({ label }) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-slate-700 bg-slate-900 p-4 text-sm text-slate-300">
      <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-indigo-400 border-r-transparent" />
      <span>{label}</span>
    </div>
  )
}


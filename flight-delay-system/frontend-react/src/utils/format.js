export function probabilityColor(probability) {
  if (probability < 0.3) return 'bg-emerald-500'
  if (probability < 0.6) return 'bg-amber-400'
  return 'bg-rose-500'
}

export function riskBadgeClass(riskLevel) {
  if (riskLevel === 'low') return 'bg-emerald-500/20 text-emerald-300 ring-emerald-400/40'
  if (riskLevel === 'medium') return 'bg-amber-500/20 text-amber-300 ring-amber-400/40'
  return 'bg-rose-500/20 text-rose-300 ring-rose-400/40'
}

export function sourceBadgeClass(source) {
  return source === 'live'
    ? 'bg-sky-500/20 text-sky-300 ring-sky-400/40'
    : 'bg-violet-500/20 text-violet-300 ring-violet-400/40'
}


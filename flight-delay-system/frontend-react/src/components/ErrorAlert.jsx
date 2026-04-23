export default function ErrorAlert({ message }) {
  return (
    <div className="rounded-xl border border-rose-500/50 bg-rose-500/10 p-4 text-sm text-rose-200">
      <p className="font-semibold">Request failed</p>
      <p className="mt-1">{message}</p>
    </div>
  )
}


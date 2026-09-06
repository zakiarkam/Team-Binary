/**
 * Route-level loading state. Every dashboard page is force-dynamic and waits
 * on the API, so navigation shows this skeleton instead of a frozen screen.
 */
export default function Loading() {
  return (
    <div className="mx-auto max-w-6xl animate-pulse">
      <div className="mb-6">
        <div className="h-3 w-24 rounded bg-slate-200" />
        <div className="mt-2 h-7 w-56 rounded bg-slate-200" />
        <div className="mt-2 h-3 w-80 rounded bg-slate-100" />
      </div>
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="card">
            <div className="h-3 w-20 rounded bg-slate-200" />
            <div className="mt-3 h-8 w-16 rounded bg-slate-200" />
          </div>
        ))}
      </div>
      <div className="card mt-4">
        <div className="h-3 w-32 rounded bg-slate-200" />
        <div className="mt-4 h-48 rounded bg-slate-100" />
      </div>
      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        {Array.from({ length: 2 }).map((_, i) => (
          <div key={i} className="card">
            <div className="h-3 w-28 rounded bg-slate-200" />
            <div className="mt-4 h-40 rounded bg-slate-100" />
          </div>
        ))}
      </div>
    </div>
  );
}

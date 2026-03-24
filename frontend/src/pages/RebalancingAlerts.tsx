import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAlerts } from '../hooks/useAlerts'
import { LoadingSpinner } from '../components/common/LoadingSpinner'
import { ErrorMessage } from '../components/common/ErrorMessage'
import { Pagination } from '../components/common/Pagination'

const TYPE_LABELS: Record<string, { label: string; cls: string }> = {
  added: { label: 'Added', cls: 'bg-green-100 text-green-800' },
  removed: { label: 'Removed', cls: 'bg-red-100 text-red-800' },
  weight_change: { label: 'Weight Δ', cls: 'bg-yellow-100 text-yellow-800' },
}

export function RebalancingAlerts() {
  const [page, setPage] = useState(1)
  const [etfFilter, setEtfFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [etfInput, setEtfInput] = useState('')

  const { data, isLoading, isError } = useAlerts(page, 50, etfFilter, typeFilter)

  function applyEtfFilter(e: React.FormEvent) {
    e.preventDefault()
    setEtfFilter(etfInput.toUpperCase())
    setPage(1)
  }

  function clearFilters() {
    setEtfFilter('')
    setEtfInput('')
    setTypeFilter('')
    setPage(1)
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Rebalancing Alerts</h1>
        <p className="text-sm text-gray-500 mt-1">
          Component additions, removals, and significant weight changes across all tracked ETFs.
        </p>
      </div>

      {/* Filters */}
      <div className="mb-4 flex flex-wrap items-center gap-3 bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
        <form onSubmit={applyEtfFilter} className="flex gap-2">
          <input
            type="text"
            value={etfInput}
            onChange={e => setEtfInput(e.target.value)}
            placeholder="Filter by ETF…"
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm w-36 focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
          <button type="submit" className="rounded-lg bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700">
            Apply
          </button>
        </form>
        <select
          value={typeFilter}
          onChange={e => { setTypeFilter(e.target.value); setPage(1) }}
          className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        >
          <option value="">All types</option>
          <option value="added">Added</option>
          <option value="removed">Removed</option>
          <option value="weight_change">Weight Change</option>
        </select>
        {(etfFilter || typeFilter) && (
          <button onClick={clearFilters} className="text-sm text-gray-500 hover:text-gray-800">
            × Clear filters
          </button>
        )}
        {data && (
          <span className="ml-auto text-sm text-gray-400">
            {data.total.toLocaleString()} events
          </span>
        )}
      </div>

      {isLoading && <LoadingSpinner />}
      {isError && <ErrorMessage message="Failed to load alerts." />}

      {data && (
        <>
          <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  {['ETF', 'Period', 'Type', 'Component', 'Sector', 'Old Shares', 'New Shares', 'Δ Shares'].map(h => (
                    <th key={h} className="px-4 py-3 text-left font-semibold text-gray-700 whitespace-nowrap">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.alerts.map((alert, i) => {
                  const type = TYPE_LABELS[alert.change_type] ?? { label: alert.change_type, cls: 'bg-gray-100 text-gray-700' }
                  const sharesOld = alert.shares_old
                  const sharesNew = alert.shares_new
                  const sharesDelta = sharesOld != null && sharesNew != null
                    ? sharesNew - sharesOld
                    : sharesNew != null ? sharesNew
                    : sharesOld != null ? -sharesOld
                    : null
                  const deltaStr = sharesDelta != null
                    ? `${sharesDelta > 0 ? '+' : ''}${Math.round(sharesDelta).toLocaleString()}`
                    : '—'
                  return (
                    <tr key={i} className={`border-b last:border-0 ${i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}`}>
                      <td className="px-4 py-2 font-semibold">
                        <Link to={`/etfs/${alert.etf_ticker}`} className="text-blue-600 hover:underline">
                          {alert.etf_ticker}
                        </Link>
                      </td>
                      <td className="px-4 py-2 whitespace-nowrap text-gray-500 text-xs">
                        {alert.date_from} → {alert.date_to}
                      </td>
                      <td className="px-4 py-2">
                        <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${type.cls}`}>
                          {type.label}
                        </span>
                      </td>
                      <td className="px-4 py-2 whitespace-nowrap">
                        <span className="font-medium">{alert.component_ticker ?? '—'}</span>
                        {alert.component_name && (
                          <span className="ml-1 text-xs text-gray-400">
                            {alert.component_name.length > 28
                              ? alert.component_name.slice(0, 28) + '…'
                              : alert.component_name}
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-2 text-xs text-gray-500">{alert.component_sector ?? '—'}</td>
                      <td className="px-4 py-2 text-xs text-gray-600 text-right whitespace-nowrap">
                        {sharesOld != null ? Math.round(sharesOld).toLocaleString() : '—'}
                      </td>
                      <td className="px-4 py-2 text-xs text-gray-600 text-right whitespace-nowrap">
                        {sharesNew != null ? Math.round(sharesNew).toLocaleString() : '—'}
                      </td>
                      <td className={`px-4 py-2 text-xs font-medium text-right whitespace-nowrap ${
                        sharesDelta == null ? 'text-gray-400' : sharesDelta > 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {deltaStr}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          <Pagination page={page} totalPages={data.total_pages} onPage={setPage} />
        </>
      )}
    </div>
  )
}

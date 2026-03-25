import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useEtfDetail } from '../hooks/useEtfs'
import { useCompare } from '../hooks/useCompositions'
import { DiffTable } from '../components/comparison/DiffTable'
import { LoadingSpinner } from '../components/common/LoadingSpinner'
import { ErrorMessage } from '../components/common/ErrorMessage'
import { DatePickerCalendar } from '../components/common/DatePickerCalendar'

function fmtShares(v: unknown) {
  if (v == null) return '—'
  const n = Number(v)
  return isNaN(n) ? '—' : Math.round(n).toLocaleString()
}

function fmtSharesDelta(v: unknown) {
  if (v == null) return '—'
  const n = Number(v)
  if (isNaN(n)) return '—'
  return `${n > 0 ? '+' : ''}${Math.round(n).toLocaleString()}`
}

export function CompositionHistory() {
  const { ticker = '' } = useParams()
  const upper = ticker.toUpperCase()

  const { data: detail, isLoading } = useEtfDetail(upper)

  const dates = detail?.available_dates ?? []
  const [date1, setDate1] = useState('')
  const [date2, setDate2] = useState('')

  const d1 = date1 || (dates.length >= 2 ? dates[1] : '')
  const d2 = date2 || (dates.length >= 1 ? dates[0] : '')

  const { data: compare, isLoading: comparing, isError: compareError } = useCompare(upper, d1, d2)

  if (isLoading) return <LoadingSpinner />

  return (
    <div>
      <div className="mb-4 text-sm text-gray-500 dark:text-gray-400">
        <Link to="/" className="hover:underline text-blue-600">Directory</Link>
        {' / '}
        <Link to={`/etfs/${upper}`} className="hover:underline text-blue-600">{upper}</Link>
        {' / '}
        <span className="text-gray-800 dark:text-gray-200 font-semibold">Composition History</span>
      </div>

      <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-1">{upper} — Composition History</h1>
      <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
        Compare holdings between any two stored snapshot dates.
      </p>

      {dates.length < 2 && (
        <ErrorMessage message="Need at least 2 stored composition dates to compare." />
      )}

      {dates.length >= 2 && (
        <>
          {/* Date selectors */}
          <div className="flex items-center gap-4 mb-6 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 shadow-sm">
            <DatePickerCalendar
              label="From date"
              value={d1}
              onChange={setDate1}
              availableDates={dates}
            />
            <span className="text-gray-400 dark:text-gray-500 mt-5">→</span>
            <DatePickerCalendar
              label="To date"
              value={d2}
              onChange={setDate2}
              availableDates={dates}
            />
          </div>

          {comparing && <LoadingSpinner />}
          {compareError && <ErrorMessage message="Failed to load comparison." />}

          {compare && (
            <div className="space-y-6">
              {/* Summary */}
              <div className="grid grid-cols-3 gap-4">
                {[
                  { label: 'Added', count: compare.summary.added_count, color: 'text-green-700 dark:text-green-400 bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800' },
                  { label: 'Removed', count: compare.summary.removed_count, color: 'text-red-700 dark:text-red-400 bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800' },
                  { label: 'Share Changes', count: compare.summary.weight_changes_count, color: 'text-yellow-700 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800' },
                ].map(({ label, count, color }) => (
                  <div key={label} className={`rounded-xl border p-4 ${color}`}>
                    <p className="text-2xl font-bold">{count}</p>
                    <p className="text-sm font-medium">{label}</p>
                  </div>
                ))}
              </div>

              {/* Added */}
              <div className="rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 p-5 shadow-sm">
                <h2 className="text-base font-semibold text-green-700 dark:text-green-400 mb-3">
                  ✚ Added ({compare.summary.added_count})
                </h2>
                <DiffTable
                  rows={compare.added}
                  columns={[
                    { key: 'component_ticker', label: 'Ticker' },
                    { key: 'component_name', label: 'Name' },
                    { key: 'shares_new', label: 'New Shares', format: fmtShares },
                    { key: 'component_sector', label: 'Sector' },
                  ]}
                  rowClass="bg-green-50 dark:bg-green-900/20 text-green-900 dark:text-green-300"
                  emptyMessage="No components added."
                />
              </div>

              {/* Removed */}
              <div className="rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 p-5 shadow-sm">
                <h2 className="text-base font-semibold text-red-700 dark:text-red-400 mb-3">
                  ✕ Removed ({compare.summary.removed_count})
                </h2>
                <DiffTable
                  rows={compare.removed}
                  columns={[
                    { key: 'component_ticker', label: 'Ticker' },
                    { key: 'component_name', label: 'Name' },
                    { key: 'shares_old', label: 'Old Shares', format: fmtShares },
                    { key: 'component_sector', label: 'Sector' },
                  ]}
                  rowClass="bg-red-50 dark:bg-red-900/20 text-red-900 dark:text-red-300"
                  emptyMessage="No components removed."
                />
              </div>

              {/* Share changes */}
              <div className="rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 p-5 shadow-sm">
                <h2 className="text-base font-semibold text-yellow-700 dark:text-yellow-400 mb-3">
                  ↕ Share Changes ({compare.summary.weight_changes_count})
                </h2>
                <DiffTable
                  rows={compare.weight_changes}
                  columns={[
                    { key: 'component_ticker', label: 'Ticker' },
                    { key: 'component_name', label: 'Name' },
                    { key: 'shares_old', label: 'Old Shares', format: fmtShares },
                    { key: 'shares_new', label: 'New Shares', format: fmtShares },
                    { key: 'shares_delta', label: 'Δ Shares', format: fmtSharesDelta },
                    { key: 'component_sector', label: 'Sector' },
                  ]}
                  rowClass="bg-yellow-50 dark:bg-yellow-900/20 text-yellow-900 dark:text-yellow-300"
                  emptyMessage="No share count changes detected."
                />
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}

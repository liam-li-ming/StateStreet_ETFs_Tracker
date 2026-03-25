import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useSearch } from '../hooks/useSearch'
import { LoadingSpinner } from '../components/common/LoadingSpinner'
import { ErrorMessage } from '../components/common/ErrorMessage'

export function CrossETFSearch() {
  const [input, setInput] = useState('')
  const [query, setQuery] = useState('')

  const { data, isLoading, isError, isFetching } = useSearch(query)

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setQuery(input.trim().toUpperCase())
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Cross-ETF Search</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Find all SSGA ETFs that hold a specific stock or component.
        </p>
      </div>

      {/* Search box */}
      <form onSubmit={handleSubmit} className="mb-6 flex gap-2">
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="Enter component ticker, e.g. NVDA"
          className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 px-4 py-2 text-sm w-72 focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
        <button
          type="submit"
          className="rounded-lg bg-blue-600 px-5 py-2 text-sm text-white hover:bg-blue-700"
        >
          Search
        </button>
      </form>

      {(isLoading || isFetching) && <LoadingSpinner />}
      {isError && <ErrorMessage message="Search failed. Try a different ticker." />}

      {data && !isFetching && (
        <>
          <div className="mb-3 text-sm text-gray-600 dark:text-gray-400">
            {data.total_etfs > 0 ? (
              <>
                <span className="font-semibold text-blue-700 dark:text-blue-400">{data.component_ticker}</span>
                {' is held by '}
                <span className="font-semibold text-gray-900 dark:text-gray-100">{data.total_etfs}</span>
                {' SSGA ETFs (latest composition date per ETF)'}
              </>
            ) : (
              <>
                No SSGA ETFs hold{' '}
                <span className="font-semibold text-gray-900 dark:text-gray-100">{data.component_ticker}</span>
                {' in their latest compositions.'}
              </>
            )}
          </div>

          {data.total_etfs > 0 && (
            <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm overflow-hidden">
              <table className="min-w-full text-sm">
                <thead className="bg-gray-50 dark:bg-gray-700 border-b border-gray-200 dark:border-gray-600">
                  <tr>
                    {['ETF', 'Fund Name', 'Weight', 'Sector', 'Shares Held', 'As of Date'].map(h => (
                      <th key={h} className="px-4 py-3 text-left font-semibold text-gray-700 dark:text-gray-300 whitespace-nowrap">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.found_in.map((r, i) => (
                    <tr key={i} className={`border-b border-gray-100 dark:border-gray-700 last:border-0 ${i % 2 === 0 ? 'bg-white dark:bg-gray-800' : 'bg-gray-50 dark:bg-gray-700/50'}`}>
                      <td className="px-4 py-2 font-semibold">
                        <Link to={`/etfs/${r.etf_ticker}`} className="text-blue-600 hover:underline">
                          {r.etf_ticker}
                        </Link>
                      </td>
                      <td className="px-4 py-2 text-gray-700 dark:text-gray-300">
                        {r.etf_name ?? '—'}
                      </td>
                      <td className="px-4 py-2 font-medium text-gray-900 dark:text-gray-100">
                        {r.component_weight != null ? `${r.component_weight.toFixed(4)}%` : '—'}
                      </td>
                      <td className="px-4 py-2 text-gray-500 dark:text-gray-400 text-xs">{r.component_sector ?? '—'}</td>
                      <td className="px-4 py-2 text-gray-700 dark:text-gray-300">
                        {r.component_shares != null ? r.component_shares.toLocaleString() : '—'}
                      </td>
                      <td className="px-4 py-2 text-gray-400 dark:text-gray-500 text-xs">{r.composition_date}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  )
}

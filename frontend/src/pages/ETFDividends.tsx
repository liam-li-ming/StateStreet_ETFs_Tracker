import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useDividends } from '../hooks/useDividends'
import { LoadingSpinner } from '../components/common/LoadingSpinner'
import { ErrorMessage } from '../components/common/ErrorMessage'
import { Pagination } from '../components/common/Pagination'

export function ETFDividends() {
  const [page, setPage] = useState(1)
  const [etfFilter, setEtfFilter] = useState('')
  const [etfInput, setEtfInput] = useState('')

  const { data, isLoading, isError } = useDividends(page, 50, etfFilter)

  function applyFilter(e: React.FormEvent) {
    e.preventDefault()
    setEtfFilter(etfInput.toUpperCase())
    setPage(1)
  }

  function clearFilter() {
    setEtfFilter('')
    setEtfInput('')
    setPage(1)
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">ETF Dividends</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Historical dividend distributions for all tracked SSGA ETFs.
        </p>
      </div>

      {/* Filter bar */}
      <div className="mb-4 flex flex-wrap items-center gap-3 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 shadow-sm">
        <form onSubmit={applyFilter} className="flex gap-2">
          <input
            type="text"
            value={etfInput}
            onChange={e => setEtfInput(e.target.value)}
            placeholder="Filter by ETF…"
            className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 px-3 py-1.5 text-sm w-36 focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
          <button type="submit" className="rounded-lg bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700">
            Apply
          </button>
        </form>
        {etfFilter && (
          <button onClick={clearFilter} className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200">
            × Clear
          </button>
        )}
        {data && (
          <span className="ml-auto text-sm text-gray-400 dark:text-gray-500">
            {data.total.toLocaleString()} records
          </span>
        )}
      </div>

      {isLoading && <LoadingSpinner />}
      {isError && <ErrorMessage message="Failed to load dividend data." />}

      {data && (
        <>
          <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm overflow-hidden">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-50 dark:bg-gray-700 border-b border-gray-200 dark:border-gray-600">
                <tr>
                  {['ETF', 'Ex-Date', 'Dividend Amount', 'Currency'].map(h => (
                    <th key={h} className="px-4 py-3 text-left font-semibold text-gray-700 dark:text-gray-300 whitespace-nowrap">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.dividends.map((d, i) => (
                  <tr
                    key={`${d.etf_ticker}-${d.ex_date}`}
                    className={`border-b border-gray-100 dark:border-gray-700 last:border-0 ${
                      i % 2 === 0 ? 'bg-white dark:bg-gray-800' : 'bg-gray-50 dark:bg-gray-700/50'
                    }`}
                  >
                    <td className="px-4 py-2 font-semibold">
                      <Link to={`/etfs/${d.etf_ticker}`} className="text-blue-600 hover:underline">
                        {d.etf_ticker}
                      </Link>
                    </td>
                    <td className="px-4 py-2 text-gray-600 dark:text-gray-400 whitespace-nowrap">
                      {d.ex_date}
                    </td>
                    <td className="px-4 py-2 font-medium text-gray-800 dark:text-gray-200 whitespace-nowrap">
                      ${d.dividend_amount.toFixed(4)}
                    </td>
                    <td className="px-4 py-2 text-gray-500 dark:text-gray-400">
                      {d.currency}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination page={page} totalPages={data.total_pages} onPage={setPage} />
        </>
      )}
    </div>
  )
}

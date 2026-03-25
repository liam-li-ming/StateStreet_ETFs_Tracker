import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useEtfDetail } from '../hooks/useEtfs'
import { useComposition } from '../hooks/useCompositions'
import { SectorPieChart } from '../components/etf/SectorPieChart'
import { Top10BarChart } from '../components/etf/Top10BarChart'
import { HoldingsTable } from '../components/etf/HoldingsTable'
import { LoadingSpinner } from '../components/common/LoadingSpinner'
import { ErrorMessage } from '../components/common/ErrorMessage'
import { DatePickerCalendar } from '../components/common/DatePickerCalendar'

export function ETFDetail() {
  const { ticker = '' } = useParams()
  const [selectedDate, setSelectedDate] = useState('')
  const [holdingLimit, setHoldingLimit] = useState(50)

  const { data: detail, isLoading, isError } = useEtfDetail(ticker.toUpperCase(), holdingLimit)

  const activeDate = selectedDate || detail?.latest_composition_date || ''
  const { data: composition } = useComposition(ticker.toUpperCase(), activeDate, 5000)

  if (isLoading) return <LoadingSpinner />
  if (isError || !detail) return <ErrorMessage message={`ETF '${ticker}' not found.`} />

  const chartHoldings = composition?.holdings ?? detail.holdings

  return (
    <div>
      {/* Breadcrumb */}
      <div className="mb-4 text-sm text-gray-500 dark:text-gray-400">
        <Link to="/" className="hover:underline text-blue-600">Directory</Link>
        {' / '}
        <span className="text-gray-800 dark:text-gray-200 font-semibold">{detail.ticker}</span>
      </div>

      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">{detail.ticker}</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-0.5">{detail.name}</p>
        </div>
        <Link
          to={`/etfs/${ticker}/history`}
          className="rounded-lg border border-blue-300 dark:border-blue-700 px-4 py-2 text-sm text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20"
        >
          Compare Dates →
        </Link>
      </div>

      {/* Metadata cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        {[
          { label: 'NAV', value: detail.nav },
          { label: 'AUM', value: detail.aum },
          { label: 'Expense Ratio', value: detail.gross_expense_ratio },
          { label: 'Domicile', value: detail.domicile },
        ].map(({ label, value }) => (
          <div key={label} className="rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 p-4 shadow-sm">
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">{label}</p>
            <p className="font-semibold text-gray-900 dark:text-gray-100">{value ?? '—'}</p>
          </div>
        ))}
      </div>

      {/* Date picker */}
      {detail.available_dates.length > 0 && (
        <div className="mb-4 flex items-center gap-3">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Composition date:</span>
          <DatePickerCalendar
            label=""
            value={activeDate}
            onChange={setSelectedDate}
            availableDates={detail.available_dates}
          />
          <span className="text-xs text-gray-400 dark:text-gray-500 self-end mb-2">
            {detail.holdings_count.toLocaleString()} holdings
          </span>
        </div>
      )}

      {/* Charts */}
      <div className="grid md:grid-cols-2 gap-6 mb-6">
        <div className="rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 p-5 shadow-sm">
          <h2 className="text-base font-semibold text-gray-800 dark:text-gray-200 mb-4">Sector Allocation</h2>
          <SectorPieChart holdings={chartHoldings} />
        </div>
        <div className="rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 p-5 shadow-sm">
          <h2 className="text-base font-semibold text-gray-800 dark:text-gray-200 mb-4">Top 10 Holdings</h2>
          <Top10BarChart holdings={chartHoldings} />
        </div>
      </div>

      {/* Holdings table */}
      <div className="rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 p-5 shadow-sm">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-base font-semibold text-gray-800 dark:text-gray-200">
            All Holdings
            <span className="ml-2 text-sm font-normal text-gray-400 dark:text-gray-500">
              (showing {detail.holdings.length} of {detail.holdings_count})
            </span>
          </h2>
          {detail.holdings_truncated && (
            <button
              onClick={() => setHoldingLimit(prev => prev + 200)}
              className="text-xs text-blue-600 hover:underline"
            >
              Load more
            </button>
          )}
        </div>
        <HoldingsTable holdings={detail.holdings} truncated={detail.holdings_truncated} />
      </div>
    </div>
  )
}

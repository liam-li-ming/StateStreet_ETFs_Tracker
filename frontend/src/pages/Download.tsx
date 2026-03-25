import { useState, useEffect } from 'react'
import { useEtfDetail } from '../hooks/useEtfs'
import { DatePickerCalendar } from '../components/common/DatePickerCalendar'

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

export function Download() {
  const [inputTicker, setInputTicker] = useState('')
  const [confirmedTicker, setConfirmedTicker] = useState('')
  const [selectedDate, setSelectedDate] = useState('')

  const { data: detail, isLoading, isError } = useEtfDetail(confirmedTicker)

  // Default to latest available date when ETF loads
  useEffect(() => {
    if (detail?.available_dates?.length) {
      setSelectedDate(detail.available_dates[0])
    }
  }, [detail])

  function handleLoad() {
    const t = inputTicker.trim().toUpperCase()
    if (!t) return
    if (t !== confirmedTicker) {
      setSelectedDate('')
      setConfirmedTicker(t)
    }
  }

  function handleDownload(format: 'xlsx' | 'csv' | 'json') {
    if (!confirmedTicker || !selectedDate) return
    const url = `${BASE_URL}/api/etfs/${confirmedTicker}/compositions/${selectedDate}/download?format=${format}`
    const a = document.createElement('a')
    a.href = url
    a.download = `${confirmedTicker}_${selectedDate}_composition.${format}`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }

  const ready = !!detail && !!selectedDate
  const noData = confirmedTicker && !isLoading && isError
  const hasNoDates = detail && detail.available_dates.length === 0

  return (
    <div className="max-w-xl">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">Download Composition</h1>
      <p className="text-sm text-gray-500 mb-6">
        Download the full ETF holdings and metadata for a given date.
      </p>

      {/* Ticker input */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm mb-4">
        <label className="block text-xs font-medium text-gray-500 mb-1">ETF Ticker</label>
        <div className="flex gap-2">
          <input
            type="text"
            value={inputTicker}
            onChange={e => setInputTicker(e.target.value.toUpperCase())}
            onKeyDown={e => { if (e.key === 'Enter') handleLoad() }}
            placeholder="e.g. SPY"
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm w-36 focus:outline-none focus:ring-2 focus:ring-blue-400 font-mono uppercase"
          />
          <button
            onClick={handleLoad}
            disabled={!inputTicker.trim()}
            className="rounded-lg bg-blue-600 text-white px-4 py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Load
          </button>
        </div>

        {isLoading && (
          <p className="text-xs text-gray-400 mt-2">Loading...</p>
        )}
        {noData && (
          <p className="text-xs text-red-500 mt-2">ETF "{confirmedTicker}" not found.</p>
        )}
        {hasNoDates && (
          <p className="text-xs text-yellow-600 mt-2">No composition data available for {confirmedTicker}.</p>
        )}
        {detail && (
          <p className="text-xs text-green-600 mt-2 font-medium">
            {detail.ticker} — {detail.name}
          </p>
        )}
      </div>

      {/* Date picker */}
      {detail && detail.available_dates.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm mb-4">
          <DatePickerCalendar
            label="Composition Date"
            value={selectedDate}
            onChange={setSelectedDate}
            availableDates={detail.available_dates}
          />
        </div>
      )}

      {/* Download buttons */}
      {ready && (
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <p className="text-xs font-medium text-gray-500 mb-3">Format</p>
          <div className="flex gap-2 flex-wrap">
            {([
              { format: 'xlsx', label: 'XLSX', style: 'bg-green-600 hover:bg-green-700' },
              { format: 'csv',  label: 'CSV',  style: 'bg-blue-600 hover:bg-blue-700' },
              { format: 'json', label: 'JSON', style: 'bg-gray-700 hover:bg-gray-800' },
            ] as const).map(({ format, label, style }) => (
              <button
                key={format}
                onClick={() => handleDownload(format)}
                className={`flex items-center gap-2 rounded-lg text-white px-5 py-2.5 text-sm font-medium ${style}`}
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                {label}
              </button>
            ))}
          </div>
          <p className="text-xs text-gray-400 mt-3">
            {confirmedTicker} · {selectedDate} · {detail.holdings_count.toLocaleString()} holdings
          </p>
        </div>
      )}
    </div>
  )
}

import { useState, useRef, useEffect } from 'react'

interface Props {
  label: string
  value: string
  onChange: (date: string) => void
  availableDates: string[] // sorted DESC YYYY-MM-DD
}

function getDaysInMonth(year: number, month: number) {
  return new Date(year, month + 1, 0).getDate()
}

function getFirstDayOfMonth(year: number, month: number) {
  // Returns 0=Sun … 6=Sat
  return new Date(year, month, 1).getDay()
}

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]
const DAY_NAMES = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa']

function parseViewFromDate(date: string): { year: number; month: number } | null {
  if (!date || !/^\d{4}-\d{2}-\d{2}$/.test(date)) return null
  return { year: parseInt(date.slice(0, 4)), month: parseInt(date.slice(5, 7)) - 1 }
}

export function DatePickerCalendar({ label, value, onChange, availableDates }: Props) {
  const [inputValue, setInputValue] = useState(value)
  const [isOpen, setIsOpen] = useState(false)
  const [inputError, setInputError] = useState(false)

  const initView = () => {
    const parsed = parseViewFromDate(value) ?? parseViewFromDate(availableDates[0] ?? '')
    if (parsed) return parsed
    const now = new Date()
    return { year: now.getFullYear(), month: now.getMonth() }
  }

  const [viewYear, setViewYear] = useState(() => initView().year)
  const [viewMonth, setViewMonth] = useState(() => initView().month)

  const containerRef = useRef<HTMLDivElement>(null)
  const availableSet = new Set(availableDates)

  useEffect(() => {
    setInputValue(value)
    setInputError(false)
    const parsed = parseViewFromDate(value)
    if (parsed) {
      setViewYear(parsed.year)
      setViewMonth(parsed.month)
    }
  }, [value])

  useEffect(() => {
    function handleOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleOutside)
    return () => document.removeEventListener('mousedown', handleOutside)
  }, [])

  function commitInput(raw: string) {
    const v = raw.trim()
    if (!v) {
      setInputValue(value)
      setInputError(false)
      return
    }
    if (!/^\d{4}-\d{2}-\d{2}$/.test(v)) {
      setInputError(true)
      return
    }
    if (availableSet.has(v)) {
      onChange(v)
      setInputError(false)
      const parsed = parseViewFromDate(v)
      if (parsed) { setViewYear(parsed.year); setViewMonth(parsed.month) }
    } else {
      setInputError(true)
    }
  }

  function selectDate(dateStr: string) {
    onChange(dateStr)
    setInputValue(dateStr)
    setInputError(false)
    setIsOpen(false)
  }

  function prevMonth() {
    if (viewMonth === 0) { setViewMonth(11); setViewYear(y => y - 1) }
    else setViewMonth(m => m - 1)
  }

  function nextMonth() {
    if (viewMonth === 11) { setViewMonth(0); setViewYear(y => y + 1) }
    else setViewMonth(m => m + 1)
  }

  const daysInMonth = getDaysInMonth(viewYear, viewMonth)
  const firstDay = getFirstDayOfMonth(viewYear, viewMonth)
  const cells: (string | null)[] = Array(firstDay).fill(null)
  for (let d = 1; d <= daysInMonth; d++) {
    cells.push(
      `${viewYear}-${String(viewMonth + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`
    )
  }

  return (
    <div ref={containerRef} className="relative">
      {label && <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">{label}</label>}
      <div className="flex items-center gap-1">
        <input
          type="text"
          value={inputValue}
          onChange={e => { setInputValue(e.target.value); setInputError(false) }}
          onBlur={e => commitInput(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') commitInput(inputValue) }}
          placeholder="YYYY-MM-DD"
          className={`rounded-lg border px-3 py-2 text-sm w-32 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 ${
            inputError
              ? 'border-red-400 focus:ring-red-300'
              : 'border-gray-300 dark:border-gray-600 focus:ring-blue-400'
          }`}
        />
        <button
          type="button"
          onClick={() => setIsOpen(o => !o)}
          className="p-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 text-gray-500 dark:text-gray-400"
          title="Open calendar"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
        </button>
      </div>

      {inputError && (
        <p className="text-xs text-red-500 mt-1">No data available for this date.</p>
      )}

      {isOpen && (
        <div className="absolute z-50 mt-1 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-lg p-3 w-60">
          {/* Month navigation */}
          <div className="flex items-center justify-between mb-2">
            <button
              type="button"
              onClick={prevMonth}
              className="w-6 h-6 flex items-center justify-center rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-300 text-lg leading-none"
            >
              ‹
            </button>
            <span className="text-sm font-semibold text-gray-800 dark:text-gray-200">
              {MONTH_NAMES[viewMonth]} {viewYear}
            </span>
            <button
              type="button"
              onClick={nextMonth}
              className="w-6 h-6 flex items-center justify-center rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-300 text-lg leading-none"
            >
              ›
            </button>
          </div>

          {/* Day-of-week headers */}
          <div className="grid grid-cols-7 mb-1">
            {DAY_NAMES.map(d => (
              <div key={d} className="text-center text-xs font-medium text-gray-400 dark:text-gray-500 py-0.5">{d}</div>
            ))}
          </div>

          {/* Day cells */}
          <div className="grid grid-cols-7 gap-y-0.5">
            {cells.map((dateStr, i) => {
              if (!dateStr) return <div key={`e-${i}`} />
              const isAvailable = availableSet.has(dateStr)
              const isSelected = dateStr === value
              return (
                <button
                  key={dateStr}
                  type="button"
                  disabled={!isAvailable}
                  onClick={() => selectDate(dateStr)}
                  className={`mx-auto w-7 h-7 flex items-center justify-center rounded-full text-xs transition-colors ${
                    isSelected
                      ? 'bg-blue-600 text-white font-bold'
                      : isAvailable
                        ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-800 dark:text-blue-300 hover:bg-blue-200 dark:hover:bg-blue-900/60 font-medium cursor-pointer'
                        : 'text-gray-300 dark:text-gray-600 cursor-not-allowed'
                  }`}
                >
                  {parseInt(dateStr.slice(8))}
                </button>
              )
            })}
          </div>

          {/* Legend */}
          <div className="mt-2 pt-2 border-t border-gray-100 dark:border-gray-700 flex items-center gap-1.5 text-xs text-gray-400 dark:text-gray-500">
            <span className="inline-block w-3 h-3 bg-blue-100 dark:bg-blue-900/40 rounded-full" />
            Data available
          </div>
        </div>
      )}
    </div>
  )
}

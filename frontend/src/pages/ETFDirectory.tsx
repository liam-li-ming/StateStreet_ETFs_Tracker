import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  useReactTable, getCoreRowModel, getSortedRowModel,
  flexRender, type ColumnDef, type SortingState,
} from '@tanstack/react-table'
import { useEtfs } from '../hooks/useEtfs'
import { LoadingSpinner } from '../components/common/LoadingSpinner'
import { ErrorMessage } from '../components/common/ErrorMessage'
import type { EtfInfo } from '../types/etf'

const columns: ColumnDef<EtfInfo>[] = [
  {
    accessorKey: 'ticker',
    header: 'Ticker',
    cell: ({ getValue }) => (
      <Link
        to={`/etfs/${getValue<string>()}`}
        className="font-semibold text-blue-600 hover:underline"
      >
        {getValue<string>()}
      </Link>
    ),
    size: 90,
  },
  { accessorKey: 'name', header: 'Name', size: 280 },
  { accessorKey: 'domicile', header: 'Domicile', size: 90 },
  { accessorKey: 'gross_expense_ratio', header: 'Expense Ratio', size: 120 },
  { accessorKey: 'nav', header: 'NAV', size: 90 },
  { accessorKey: 'aum', header: 'AUM', size: 110 },
]

export function ETFDirectory() {
  const [q, setQ] = useState('')
  const [input, setInput] = useState('')
  const [sorting, setSorting] = useState<SortingState>([])

  const { data, isLoading, isError } = useEtfs(q)

  const table = useReactTable({
    data: data?.etfs ?? [],
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  })

  function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    setQ(input)
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">ETF Directory</h1>
          <p className="text-sm text-gray-500 mt-1">
            {data ? `${data.total} SSGA ETFs tracked` : 'Loading…'}
          </p>
        </div>
        <form onSubmit={handleSearch} className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="Search ticker or name…"
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm w-64 focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
          <button
            type="submit"
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700"
          >
            Search
          </button>
          {q && (
            <button
              type="button"
              onClick={() => { setQ(''); setInput('') }}
              className="rounded-lg border px-4 py-2 text-sm text-gray-600 hover:bg-gray-100"
            >
              Clear
            </button>
          )}
        </form>
      </div>

      {isLoading && <LoadingSpinner />}
      {isError && <ErrorMessage message="Failed to load ETFs." />}

      {data && (
        <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white shadow-sm">
          <table className="min-w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              {table.getHeaderGroups().map(hg => (
                <tr key={hg.id}>
                  {hg.headers.map(h => (
                    <th
                      key={h.id}
                      onClick={h.column.getToggleSortingHandler()}
                      className="px-4 py-3 text-left font-semibold text-gray-700 cursor-pointer select-none whitespace-nowrap hover:bg-gray-100"
                    >
                      {flexRender(h.column.columnDef.header, h.getContext())}
                      {h.column.getIsSorted() === 'asc' ? ' ↑' : h.column.getIsSorted() === 'desc' ? ' ↓' : ''}
                    </th>
                  ))}
                  <th className="px-4 py-3 text-left font-semibold text-gray-700 whitespace-nowrap">
                    History
                  </th>
                </tr>
              ))}
            </thead>
            <tbody>
              {table.getRowModel().rows.map((row, i) => (
                <tr
                  key={row.id}
                  className={`border-b last:border-0 ${i % 2 === 0 ? 'bg-white' : 'bg-gray-50'} hover:bg-blue-50`}
                >
                  {row.getVisibleCells().map(cell => (
                    <td key={cell.id} className="px-4 py-2 text-gray-700 whitespace-nowrap">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                  <td className="px-4 py-2">
                    <Link
                      to={`/etfs/${row.original.ticker}/history`}
                      className="text-xs text-blue-500 hover:underline"
                    >
                      Compare dates
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

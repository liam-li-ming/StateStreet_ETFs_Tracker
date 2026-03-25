import {
  useReactTable, getCoreRowModel, getSortedRowModel,
  flexRender, type ColumnDef, type SortingState,
} from '@tanstack/react-table'
import { useState } from 'react'
import type { HoldingItem } from '../../types/etf'

interface Props {
  holdings: HoldingItem[]
  truncated?: boolean
}

const columns: ColumnDef<HoldingItem>[] = [
  { accessorKey: 'component_ticker', header: 'Ticker', size: 90 },
  { accessorKey: 'component_name', header: 'Name', size: 220 },
  {
    accessorKey: 'component_weight',
    header: 'Weight',
    cell: ({ getValue }) => {
      const v = getValue<number | null>()
      return v != null ? `${v.toFixed(4)}%` : '—'
    },
    size: 90,
  },
  { accessorKey: 'component_sector', header: 'Sector', size: 180 },
  {
    accessorKey: 'component_shares',
    header: 'Shares',
    cell: ({ getValue }) => {
      const v = getValue<number | null>()
      return v != null ? v.toLocaleString() : '—'
    },
    size: 110,
  },
  { accessorKey: 'component_currency', header: 'Currency', size: 80 },
]

export function HoldingsTable({ holdings, truncated }: Props) {
  const [sorting, setSorting] = useState<SortingState>([
    { id: 'component_weight', desc: true },
  ])

  const table = useReactTable({
    data: holdings,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  })

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700">
      {truncated && (
        <p className="bg-yellow-50 dark:bg-yellow-900/20 px-4 py-2 text-xs text-yellow-700 dark:text-yellow-300 border-b border-yellow-200 dark:border-yellow-800">
          Showing first {holdings.length} holdings. Use the Composition page for the full list.
        </p>
      )}
      <table className="min-w-full text-sm">
        <thead className="bg-gray-50 dark:bg-gray-700 sticky top-0">
          {table.getHeaderGroups().map(hg => (
            <tr key={hg.id}>
              {hg.headers.map(h => (
                <th
                  key={h.id}
                  onClick={h.column.getToggleSortingHandler()}
                  className="px-3 py-2 text-left font-semibold text-gray-700 dark:text-gray-300 cursor-pointer select-none whitespace-nowrap"
                >
                  {flexRender(h.column.columnDef.header, h.getContext())}
                  {h.column.getIsSorted() === 'asc' ? ' ↑' : h.column.getIsSorted() === 'desc' ? ' ↓' : ''}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row, i) => (
            <tr key={row.id} className={i % 2 === 0 ? 'bg-white dark:bg-gray-800' : 'bg-gray-50 dark:bg-gray-700/50'}>
              {row.getVisibleCells().map(cell => (
                <td key={cell.id} className="px-3 py-1.5 text-gray-700 dark:text-gray-300 whitespace-nowrap">
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

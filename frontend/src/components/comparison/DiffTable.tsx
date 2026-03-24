interface Column {
  key: string
  label: string
  format?: (v: unknown) => string
}

interface Props {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  rows: any[]
  columns: Column[]
  rowClass: string
  emptyMessage: string
}

export function DiffTable({ rows, columns, rowClass, emptyMessage }: Props) {
  if (!rows.length) {
    return <p className="text-sm text-gray-400 py-2">{emptyMessage}</p>
  }
  return (
    <div className="overflow-x-auto rounded-lg border">
      <table className="min-w-full text-sm">
        <thead className="bg-gray-50">
          <tr>
            {columns.map(c => (
              <th key={c.key} className="px-3 py-2 text-left font-semibold text-gray-700 whitespace-nowrap">
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className={rowClass}>
              {columns.map(c => {
                const val = row[c.key]
                const display = c.format ? c.format(val) : (val != null ? String(val) : '—')
                return (
                  <td key={c.key} className="px-3 py-1.5 whitespace-nowrap">
                    {display}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

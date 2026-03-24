import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LabelList,
} from 'recharts'
import type { HoldingItem } from '../../types/etf'

interface Props { holdings: HoldingItem[] }

export function Top10BarChart({ holdings }: Props) {
  const top10 = [...holdings]
    .filter(h => h.component_weight != null)
    .sort((a, b) => (b.component_weight ?? 0) - (a.component_weight ?? 0))
    .slice(0, 10)
    .map(h => ({
      name: h.component_ticker ?? h.component_name ?? '—',
      weight: Math.round((h.component_weight ?? 0) * 100) / 100,
    }))

  if (!top10.length) return <p className="text-sm text-gray-400">No data</p>

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={top10} layout="vertical" margin={{ left: 8, right: 24 }}>
        <XAxis type="number" tickFormatter={v => `${v}%`} tick={{ fontSize: 11 }} />
        <YAxis type="category" dataKey="name" width={52} tick={{ fontSize: 12 }} />
        <Tooltip formatter={(v) => `${Number(v).toFixed(2)}%`} />
        <Bar dataKey="weight" radius={[0, 4, 4, 0]} fill="#3b82f6">
          <LabelList dataKey="weight" position="right" formatter={(v: unknown) => `${Number(v).toFixed(2)}%`} style={{ fontSize: 11 }} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

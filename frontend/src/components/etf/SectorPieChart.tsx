import {
  PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import type { HoldingItem } from '../../types/etf'

const COLORS = [
  '#3b82f6','#10b981','#f59e0b','#ef4444','#8b5cf6',
  '#06b6d4','#f97316','#84cc16','#ec4899','#14b8a6',
  '#a855f7','#0ea5e9',
]

interface Props { holdings: HoldingItem[] }

export function SectorPieChart({ holdings }: Props) {
  const sectorMap: Record<string, number> = {}
  for (const h of holdings) {
    if (h.component_sector && h.component_weight != null) {
      sectorMap[h.component_sector] = (sectorMap[h.component_sector] ?? 0) + h.component_weight
    }
  }
  const data = Object.entries(sectorMap)
    .map(([name, value]) => ({ name, value: Math.round(value * 100) / 100 }))
    .sort((a, b) => b.value - a.value)

  if (!data.length) return <p className="text-sm text-gray-400">No sector data</p>

  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Pie
          data={data}
          dataKey="value"
          nameKey="name"
          cx="50%"
          cy="50%"
          innerRadius={60}
          outerRadius={110}
          paddingAngle={2}
        >
          {data.map((_, i) => (
            <Cell key={i} fill={COLORS[i % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip formatter={(v) => `${Number(v).toFixed(2)}%`} />
        <Legend
          formatter={(value) =>
            value.length > 20 ? value.slice(0, 20) + '…' : value
          }
        />
      </PieChart>
    </ResponsiveContainer>
  )
}

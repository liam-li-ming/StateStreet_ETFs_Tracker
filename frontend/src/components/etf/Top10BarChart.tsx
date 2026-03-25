import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LabelList,
} from 'recharts'
import type { HoldingItem } from '../../types/etf'
import { useThemeContext } from '../../context/ThemeContext'

interface Props { holdings: HoldingItem[] }

export function Top10BarChart({ holdings }: Props) {
  const { theme } = useThemeContext()
  const isDark = theme === 'dark' ||
    (theme === 'system' && typeof window !== 'undefined' && window.matchMedia('(prefers-color-scheme: dark)').matches)

  const top10 = [...holdings]
    .filter(h => h.component_weight != null)
    .sort((a, b) => (b.component_weight ?? 0) - (a.component_weight ?? 0))
    .slice(0, 10)
    .map(h => ({
      name: h.component_ticker ?? h.component_name ?? '—',
      weight: Math.round((h.component_weight ?? 0) * 100) / 100,
    }))

  if (!top10.length) return <p className="text-sm text-gray-400 dark:text-gray-500">No data</p>

  const tickColor = isDark ? '#9ca3af' : '#6b7280'
  const labelColor = isDark ? '#d1d5db' : '#374151'
  const tooltipStyle = {
    backgroundColor: isDark ? '#1f2937' : '#ffffff',
    borderColor: isDark ? '#374151' : '#e5e7eb',
    color: isDark ? '#f3f4f6' : '#111827',
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={top10} layout="vertical" margin={{ left: 8, right: 24 }}>
        <XAxis type="number" tickFormatter={v => `${v}%`} tick={{ fontSize: 11, fill: tickColor }} />
        <YAxis type="category" dataKey="name" width={52} tick={{ fontSize: 12, fill: tickColor }} />
        <Tooltip formatter={(v) => `${Number(v).toFixed(2)}%`} contentStyle={tooltipStyle} />
        <Bar dataKey="weight" radius={[0, 4, 4, 0]} fill="#3b82f6">
          <LabelList
            dataKey="weight"
            position="right"
            formatter={(v: unknown) => `${Number(v).toFixed(2)}%`}
            style={{ fontSize: 11, fill: labelColor }}
          />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

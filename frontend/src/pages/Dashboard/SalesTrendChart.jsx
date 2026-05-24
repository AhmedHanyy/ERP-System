import { useState, useEffect } from 'react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, LineChart, Line
} from 'recharts'
import { dashboardApi } from '@/services/api'
import { PageLoader } from '@/components/shared/States'
import { format } from 'date-fns'

const PERIODS = [
  { label: '7D',  value: '7d'  },
  { label: '30D', value: '30d' },
  { label: '90D', value: '90d' },
]

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="glass-card p-3 text-xs border border-border shadow-card">
      <p className="text-text-muted mb-1">{label}</p>
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.color }} className="font-medium">
          {p.name}: {p.name === 'revenue' ? `EGP ${p.value?.toLocaleString()}` : p.value}
        </p>
      ))}
    </div>
  )
}

export default function SalesTrendChart() {
  const [data,   setData]   = useState([])
  const [period, setPeriod] = useState('30d')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    dashboardApi.getSalesTrend(period)
      .then(d => { setData(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [period])

  const totalRevenue = data.reduce((s, d) => s + (d.revenue || 0), 0)

  return (
    <div className="glass-card p-6 h-full">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="section-title mb-0">Sales Trend</h3>
          <p className="text-xs text-text-secondary mt-0.5">
            Total: <span className="text-text-primary font-semibold">EGP {totalRevenue.toLocaleString(undefined, {maximumFractionDigits: 0})}</span>
          </p>
        </div>
        <div className="flex gap-1 bg-bg-primary rounded-xl p-1">
          {PERIODS.map(p => (
            <button
              key={p.value}
              onClick={() => setPeriod(p.value)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 ${
                period === p.value
                  ? 'bg-brand-500 text-white shadow-glow-brand'
                  : 'text-text-muted hover:text-text-primary'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {loading ? <PageLoader /> : (
        <ResponsiveContainer width="100%" height={220}>
          <AreaChart data={data} margin={{ top: 5, right: 5, left: 0, bottom: 5 }}>
            <defs>
              <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#6366F1" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#6366F1" stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1E2D47" vertical={false} />
            <XAxis
              dataKey="date"
              tick={{ fill: '#475569', fontSize: 11 }}
              tickFormatter={(v) => {
                try { return format(new Date(v), 'MMM d') } catch { return v }
              }}
              axisLine={false} tickLine={false}
            />
            <YAxis
              tick={{ fill: '#475569', fontSize: 11 }}
              tickFormatter={(v) => `${(v/1000).toFixed(0)}K`}
              axisLine={false} tickLine={false} width={40}
            />
            <Tooltip content={<CustomTooltip />} />
            <Area
              type="monotone" dataKey="revenue" name="revenue"
              stroke="#6366F1" strokeWidth={2}
              fill="url(#colorRevenue)"
              dot={false} activeDot={{ r: 4, fill: '#6366F1' }}
            />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}

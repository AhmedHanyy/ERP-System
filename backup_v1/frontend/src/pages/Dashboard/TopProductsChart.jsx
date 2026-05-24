import { useState, useEffect } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { dashboardApi } from '@/services/api'
import { PageLoader } from '@/components/shared/States'

export default function TopProductsChart() {
  const [data,    setData]    = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    dashboardApi.getTopProducts()
      .then(d => { setData(d.slice(0, 7)); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  return (
    <div className="glass-card p-6 h-full">
      <h3 className="section-title">Top Products</h3>
      {loading ? <PageLoader /> : (
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={data} layout="vertical" margin={{ top: 0, right: 10, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1E2D47" horizontal={false} />
            <XAxis
              type="number" tick={{ fill: '#475569', fontSize: 10 }}
              tickFormatter={(v) => `${(v/1000).toFixed(0)}K`}
              axisLine={false} tickLine={false}
            />
            <YAxis
              type="category" dataKey="name"
              tick={{ fill: '#94A3B8', fontSize: 10 }}
              width={100}
              tickFormatter={(v) => v.length > 14 ? v.substring(0, 14) + '…' : v}
              axisLine={false} tickLine={false}
            />
            <Tooltip
              contentStyle={{ background: '#131C2E', border: '1px solid #1E2D47', borderRadius: 12, fontSize: 11 }}
              formatter={(v) => [`EGP ${v.toLocaleString()}`, 'Revenue']}
            />
            <Bar dataKey="revenue" radius={[0, 4, 4, 0]} maxBarSize={12}>
              {data.map((_, i) => (
                <Cell
                  key={i}
                  fill={i === 0 ? '#6366F1' : i === 1 ? '#8B5CF6' : i === 2 ? '#0EA5E9' : '#1E2D47'}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}

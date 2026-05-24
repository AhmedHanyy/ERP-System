import { useState, useEffect } from 'react'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { dashboardApi } from '@/services/api'
import { PageLoader } from '@/components/shared/States'

const COLORS = {
  'Delivered':  '#10B981',
  'Shipped':    '#6366F1',
  'Preparing':  '#0EA5E9',
  'Pending':    '#475569',
  'Cancelled':  '#F43F5E',
}

const CustomLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent }) => {
  if (percent < 0.05) return null
  const RADIAN = Math.PI / 180
  const radius = innerRadius + (outerRadius - innerRadius) * 0.5
  const x = cx + radius * Math.cos(-midAngle * RADIAN)
  const y = cy + radius * Math.sin(-midAngle * RADIAN)
  return (
    <text x={x} y={y} fill="white" textAnchor="middle" dominantBaseline="central" fontSize={11} fontWeight={600}>
      {`${(percent * 100).toFixed(0)}%`}
    </text>
  )
}

export default function OrderStatusChart() {
  const [data,    setData]    = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    dashboardApi.getOrderStatus()
      .then(d => { setData(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  const total = data.reduce((s, d) => s + d.count, 0)

  return (
    <div className="glass-card p-6 h-full">
      <div className="mb-4">
        <h3 className="section-title mb-0">Order Status</h3>
        <p className="text-xs text-text-secondary mt-0.5">{total.toLocaleString()} total orders</p>
      </div>

      {loading ? <PageLoader /> : (
        <>
          <ResponsiveContainer width="100%" height={180}>
            <PieChart>
              <Pie
                data={data} dataKey="count" nameKey="status"
                cx="50%" cy="50%" innerRadius={45} outerRadius={75}
                paddingAngle={2} labelLine={false} label={CustomLabel}
              >
                {data.map((entry) => (
                  <Cell key={entry.status} fill={COLORS[entry.status] || '#6366F1'} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ background: '#131C2E', border: '1px solid #1E2D47', borderRadius: 12, fontSize: 12 }}
                labelStyle={{ color: '#94A3B8' }} itemStyle={{ color: '#F1F5F9' }}
              />
            </PieChart>
          </ResponsiveContainer>

          <div className="space-y-2 mt-2">
            {data.map(d => (
              <div key={d.status} className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full" style={{ background: COLORS[d.status] || '#6366F1' }} />
                  <span className="text-text-secondary">{d.status}</span>
                </div>
                <span className="text-text-primary font-medium">{d.count.toLocaleString()}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

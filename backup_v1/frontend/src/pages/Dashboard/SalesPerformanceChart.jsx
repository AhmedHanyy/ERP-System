import { useState, useEffect } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { dashboardApi } from '@/services/api'
import { PageLoader } from '@/components/shared/States'

export default function SalesPerformanceChart() {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    dashboardApi.getSalesTrend('30d').then(d => {
      setData(d)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  if (loading) return <PageLoader />

  return (
    <div className="h-full">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h3 className="section-title mb-0">Sales Performance</h3>
          <p className="text-xs text-text-muted">Net revenue generated over time</p>
        </div>
        <select className="bg-bg-hover text-[11px] font-bold py-1 px-2 rounded-lg border-none outline-none cursor-pointer">
           <option>Last 30 Days</option>
           <option>Last 6 Months</option>
        </select>
      </div>

      <div className="h-[280px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" vertical={false} />
            <XAxis 
              dataKey="date" 
              tick={{ fill: '#94A3B8', fontSize: 10 }} 
              axisLine={false} 
              tickLine={false}
              tickFormatter={(v) => {
                const d = new Date(v)
                return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
              }}
            />
            <YAxis 
              tick={{ fill: '#94A3B8', fontSize: 10 }} 
              axisLine={false} 
              tickLine={false} 
              tickFormatter={(v) => `EGP ${v/1000}K`}
            />
            <Tooltip 
              contentStyle={{ background: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: 12, boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}
              labelStyle={{ fontWeight: 'bold', fontSize: 12, color: '#0F172A' }}
              itemStyle={{ fontSize: 12, color: '#2563EB' }}
            />
            <Line 
              type="monotone" 
              dataKey="revenue" 
              stroke="#2563EB" 
              strokeWidth={3} 
              dot={{ r: 4, fill: '#FFFFFF', stroke: '#2563EB', strokeWidth: 2 }}
              activeDot={{ r: 6, fill: '#2563EB', stroke: '#FFFFFF', strokeWidth: 2 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

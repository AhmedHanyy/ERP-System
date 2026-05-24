import { useState, useEffect } from 'react'
import { dashboardApi } from '@/services/api'

export default function TopSKUProgress() {
  const [data, setData] = useState([])

  useEffect(() => {
    dashboardApi.getTopProducts().then(d => {
      setData(d.slice(0, 3))
    })
  }, [])

  return (
    <div className="glass-card p-6">
      <h3 className="text-xs font-bold text-text-muted uppercase tracking-widest mb-6">Top Performing SKUs</h3>
      <div className="flex flex-col md:flex-row gap-8">
        {data.map((item, idx) => (
          <div key={item.id || idx} className="flex-1 space-y-2">
            <div className="flex justify-between items-center mb-1">
              <p className="text-sm font-semibold text-text-primary truncate max-w-[150px]">{item.name || 'Unknown SKU'}</p>
              <p className="text-xs font-bold text-text-primary">{item.revenue ? (item.revenue >= 1000 ? `${(item.revenue/1000).toFixed(1)}k` : item.revenue) : 0} EGP</p>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden">
              <div 
                className="h-full bg-brand-400 rounded-full transition-all duration-1000"
                style={{ width: `${Math.min(100, (item.revenue / (data[0]?.revenue || 1)) * 100)}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

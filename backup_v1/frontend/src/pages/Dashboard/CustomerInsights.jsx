import { useState, useEffect } from 'react'
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts'
import { analyticsApi } from '@/services/api'

export default function CustomerInsights() {
  const [data, setData] = useState({ segments: [] })

  useEffect(() => {
    analyticsApi.getRFM().then(d => {
      setData(d)
    }).catch(() => {})
  }, [])

  const COLORS = ['#2563EB', '#CBD5E1']
  const chartData = [
    { name: 'Recurring', value: 70 },
    { name: 'Acquisition', value: 30 }
  ]

  return (
    <div className="glass-card p-6 h-full flex flex-col">
      <h3 className="section-title">Customer Insights</h3>
      
      <div className="flex-1 flex flex-col items-center justify-center py-4">
        <div className="relative w-32 h-32 mb-6">
           <ResponsiveContainer width="100%" height="100%">
             <PieChart>
               <Pie
                 data={chartData}
                 innerRadius={45}
                 outerRadius={60}
                 paddingAngle={0}
                 dataKey="value"
                 stroke="none"
               >
                 {chartData.map((entry, index) => (
                   <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                 ))}
               </Pie>
             </PieChart>
           </ResponsiveContainer>
           <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-3xl font-bold text-text-primary">70%</span>
              <span className="text-[10px] text-text-muted uppercase font-bold">Retention</span>
           </div>
        </div>

        <div className="flex gap-6 mb-8 text-[11px] font-bold">
           <div className="flex items-center gap-2">
             <div className="w-2.5 h-2.5 rounded-full bg-brand-600" />
             <span className="text-text-secondary">Recurring</span>
           </div>
           <div className="flex items-center gap-2">
             <div className="w-2.5 h-2.5 rounded-full bg-slate-300" />
             <span className="text-text-secondary">Acquisition</span>
           </div>
        </div>
      </div>

      <div className="space-y-4">
         <p className="text-[10px] font-bold text-text-muted uppercase tracking-widest">Key Accounts</p>
         <div className="space-y-3">
           {[{name: 'Omar Mansour', orders: 15}, {name: 'Amira Hassan', orders: 12}].map(acc => (
             <div key={acc.name} className="flex items-center gap-3">
                <div className="w-7 h-7 rounded-full bg-brand-100 flex items-center justify-center text-[10px] font-bold text-brand-600">
                   {acc.name.split(' ').map(n => n[0]).join('')}
                </div>
                <p className="text-[13px] font-bold text-text-primary flex-1">{acc.name}</p>
                <p className="text-[11px] font-bold text-accent-emerald">{acc.orders} orders</p>
             </div>
           ))}
         </div>
      </div>
    </div>
  )
}

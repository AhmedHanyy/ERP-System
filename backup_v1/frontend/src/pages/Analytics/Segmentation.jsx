import { useState, useEffect } from 'react'
import { analyticsApi } from '@/services/api'
import { PageLoader, ErrorState } from '@/components/shared/States'
import { 
  ScatterChart, Scatter, XAxis, YAxis, ZAxis, CartesianGrid, 
  Tooltip, ResponsiveContainer, Cell, PieChart, Pie
} from 'recharts'
import { Users, Target, Info, Search } from 'lucide-react'
import StatusBadge from '@/components/shared/StatusBadge'

export default function Segmentation() {
  const [data,     setData]     = useState(null)
  const [loading,  setLoading]  = useState(true)
  const [error,    setError]    = useState(null)

  useEffect(() => {
    analyticsApi.getRFM()
      .then(d => { setData(d); setLoading(false) })
      .catch(() => { setError('Failed to run RFM clustering'); setLoading(false) })
  }, [])

  if (loading) return <PageLoader />
  if (error)   return <ErrorState message={error} />

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* RFM Scatter Plot */}
        <div className="lg:col-span-2 glass-card p-6">
           <div className="flex items-center justify-between mb-6">
             <h3 className="section-title flex items-center gap-2">
               <Target className="w-4 h-4 text-accent-emerald" />
               Frequency vs Monetary Distribution
             </h3>
           </div>
           
           <div className="h-[350px]">
             <ResponsiveContainer width="100%" height="100%">
                <ScatterChart margin={{ top: 10, right: 30, left: 0, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" vertical={false} />
                  <XAxis 
                    type="number" dataKey="frequency" name="Frequency" 
                    tick={{ fill: '#94A3B8', fontSize: 10 }}
                    label={{ value: 'Orders Count', position: 'bottom', fill: '#94A3B8', fontSize: 10 }}
                    axisLine={false} tickLine={false}
                  />
                  <YAxis 
                    type="number" dataKey="monetary" name="Monetary"
                    tick={{ fill: '#94A3B8', fontSize: 10 }}
                    tickFormatter={(v) => `EGP ${v/1000}K`}
                    label={{ value: 'Total Spend', angle: -90, position: 'insideLeft', fill: '#94A3B8', fontSize: 10 }}
                    axisLine={false} tickLine={false}
                  />
                  <ZAxis type="number" range={[40, 400]} />
                  <Tooltip cursor={{ strokeDasharray: '3 3' }} 
                    contentStyle={{ background: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: 12, boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}
                    itemStyle={{ fontSize: 12 }}
                  />
                  <Scatter name="Customers" data={data?.customers || []}>
                     {(data?.customers || []).map((entry, index) => (
                       <Cell 
                         key={`cell-${index}`} 
                         fill={
                           entry.segment === 'Champion' ? '#10B981' :
                           entry.segment === 'Loyal'    ? '#6366F1' :
                           entry.segment === 'At-Risk'  ? '#F59E0B' :
                           '#F43F5E'
                         } 
                       />
                     ))}
                  </Scatter>
               </ScatterChart>
             </ResponsiveContainer>
           </div>
           <p className="text-[10px] text-text-muted mt-4 italic text-center">
             K-Means clusters customers based on scaled Recency, Frequency, and Monetary dimensions.
           </p>
        </div>

        {/* Segment Breakdown */}
        <div className="space-y-6">
          <div className="glass-card p-6 h-full">
            <h3 className="section-title mb-6">Segment Distribution</h3>
            <div className="h-[180px]">
               <ResponsiveContainer width="100%" height="100%">
                 <PieChart>
                     <Pie
                       data={data?.segments || []} dataKey="count" nameKey="segment"
                       cx="50%" cy="50%" innerRadius={40} outerRadius={70}
                       paddingAngle={4}
                     >
                       {(data?.segments || []).map((entry, index) => (
                         <Cell key={`cell-${index}`} fill={entry.color} />
                       ))}
                     </Pie>
                     <Tooltip 
                       contentStyle={{ background: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: 12, fontSize: 12, boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}
                     />
                 </PieChart>
               </ResponsiveContainer>
            </div>
            
            <div className="space-y-3 mt-6">
               {data.segments.map(s => (
                 <div key={s.segment} className="flex items-center justify-between p-3 bg-bg-hover/30 rounded-xl border border-border">
                    <div className="flex items-center gap-3">
                       <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: s.color }} />
                       <div>
                         <p className="text-xs font-bold text-text-primary">{s.segment}</p>
                         <p className="text-[9px] text-text-muted">{s.count} customers</p>
                       </div>
                    </div>
                    <div className="text-right">
                       <p className="text-xs font-bold text-text-primary">EGP {Math.round(s.avg_monetary).toLocaleString()}</p>
                       <p className="text-[9px] text-text-muted">Avg. LTV</p>
                    </div>
                 </div>
               ))}
            </div>
          </div>
        </div>
      </div>

      {/* Segment Descriptions Table */}
      <div className="glass-card overflow-hidden">
         <div className="p-4 border-b border-border bg-bg-hover/20">
            <h3 className="text-xs font-bold text-text-muted uppercase tracking-wider">Segmentation Logic & Descriptions</h3>
         </div>
         <div className="overflow-x-auto">
            <table className="data-table">
               <thead>
                  <tr>
                    <th>Segment</th><th>Definition</th><th>Recency</th><th>Frequency</th><th>Monetary</th>
                  </tr>
               </thead>
               <tbody>
                 {(data?.segments || []).map(s => (
                    <tr key={s.segment}>
                       <td><StatusBadge status={s.segment} /></td>
                       <td className="max-w-[300px] text-xs text-text-secondary leading-relaxed">{s.description}</td>
                       <td className="text-xs font-medium text-text-primary">~{s.avg_recency_days} days</td>
                       <td className="text-xs font-medium text-text-primary">{s.avg_frequency?.toFixed(1) || 0} orders</td>
                       <td className="text-xs font-medium text-accent-emerald">EGP {Math.round(s.avg_monetary || 0).toLocaleString()}</td>
                    </tr>
                 ))}
               </tbody>
            </table>
         </div>
      </div>
    </div>
  )
}

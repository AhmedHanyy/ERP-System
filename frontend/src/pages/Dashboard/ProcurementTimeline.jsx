import { useState, useEffect } from 'react'
import { procurementApi } from '@/services/api'
import { CheckCircle2, Clock, Truck } from 'lucide-react'

export default function ProcurementTimeline() {
  const [data, setData] = useState([])

  useEffect(() => {
    procurementApi.listRequests().then(d => {
      setData(d.slice(0, 3))
    })
  }, [])

  return (
    <div className="glass-card p-6 h-full flex flex-col">
      <div className="flex items-center justify-between mb-6">
        <h3 className="section-title mb-0">Procurement Management</h3>
      </div>

      <div className="flex-1 space-y-6">
        {data.length ? data.map((req, idx) => (
          <div key={req.id} className="relative flex gap-4">
             {/* Timeline Line */}
             {idx < data.length - 1 && <div className="absolute left-[13px] top-7 bottom-[-15px] w-0.5 bg-slate-100" />}
             
             <div className="relative z-10 w-7 h-7 rounded-full bg-white border-2 border-white shadow-sm flex items-center justify-center shrink-0">
                {req.status === 'Received' ? <CheckCircle2 className="w-4 h-4 text-accent-emerald" /> : 
                 req.status === 'Confirmed' ? <Truck className="w-4 h-4 text-brand-600" /> :
                <div className="w-2 h-2 rounded-full bg-accent-amber" />}
             </div>

             <div className="space-y-1">
                <div className="flex items-center gap-2">
                   <p className="text-[13px] font-bold text-text-primary">Request #PR-{req.id + 700}</p>
                   <span className="text-[10px] text-text-muted">{req.status}</span>
                </div>
                <p className="text-[11px] text-text-muted leading-tight">{req.product_name} · {req.supplier_name}</p>
                <div className="mt-2 py-1 px-2 border border-slate-100 rounded-lg bg-slate-50 w-fit">
                   <p className="text-[11px] font-bold text-text-secondary">EGP {req.total_cost?.toLocaleString()}</p>
                </div>
             </div>
          </div>
        )) : (
          <div className="flex flex-col items-center justify-center h-full text-text-muted text-xs">
            No active requests
          </div>
        )}
      </div>

      <button className="w-full btn-secondary mt-6 border-slate-100 text-[11px] font-bold py-2">
         View All Requests
      </button>
    </div>
  )
}

import { useState, useEffect } from 'react'
import { procurementApi } from '@/services/api'
import { PageLoader } from '@/components/shared/States'
import { Phone, PhoneCall, Star, Mail } from 'lucide-react'
import toast from 'react-hot-toast'

export default function SuppliersList() {
  const [suppliers, setSuppliers] = useState([])
  const [loading,   setLoading]   = useState(true)

  useEffect(() => {
    procurementApi.listSuppliers()
      .then(d => { setSuppliers(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  const handleWhatsApp = (number, name) => {
    const text = encodeURIComponent(`Hello ${name}, we would like to inquire about a restock request for SmartERP.`)
    window.open(`https://wa.me/${number.replace(/\+/g, '')}?text=${text}`, '_blank')
    toast.success('Opening WhatsApp...')
  }

  return (
    <div className="glass-card overflow-hidden">
      <div className="p-4 border-b border-border bg-bg-hover/20">
        <h3 className="text-xs font-bold text-text-muted uppercase tracking-wider">Trusted Suppliers</h3>
      </div>
      <div className="p-3 space-y-3 max-h-[400px] overflow-y-auto no-scrollbar">
        {loading ? <PageLoader /> :
         suppliers.map(s => (
          <div key={s.id} className="p-3 bg-bg-hover/40 rounded-xl border border-border group hover:border-brand-500/30 transition-all">
             <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-bg-card border border-border flex items-center justify-center text-xs font-bold text-brand-400">
                  {s.name.charAt(0)}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold truncate text-text-primary">{s.name}</p>
                  <div className="flex items-center gap-1">
                    <Star className="w-3 h-3 text-accent-amber fill-accent-amber" />
                    <span className="text-[10px] font-medium text-text-secondary">{s.rating} · {s.lead_time_days}d lead</span>
                  </div>
                </div>
                <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button 
                    onClick={() => handleWhatsApp(s.whatsapp_number, s.name)}
                    className="p-1.5 bg-green-500/10 text-green-500 rounded-lg hover:bg-green-500 hover:text-white transition-all shadow-sm"
                    title="Contact via WhatsApp"
                  >
                    <Phone className="w-3.5 h-3.5" />
                  </button>
                </div>
             </div>
          </div>
        ))}
      </div>
    </div>
  )
}

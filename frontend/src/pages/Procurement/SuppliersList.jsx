import { useState, useEffect } from 'react'
import { procurementApi } from '@/services/api'
import { PageLoader } from '@/components/shared/States'
import { Phone, Star, Mail, Award, Clock, CheckCircle2, ShieldCheck, X } from 'lucide-react'
import toast from 'react-hot-toast'

export default function SuppliersList() {
  const [suppliers, setSuppliers] = useState([])
  const [loading,   setLoading]   = useState(true)
  const [selectedSupplier, setSelectedSupplier] = useState(null)
  const [modalLoading, setModalLoading] = useState(false)
  const [supplierDetails, setSupplierDetails] = useState(null)

  const fetchSuppliers = () => {
    setLoading(true)
    procurementApi.listSuppliers()
      .then(d => { setSuppliers(d); setLoading(false) })
      .catch(() => setLoading(false))
  }

  useEffect(() => {
    fetchSuppliers()
  }, [])

  const handleWhatsApp = (number, name) => {
    if (!number) return toast.error('No contact number registered')
    const text = encodeURIComponent(`Hello ${name}, we would like to inquire about a restock request for SmartERP.`)
    window.open(`https://wa.me/${number.replace(/\+/g, '')}?text=${text}`, '_blank')
    toast.success('Opening WhatsApp...')
  }

  const handleSupplierClick = async (supplierId) => {
    setModalLoading(true)
    setSelectedSupplier(supplierId)
    try {
      const data = await procurementApi.getSupplier(supplierId)
      setSupplierDetails(data)
    } catch {
      toast.error('Failed to load supplier performance data')
      setSelectedSupplier(null)
    } finally {
      setModalLoading(false)
    }
  }

  return (
    <div className="glass-card overflow-hidden">
      <div className="p-4 border-b border-border bg-bg-hover/20 flex justify-between items-center">
        <h3 className="text-xs font-bold text-text-muted uppercase tracking-wider">Trusted Suppliers</h3>
        <span className="text-[10px] font-black text-brand-500 uppercase tracking-tight">Performance Ranked</span>
      </div>
      <div className="p-3 space-y-3 max-h-[400px] overflow-y-auto no-scrollbar">
        {loading ? <PageLoader /> :
         suppliers.map(s => (
          <div 
            key={s.id} 
            onClick={() => handleSupplierClick(s.id)}
            className="p-3 bg-bg-hover/40 rounded-xl border border-border group hover:border-brand-500/30 transition-all cursor-pointer flex items-center justify-between"
          >
             <div className="flex items-center gap-3 min-w-0 flex-1">
                <div className="w-10 h-10 rounded-lg bg-bg-card border border-border flex items-center justify-center text-xs font-bold text-brand-400 shrink-0 relative">
                  {s.name.charAt(0)}
                  <span className="absolute -top-1.5 -left-1.5 px-1 py-0.5 bg-slate-800 text-slate-100 text-[8px] font-black rounded border border-slate-700">
                    #{s.rank || '—'}
                  </span>
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-semibold truncate text-text-primary">{s.name}</p>
                  <div className="flex items-center gap-2">
                    <div className="flex items-center gap-0.5">
                      <Star className="w-3 h-3 text-accent-amber fill-accent-amber" />
                      <span className="text-[10px] font-medium text-text-secondary">{s.rating}</span>
                    </div>
                    <span className="text-text-muted text-[10px]">·</span>
                    <span className="text-[10px] text-text-muted">{s.lead_time_days}d lead</span>
                  </div>
                </div>
             </div>
             
             <div className="text-right shrink-0 flex items-center gap-3">
                <div>
                   <p className="text-xs font-black text-emerald-600 dark:text-emerald-400">{s.overall_score}%</p>
                   <p className="text-[8px] font-black text-text-muted uppercase tracking-tighter">Score</p>
                </div>
                <button 
                  onClick={(e) => { e.stopPropagation(); handleWhatsApp(s.whatsapp_number, s.name); }}
                  className="p-1.5 bg-green-500/10 text-green-500 rounded-lg hover:bg-green-500 hover:text-white transition-all shadow-sm opacity-0 group-hover:opacity-100 shrink-0"
                  title="Contact via WhatsApp"
                >
                  <Phone className="w-3.5 h-3.5" />
                </button>
             </div>
          </div>
        ))}
      </div>

      {/* PERFORMANCE DETAIL MODAL */}
      {selectedSupplier && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-bg-primary/80 backdrop-blur-sm" onClick={() => setSelectedSupplier(null)}>
          <div 
            className="w-full max-w-lg bg-bg-secondary border border-border shadow-2xl rounded-2xl animate-scale-in overflow-hidden"
            onClick={e => e.stopPropagation()}
          >
            <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-bg-hover/20">
              <h2 className="text-lg font-semibold flex items-center gap-2 text-text-primary">
                <Award className="w-5 h-5 text-brand-500" />
                Supplier Performance Scorecard
              </h2>
              <button onClick={() => setSelectedSupplier(null)} className="p-2 rounded-xl hover:bg-bg-hover transition-colors">
                <X className="w-4 h-4" />
              </button>
            </div>
            
            {modalLoading || !supplierDetails ? (
              <div className="p-12"><PageLoader /></div>
            ) : (
              <div className="p-6 space-y-6">
                {/* Header Profile */}
                <div className="flex items-center gap-4">
                  <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-600 text-white flex items-center justify-center font-black text-xl shadow-lg">
                    {supplierDetails.name.slice(0, 2).toUpperCase()}
                  </div>
                  <div>
                    <h3 className="text-xl font-black text-text-primary">{supplierDetails.name}</h3>
                    <p className="text-xs text-text-muted font-medium">Ranked #{supplierDetails.rank} of Trusted Suppliers</p>
                  </div>
                </div>

                {/* Score breakdown grid */}
                <div className="grid grid-cols-3 gap-4">
                  <div className="glass-card p-4 text-center">
                    <CheckCircle2 className="w-5 h-5 text-emerald-500 mx-auto mb-2" />
                    <p className="text-lg font-black text-text-primary">{supplierDetails.reliability_score}%</p>
                    <p className="text-[9px] font-black text-text-muted uppercase tracking-tight mt-0.5">Reliability</p>
                  </div>
                  <div className="glass-card p-4 text-center">
                    <Clock className="w-5 h-5 text-blue-500 mx-auto mb-2" />
                    <p className="text-lg font-black text-text-primary">{supplierDetails.lead_time_score}%</p>
                    <p className="text-[9px] font-black text-text-muted uppercase tracking-tight mt-0.5">Lead Time</p>
                  </div>
                  <div className="glass-card p-4 text-center">
                    <ShieldCheck className="w-5 h-5 text-purple-500 mx-auto mb-2" />
                    <p className="text-lg font-black text-text-primary">{supplierDetails.cost_score}%</p>
                    <p className="text-[9px] font-black text-text-muted uppercase tracking-tight mt-0.5">Cost Stability</p>
                  </div>
                </div>

                {/* Overall big card */}
                <div className="p-4 bg-brand-500/5 border border-brand-500/10 rounded-2xl flex justify-between items-center">
                  <div>
                    <h4 className="text-sm font-bold text-text-primary">Weighted Scorecard Rating</h4>
                    <p className="text-[10px] text-text-muted mt-0.5">Weighted average of reliability, lead time and costs.</p>
                  </div>
                  <div className="text-right">
                    <p className="text-2xl font-black text-brand-500">{supplierDetails.overall_score}%</p>
                    <p className="text-[8px] font-black text-text-muted uppercase tracking-widest mt-0.5">Operational Score</p>
                  </div>
                </div>

                {/* Contact information details */}
                <div className="space-y-3">
                  <h4 className="text-xs font-bold text-text-muted uppercase tracking-wider">Contact & Logistics</h4>
                  <div className="grid grid-cols-2 gap-4 text-xs">
                    <div className="p-3 bg-bg-body rounded-xl border border-border-main">
                      <p className="text-text-muted font-semibold">Average Lead Time</p>
                      <p className="font-bold text-text-primary mt-1">{supplierDetails.lead_time_days} Business Days</p>
                    </div>
                    <div className="p-3 bg-bg-body rounded-xl border border-border-main">
                      <p className="text-text-muted font-semibold">Total Orders Processed</p>
                      <p className="font-bold text-text-primary mt-1">{supplierDetails.total_orders} Orders</p>
                    </div>
                  </div>
                </div>

                {/* WhatsApp Action button */}
                <div className="pt-2">
                  <button 
                    onClick={() => handleWhatsApp(supplierDetails.whatsapp_number, supplierDetails.name)}
                    className="w-full py-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2 shadow-lg shadow-emerald-600/15"
                  >
                    <Phone className="w-4 h-4" /> Message Supplier on WhatsApp
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

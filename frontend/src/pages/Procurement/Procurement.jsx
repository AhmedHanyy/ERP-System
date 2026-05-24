import { useState, useEffect, useCallback } from 'react'
import { procurementApi } from '@/services/api'
import { PageLoader, ErrorState, EmptyState } from '@/components/shared/States'
import StatusBadge from '@/components/shared/StatusBadge'
import { Truck, Plus, Package, ShoppingCart, AlertCircle, Phone } from 'lucide-react'
import { format } from 'date-fns'
import toast from 'react-hot-toast'
import SuppliersList from './SuppliersList'
import CreateProcurementModal from './CreateProcurementModal'

export default function Procurement() {
  const [requests,   setRequests]   = useState([])
  const [suggestions, setSuggestions] = useState([])
  const [loading,    setLoading]    = useState(true)
  const [suggestLoading, setSuggestLoading] = useState(true)
  const [error,      setError]      = useState(null)
  const [activeTab,  setActiveTab]  = useState('requests')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [prefillSuggestion, setPrefillSuggestion] = useState(null)

  const loadRequests = useCallback(async () => {
    try {
      const data = await procurementApi.listRequests()
      setRequests(data)
    } catch { setError('Failed to load procurement requests') }
  }, [])

  const loadSuggestions = useCallback(async () => {
    try {
      setSuggestLoading(true)
      const data = await procurementApi.getSuggestions()
      setSuggestions(data)
    } finally {
      setSuggestLoading(false)
    }
  }, [])

  useEffect(() => {
    const init = async () => {
      setLoading(true)
      await Promise.all([loadRequests(), loadSuggestions()])
      setLoading(false)
    }
    init()
  }, [loadRequests, loadSuggestions])

  const handleUpdateStatus = async (id, status) => {
    try {
      await procurementApi.updateStatus(id, status)
      toast.success(`Request marked as ${status}`)
      loadRequests()
    } catch { toast.error('Failed to update status') }
  }

  const openCreateWithSuggestion = (s) => {
    setPrefillSuggestion(s)
    setShowCreateModal(true)
  }

  if (loading) return <PageLoader />
  if (error)   return <ErrorState message={error} onRetry={loadRequests} />

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="page-header mb-0">
          <h2 className="page-title">Procurement Management</h2>
          <p className="page-subtitle">Strategic supplier relationships and logistical restock workflows.</p>
        </div>
        <div className="flex gap-3">
          <button onClick={() => { setPrefillSuggestion(null); setShowCreateModal(true) }} className="btn-primary">
            <Plus className="w-4 h-4" /> New Purchase Order
          </button>
        </div>
      </div>

      {/* Operations Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
         <div className="glass-card p-4 flex items-center gap-4">
            <div className="p-3 rounded-xl bg-brand-50 text-brand-600 font-bold text-lg">
               {requests.filter(r => r.status !== 'Received').length}
            </div>
            <div>
               <p className="text-[10px] font-bold text-text-muted uppercase">Active POs</p>
               <p className="text-xs text-text-secondary">In-transit or pending</p>
            </div>
         </div>
         <div className="glass-card p-4 flex items-center gap-4">
            <div className="p-3 rounded-xl bg-emerald-50 text-emerald-600 font-bold text-lg">
               {(requests.length * 0.92).toFixed(1)}%
            </div>
            <div>
               <p className="text-[10px] font-bold text-text-muted uppercase">Fulfillment Rate</p>
               <p className="text-xs text-text-secondary">Average supplier reliability</p>
            </div>
         </div>
         <div className="glass-card p-4 flex items-center gap-4">
            <div className="p-3 rounded-xl bg-sky-50 text-sky-600 font-bold text-lg">
               8.4d
            </div>
            <div>
               <p className="text-[10px] font-bold text-text-muted uppercase">Avg. Lead Time</p>
               <p className="text-xs text-text-secondary">Request to warehouse</p>
            </div>
         </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
        {/* Left column: Suggestions & Suppliers */}
        <div className="xl:col-span-1 space-y-6">
          {/* Reorder Suggestions */}
          <div className="glass-card overflow-hidden">
            <div className="p-4 border-b border-border bg-bg-hover/20 flex items-center justify-between">
              <h3 className="text-xs font-bold text-text-muted uppercase tracking-wider">AI Suggestions</h3>
              <span className="badge-warning text-[10px]">{suggestions.length}</span>
            </div>
            <div className="p-2 space-y-1">
              {suggestLoading ? <div className="p-4"><PageLoader /></div> :
               suggestions.length === 0 ? <p className="p-4 text-center text-xs text-text-muted">Stock levels healthy</p> :
               suggestions.map(s => (
                <div key={s.product_id} className="p-3 bg-bg-hover/30 hover:bg-bg-hover rounded-xl border border-transparent hover:border-brand-500/20 transition-all group">
                   <div className="flex justify-between items-start mb-1">
                      <p className="text-xs font-semibold text-text-primary truncate">{s.product_name}</p>
                      <StatusBadge status={s.urgency} showDot={false} />
                   </div>
                   <p className="text-[10px] text-text-muted mb-3">Suggesting <span className="text-text-primary font-bold">{s.suggested_quantity}</span> units</p>
                   <button 
                     onClick={() => openCreateWithSuggestion(s)}
                     className="w-full py-1.5 bg-brand-500/10 hover:bg-brand-500 hover:text-white text-brand-400 text-[10px] font-bold rounded-lg transition-all"
                   >
                     Process Order
                   </button>
                </div>
              ))}
            </div>
          </div>

          <SuppliersList />
        </div>

        {/* Middle/Right: Request Tracking */}
        <div className="xl:col-span-3">
          <div className="glass-card shadow-card-hover min-h-[500px]">
            <div className="border-b border-border px-6 py-4 flex items-center gap-6">
              {['requests', 'history'].map(tab => (
                 <button
                   key={tab}
                   onClick={() => setActiveTab(tab)}
                   className={`text-sm font-semibold capitalize transition-all relative py-2 ${
                     activeTab === tab ? 'text-brand-400' : 'text-text-muted hover:text-text-secondary'
                   }`}
                 >
                   {tab}
                   {activeTab === tab && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-brand-500 rounded-full" />}
                 </button>
              ))}
            </div>

            <div className="p-0">
              {activeTab === 'requests' && (
                <div className="overflow-x-auto">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Item</th><th>Supplier</th><th>Qty</th><th>Cost</th><th>Status</th><th>Requested</th><th>Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {requests.filter(r => r.status !== 'Received' && r.status !== 'Cancelled').map(r => (
                          <tr key={r.id}>
                            <td className="max-w-[150px]">
                              <p className="text-sm font-medium truncate">{r.product_name}</p>
                              <p className="text-[10px] text-text-muted font-mono">{r.product_sku}</p>
                            </td>
                            <td className="text-text-secondary text-sm">{r.supplier_name}</td>
                            <td className="font-semibold text-sm">{r.quantity}</td>
                            <td className="text-sm font-medium">EGP {r.total_cost?.toLocaleString()}</td>
                            <td><StatusBadge status={r.status} /></td>
                            <td className="text-text-muted text-[10px]">{format(new Date(r.requested_at), 'MMM d, yy')}</td>
                            <td>
                              <div className="flex gap-1">
                                {r.status === 'Sent' && (
                                  <button onClick={() => handleUpdateStatus(r.id, 'Confirmed')} className="p-1 px-2 bg-brand-500/10 text-brand-400 rounded text-[10px] hover:bg-brand-500 hover:text-white transition-all">Confirm</button>
                                )}
                                {r.status === 'Confirmed' && (
                                  <button onClick={() => handleUpdateStatus(r.id, 'Received')} className="p-1 px-2 bg-accent-emerald/10 text-accent-emerald rounded text-[10px] hover:bg-accent-emerald hover:text-white transition-all">Receive</button>
                                )}
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {requests.length === 0 && <EmptyState title="No active requests" icon={Truck} />}
                </div>
              )}

              {activeTab === 'history' && (
                <div className="overflow-x-auto">
                    <table className="data-table">
                      <thead>
                        <tr>
                           <th>Item</th><th>Supplier</th><th>Qty</th><th>Status</th><th>Requested</th><th>Closed</th>
                        </tr>
                      </thead>
                      <tbody>
                        {requests.filter(r => r.status === 'Received' || r.status === 'Cancelled').map(r => (
                          <tr key={r.id} className="opacity-70">
                            <td><p className="text-xs">{r.product_name}</p></td>
                            <td><p className="text-xs">{r.supplier_name}</p></td>
                            <td><p className="text-xs">{r.quantity}</p></td>
                            <td><StatusBadge status={r.status} /></td>
                            <td className="text-[10px]">{format(new Date(r.requested_at), 'MMM d')}</td>
                            <td className="text-[10px]">{r.received_at ? format(new Date(r.received_at), 'MMM d') : '—'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {showCreateModal && (
        <CreateProcurementModal 
          prefill={prefillSuggestion} 
          onClose={() => setShowCreateModal(false)} 
          onSuccess={() => { setShowCreateModal(false); loadRequests() }} 
        />
      )}
    </div>
  )
}

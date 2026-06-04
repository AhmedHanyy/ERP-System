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
  const [suggMeta,    setSuggMeta]   = useState(null)
  const [loading,    setLoading]    = useState(true)
  const [suggestLoading, setSuggestLoading] = useState(true)
  const [error,      setError]      = useState(null)
  const [activeTab,  setActiveTab]  = useState('requests')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [prefillSuggestion, setPrefillSuggestion] = useState(null)
  
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(1)
  const [total, setTotal] = useState(0)
  const [stats, setStats] = useState([])

  const loadRequests = useCallback(async () => {
    try {
      const statusFilter = activeTab === 'requests' ? 'Draft,Sent,Confirmed' : 'Received,Cancelled';
      const [res, statsData] = await Promise.all([
        procurementApi.listRequests({ page, per_page: 20, status: statusFilter }),
        procurementApi.getStats()
      ]);
      setRequests(res.requests || []);
      setPages(res.pages || 1);
      setTotal(res.total || 0);
      setStats(statsData || []);
    } catch { setError('Failed to load procurement requests') }
  }, [page, activeTab])

  const loadSuggestions = useCallback(async () => {
    try {
      setSuggestLoading(true)
      const data = await procurementApi.getSuggestions()
      // Handle new API format: { suggestions: [...], meta: {...} }
      if (data && data.suggestions) {
        setSuggestions(data.suggestions)
        setSuggMeta(data.meta || null)
      } else if (Array.isArray(data)) {
        // Fallback for old format
        setSuggestions(data)
        setSuggMeta(null)
      } else {
        setSuggestions([])
      }
    } catch(e) {
      setSuggestions([])
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

  const handleTabChange = (tab) => {
    setActiveTab(tab)
    setPage(1)
  }

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
               {stats.filter(s => ['Draft', 'Sent', 'Confirmed'].includes(s.status)).reduce((a, b) => a + b.count, 0)}
            </div>
            <div>
               <p className="text-[10px] font-bold text-text-muted uppercase">Active POs</p>
               <p className="text-xs text-text-secondary">In-transit or pending</p>
            </div>
         </div>
         <div className="glass-card p-4 flex items-center gap-4">
            <div className="p-3 rounded-xl bg-emerald-50 text-emerald-600 font-bold text-lg">
               {(() => {
                  const rec = stats.find(s => s.status === 'Received')?.count || 0;
                  const can = stats.find(s => s.status === 'Cancelled')?.count || 0;
                  return rec + can > 0 ? ((rec / (rec + can)) * 100).toFixed(1) + '%' : '100.0%';
               })()}
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
              <span className="badge-warning text-[10px]">{suggestions.length} Active</span>
            </div>

            {/* Audit breakdown */}
            {suggMeta && (
              <div className="px-3 py-2 bg-bg-hover/10 border-b border-border/50 grid grid-cols-2 gap-2">
                <div className="p-1.5 bg-rose-500/5 border border-rose-500/10 rounded-lg text-center">
                  <p className="text-[9px] text-text-muted uppercase">Out of Stock</p>
                  <p className="text-sm font-black text-rose-400">{suggMeta.out_of_stock}</p>
                </div>
                <div className="p-1.5 bg-amber-500/5 border border-amber-500/10 rounded-lg text-center">
                  <p className="text-[9px] text-text-muted uppercase">Low Stock</p>
                  <p className="text-sm font-black text-amber-400">{suggMeta.low_stock}</p>
                </div>
                <div className="col-span-2 p-1.5 bg-slate-500/5 border border-slate-500/10 rounded-lg">
                  <p className="text-[9px] text-text-muted">Dead stock suppressed: <span className="font-bold text-text-secondary">{suggMeta.dead_stock_suppressed}</span> (no sales in 60d)</p>
                </div>
              </div>
            )}

            <div className="p-2 space-y-1 max-h-[500px] overflow-y-auto">
              {suggestLoading ? <div className="p-4"><PageLoader /></div> :
               suggestions.length === 0 ? <p className="p-4 text-center text-xs text-text-muted">No active reorder suggestions</p> :
                suggestions.map(s => (
                 <div key={s.product_id} className="p-3 bg-bg-hover/30 hover:bg-bg-hover rounded-xl border border-transparent hover:border-brand-500/20 transition-all group">
                    <div className="flex justify-between items-start mb-1">
                       <p className="text-xs font-semibold text-text-primary truncate">{s.product_name || s.name}</p>
                       <StatusBadge status={s.priority || s.urgency} showDot={false} />
                    </div>
                    <div className="space-y-1 my-2 text-[10px] text-text-secondary leading-normal">
                       <p>Stock: <span className="text-rose-400 font-bold">{s.current_stock}</span> / Reorder at: {s.reorder_point}</p>
                       <p>Velocity: <span className="text-text-primary font-bold">{s.velocity_60d}</span> units / 60d</p>
                       <p>Suggest: <span className="text-text-primary font-bold">{s.suggested_qty || s.suggested_quantity}</span> units</p>
                       <p>Supplier: <span className="text-brand-500 font-bold">{s.supplier_name || 'None'}</span></p>
                       {s.estimated_cost && <p>Est. Cost: <span className="text-text-primary font-bold">EGP {s.estimated_cost?.toLocaleString()}</span></p>}
                    </div>
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
                   onClick={() => handleTabChange(tab)}
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
                        {requests.map(r => (
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
                              <div className="flex gap-1.5 flex-wrap">
                                {r.status === 'Draft' && (
                                  <>
                                    <button onClick={() => handleUpdateStatus(r.id, 'Sent')} className="p-1 px-2.5 bg-blue-500/10 text-blue-400 rounded-lg text-[10px] font-bold hover:bg-blue-50 hover:text-white transition-all">Send</button>
                                    <button onClick={() => handleUpdateStatus(r.id, 'Cancelled')} className="p-1 px-2 bg-rose-500/10 text-rose-400 rounded-lg text-[10px] font-bold hover:bg-rose-500 hover:text-white transition-all">Cancel</button>
                                  </>
                                )}
                                {r.status === 'Sent' && (
                                  <>
                                    <button onClick={() => handleUpdateStatus(r.id, 'Confirmed')} className="p-1 px-2.5 bg-brand-500/10 text-brand-400 rounded-lg text-[10px] font-bold hover:bg-brand-500 hover:text-white transition-all">Confirm</button>
                                    <button onClick={() => handleUpdateStatus(r.id, 'Cancelled')} className="p-1 px-2 bg-rose-500/10 text-rose-400 rounded-lg text-[10px] font-bold hover:bg-rose-500 hover:text-white transition-all">Cancel</button>
                                  </>
                                )}
                                {r.status === 'Confirmed' && (
                                  <>
                                    <button onClick={() => handleUpdateStatus(r.id, 'Received')} className="p-1 px-2.5 bg-emerald-500/10 text-emerald-500 rounded-lg text-[10px] font-bold hover:bg-emerald-500 hover:text-white transition-all">Receive</button>
                                    <button onClick={() => handleUpdateStatus(r.id, 'Cancelled')} className="p-1 px-2 bg-rose-500/10 text-rose-400 rounded-lg text-[10px] font-bold hover:bg-rose-500 hover:text-white transition-all">Cancel</button>
                                  </>
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
                        {requests.map(r => (
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

            {/* Pagination Controls */}
            {pages > 1 && (
              <div className="flex items-center justify-between border-t border-border px-6 py-4">
                <span className="text-xs text-text-muted">Showing page {page} of {pages} ({total} requests)</span>
                <div className="flex gap-2">
                  <button className="btn-secondary py-1.5 px-3 text-xs" onClick={() => setPage(p => Math.max(1, p-1))} disabled={page === 1}>Prev</button>
                  <button className="btn-secondary py-1.5 px-3 text-xs" onClick={() => setPage(p => Math.min(pages, p+1))} disabled={page === pages}>Next</button>
                </div>
              </div>
            )}
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

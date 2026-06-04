import { useState, useEffect, useCallback } from 'react'
import { ordersApi } from '@/services/api'
import { PageLoader, ErrorState, EmptyState } from '@/components/shared/States'
import StatusBadge from '@/components/shared/StatusBadge'
import { Search, Filter, ChevronLeft, ChevronRight, Eye } from 'lucide-react'
import { format } from 'date-fns'
import toast from 'react-hot-toast'
import OrderDetailModal from './OrderDetailModal'

const STATUSES = ['', 'Pending', 'Preparing', 'Shipped', 'Delivered', 'Cancelled']

export default function Orders() {
  const [orders,     setOrders]     = useState([])
  const [total,      setTotal]      = useState(0)
  const [pages,      setPages]      = useState(1)
  const [page,       setPage]       = useState(1)
  const [loading,    setLoading]    = useState(true)
  const [error,      setError]      = useState(null)
  const [search,     setSearch]     = useState('')
  const [status,     setStatus]     = useState('')
  const [selectedId, setSelectedId] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await ordersApi.list({ page, per_page: 20, search, status })
      setOrders(data.orders)
      setTotal(data.total)
      setPages(data.pages)
    } catch { setError('Failed to load orders') }
    finally { setLoading(false) }
  }, [page, search, status])

  useEffect(() => { load() }, [load])

  const handleStatusUpdate = async (orderId, newStatus) => {
    try {
      await ordersApi.updateStatus(orderId, newStatus)
      toast.success(`Order updated to ${newStatus}`)
      load()
    } catch { toast.error('Failed to update status') }
  }

  return (
    <div className="space-y-6">
      <div className="page-header">
        <h2 className="page-title">Orders Management</h2>
        <p className="page-subtitle">{total.toLocaleString()} total orders</p>
      </div>

      {/* Filters */}
      <div className="glass-card p-4 flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
          <input
            id="orders-search"
            className="input pl-10"
            placeholder="Search by order #, customer name or email..."
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(1) }}
          />
        </div>
        <select
          id="orders-status-filter"
          className="select w-40"
          value={status}
          onChange={e => { setStatus(e.target.value); setPage(1) }}
        >
          {STATUSES.map(s => <option key={s} value={s}>{s || 'All Statuses'}</option>)}
        </select>
      </div>

      {/* Table */}
      <div className="glass-card overflow-hidden">
        {loading ? <div className="p-8"><PageLoader /></div> :
         error   ? <ErrorState message={error} onRetry={load} /> :
         orders.length === 0 ? <EmptyState title="No orders found" subtitle="Try adjusting your filters" icon={Filter} /> : (
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Order #</th><th>Customer</th><th>Items</th>
                  <th>Amount</th><th>Profit</th><th>Status</th><th>Date</th><th></th>
                </tr>
              </thead>
              <tbody>
                {orders.map(o => (
                  <tr key={o.id}>
                    <td><span className="font-mono text-xs text-brand-400">{o.order_number}</span></td>
                    <td>
                      <div>
                        <p className="text-sm font-medium">{o.customer_name}</p>
                        <p className="text-xs text-text-muted">{o.customer_email}</p>
                      </div>
                    </td>
                    <td className="text-text-secondary text-sm">
                      {o.items_count != null
                        ? <span className="font-medium">{o.items_count} {o.items_count === 1 ? 'Item' : 'Items'}</span>
                        : '—'}
                    </td>
                    <td className="font-semibold text-sm">EGP {o.total_amount?.toLocaleString()}</td>
                    <td className="text-accent-emerald text-sm font-medium">EGP {o.profit?.toLocaleString()}</td>
                    <td>
                      <select
                        className="bg-transparent border-none text-xs cursor-pointer outline-none"
                        value={o.status}
                        onChange={e => handleStatusUpdate(o.id, e.target.value)}
                        onClick={e => e.stopPropagation()}
                      >
                        {['Pending','Preparing','Shipped','Delivered','Cancelled'].map(s =>
                          <option key={s} value={s}>{s}</option>
                        )}
                      </select>
                    </td>
                    <td className="text-text-secondary text-xs">
                      {format(new Date(o.created_at), 'MMM d, yy')}
                    </td>
                    <td>
                      <button
                        className="p-1.5 rounded-lg hover:bg-bg-hover transition-colors text-text-muted hover:text-text-primary"
                        onClick={() => setSelectedId(o.id)}
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between text-sm text-text-secondary">
        <span>Showing page {page} of {pages} ({total} orders)</span>
        <div className="flex gap-2">
          <button className="btn-secondary py-1.5 px-3 text-xs" onClick={() => setPage(p => Math.max(1, p-1))} disabled={page === 1}>
            <ChevronLeft className="w-3 h-3" />
          </button>
          <button className="btn-secondary py-1.5 px-3 text-xs" onClick={() => setPage(p => Math.min(pages, p+1))} disabled={page === pages}>
            <ChevronRight className="w-3 h-3" />
          </button>
        </div>
      </div>

      {selectedId && <OrderDetailModal orderId={selectedId} onClose={() => setSelectedId(null)} onStatusUpdate={handleStatusUpdate} />}
    </div>
  )
}

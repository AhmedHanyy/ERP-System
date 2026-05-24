import { useState, useEffect, useCallback } from 'react'
import { customersApi } from '@/services/api'
import { PageLoader, ErrorState, EmptyState } from '@/components/shared/States'
import StatusBadge from '@/components/shared/StatusBadge'
import { Search, Users, Eye, ChevronLeft, ChevronRight } from 'lucide-react'
import { format } from 'date-fns'
import CustomerDetailModal from './CustomerDetailModal'

const SEGMENTS = ['', 'Champion', 'Loyal', 'At-Risk', 'Lost', 'New']

export default function Customers() {
  const [customers, setCustomers] = useState([])
  const [total,     setTotal]     = useState(0)
  const [pages,     setPages]     = useState(1)
  const [page,      setPage]      = useState(1)
  const [loading,   setLoading]   = useState(true)
  const [error,     setError]     = useState(null)
  const [search,    setSearch]    = useState('')
  const [segment,   setSegment]   = useState('')
  const [selectedId, setSelectedId] = useState(null)
  const [segmentStats, setSegmentStats] = useState([])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [data, segs] = await Promise.all([
        customersApi.list({ page, per_page: 20, search, segment }),
        customersApi.segments()
      ])
      setCustomers(data.customers)
      setTotal(data.total)
      setPages(data.pages)
      setSegmentStats(segs)
    } catch { setError('Failed to load customers') }
    finally { setLoading(false) }
  }, [page, search, segment])

  useEffect(() => { load() }, [load])

  const SEGMENT_COLORS = {
    'Champion': 'text-accent-emerald', 'Loyal': 'text-brand-400',
    'At-Risk': 'text-accent-amber',    'Lost': 'text-accent-rose', 'New': 'text-accent-sky'
  }

  return (
    <div className="space-y-6">
      <div className="page-header">
        <h2 className="page-title">Customer Management</h2>
        <p className="page-subtitle">{total.toLocaleString()} customers across all segments</p>
      </div>

      {/* Segment Overview */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {segmentStats.map(s => (
          <button
            key={s.segment}
            className={`glass-card p-4 text-left transition-all duration-200 hover:border-border-light ${segment === s.segment ? 'border-brand-500/40' : ''}`}
            onClick={() => setSegment(segment === s.segment ? '' : s.segment)}
          >
            <p className={`text-2xl font-bold mb-0.5 ${SEGMENT_COLORS[s.segment] || 'text-text-primary'}`}>{s.count}</p>
            <p className="text-xs text-text-secondary">{s.segment}</p>
          </button>
        ))}
      </div>

      {/* Filters */}
      <div className="glass-card p-4 flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
          <input className="input pl-10" placeholder="Search by name or email..."
            value={search} onChange={e => { setSearch(e.target.value); setPage(1) }} />
        </div>
        <select className="select w-36" value={segment} onChange={e => { setSegment(e.target.value); setPage(1) }}>
          {SEGMENTS.map(s => <option key={s} value={s}>{s || 'All Segments'}</option>)}
        </select>
      </div>

      {/* Table */}
      <div className="glass-card overflow-hidden">
        {loading ? <div className="p-8"><PageLoader /></div> :
         error   ? <ErrorState message={error} onRetry={load} /> :
         customers.length === 0 ? <EmptyState title="No customers found" icon={Users} /> : (
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Customer</th><th>City</th><th>Orders</th>
                  <th>Lifetime Value</th><th>Segment</th><th>Joined</th><th></th>
                </tr>
              </thead>
              <tbody>
                {customers.map(c => (
                  <tr key={c.id}>
                    <td>
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-brand-500/20 flex items-center justify-center text-brand-400 text-xs font-bold shrink-0">
                          {c.name?.charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <p className="font-medium text-sm">{c.name}</p>
                          <p className="text-xs text-text-muted">{c.email}</p>
                        </div>
                      </div>
                    </td>
                    <td className="text-text-secondary text-sm">{c.city || '—'}</td>
                    <td className="font-medium">{c.total_orders}</td>
                    <td className="font-semibold text-accent-emerald">EGP {c.lifetime_value?.toLocaleString()}</td>
                    <td><StatusBadge status={c.segment} /></td>
                    <td className="text-text-secondary text-xs">
                      {format(new Date(c.created_at), 'MMM d, yyyy')}
                    </td>
                    <td>
                      <button
                        className="p-1.5 rounded-lg hover:bg-bg-hover transition-colors text-text-muted hover:text-text-primary"
                        onClick={() => setSelectedId(c.id)}
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

      <div className="flex items-center justify-between text-sm text-text-secondary">
        <span>Page {page} of {pages}</span>
        <div className="flex gap-2">
          <button className="btn-secondary py-1.5 px-3 text-xs" onClick={() => setPage(p => Math.max(1,p-1))} disabled={page===1}>
            <ChevronLeft className="w-3 h-3" />
          </button>
          <button className="btn-secondary py-1.5 px-3 text-xs" onClick={() => setPage(p => Math.min(pages,p+1))} disabled={page===pages}>
            <ChevronRight className="w-3 h-3" />
          </button>
        </div>
      </div>

      {selectedId && <CustomerDetailModal customerId={selectedId} onClose={() => setSelectedId(null)} />}
    </div>
  )
}

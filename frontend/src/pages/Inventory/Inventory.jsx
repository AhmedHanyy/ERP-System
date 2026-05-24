import { useState, useEffect, useCallback } from 'react'
import { inventoryApi } from '@/services/api'
import { PageLoader, ErrorState, EmptyState } from '@/components/shared/States'
import StatusBadge from '@/components/shared/StatusBadge'
import { Search, Package, SlidersHorizontal, Plus, Minus, Edit3 } from 'lucide-react'
import toast from 'react-hot-toast'

const STATUS_FILTERS = ['', 'In Stock', 'Low Stock', 'Out of Stock']

export default function Inventory() {
  const [items,   setItems]   = useState([])
  const [summary, setSummary] = useState({})
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)
  const [search,  setSearch]  = useState('')
  const [status,  setStatus]  = useState('')
  const [adjusting, setAdjusting] = useState(null)  // product_id being adjusted
  const [adjQty, setAdjQty]   = useState(0)
  const [adjType, setAdjType] = useState('add')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [inv, sum] = await Promise.all([
        inventoryApi.list({ search, status }),
        inventoryApi.summary()
      ])
      setItems(inv.items)
      setSummary(sum)
    } catch { setError('Failed to load inventory') }
    finally { setLoading(false) }
  }, [search, status])

  useEffect(() => { load() }, [load])

  const handleAdjust = async (productId) => {
    try {
      await inventoryApi.adjust(productId, { type: adjType, quantity: parseInt(adjQty), reason: 'Manual adjustment' })
      toast.success('Inventory updated')
      setAdjusting(null)
      load()
    } catch { toast.error('Failed to adjust inventory') }
  }

  return (
    <div className="space-y-6">
      <div className="page-header">
        <h2 className="page-title">Inventory Management</h2>
        <p className="page-subtitle">Track stock levels and manage restocking</p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Total Products', value: summary.total,      color: 'bg-brand-500/10 text-brand-400' },
          { label: 'In Stock',       value: summary.in_stock,   color: 'bg-accent-emerald/10 text-accent-emerald' },
          { label: 'Low Stock',      value: summary.low_stock,  color: 'bg-accent-amber/10 text-accent-amber' },
          { label: 'Out of Stock',   value: summary.out_of_stock, color: 'bg-accent-rose/10 text-accent-rose' },
        ].map(s => (
          <div key={s.label} className="glass-card p-5">
            <p className={`text-2xl font-bold mb-1 ${s.color.split(' ')[1]}`}>{s.value ?? '—'}</p>
            <p className="text-xs text-text-muted">{s.label}</p>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="glass-card p-4 flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
          <input className="input pl-10" placeholder="Search products..." value={search}
            onChange={e => setSearch(e.target.value)} />
        </div>
        <select className="select w-44" value={status} onChange={e => setStatus(e.target.value)}>
          {STATUS_FILTERS.map(s => <option key={s} value={s}>{s || 'All Status'}</option>)}
        </select>
      </div>

      {/* Table */}
      <div className="glass-card overflow-hidden">
        {loading ? <div className="p-8"><PageLoader /></div> :
         error   ? <ErrorState message={error} onRetry={load} /> :
         items.length === 0 ? <EmptyState title="No products found" icon={Package} /> : (
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Product</th><th>SKU</th><th>Category</th>
                  <th>Stock</th><th>Reorder At</th><th>Location</th>
                  <th>Status</th><th>Adjust</th>
                </tr>
              </thead>
              <tbody>
                {items.map(item => (
                  <>
                    <tr key={item.id}>
                      <td className="font-medium">{item.name}</td>
                      <td><span className="font-mono text-xs text-text-secondary">{item.sku}</span></td>
                      <td className="text-text-secondary text-sm">{item.category_name || '—'}</td>
                      <td>
                        <div className="flex items-center gap-2">
                          <span className={`font-bold ${
                            item.inventory?.quantity === 0 ? 'text-accent-rose' :
                            item.inventory?.quantity <= item.inventory?.reorder_point ? 'text-accent-amber' :
                            'text-text-primary'
                          }`}>{item.inventory?.quantity}</span>
                          <span className="text-text-muted text-xs">units</span>
                        </div>
                      </td>
                      <td className="text-text-secondary text-sm">{item.inventory?.reorder_point}</td>
                      <td className="text-text-secondary text-xs font-mono">{item.inventory?.warehouse_location || '—'}</td>
                      <td><StatusBadge status={item.inventory?.status} /></td>
                      <td>
                        <button
                          className="p-1.5 rounded-lg hover:bg-bg-hover transition-colors text-text-muted hover:text-brand-400"
                          onClick={() => setAdjusting(adjusting === item.id ? null : item.id)}
                        >
                          <Edit3 className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                    {adjusting === item.id && (
                      <tr key={`adj-${item.id}`}>
                        <td colSpan={8} className="bg-bg-primary/50 p-4">
                          <div className="flex items-center gap-3 flex-wrap">
                            <select className="select w-32 py-1.5 text-xs" value={adjType} onChange={e => setAdjType(e.target.value)}>
                              <option value="add">Add Stock</option>
                              <option value="remove">Remove Stock</option>
                              <option value="set">Set Quantity</option>
                            </select>
                            <input
                              type="number" min="0" className="input w-24 py-1.5 text-xs" placeholder="Qty"
                              value={adjQty} onChange={e => setAdjQty(e.target.value)}
                            />
                            <button className="btn-primary text-xs py-1.5" onClick={() => handleAdjust(item.id)}>
                              Apply
                            </button>
                            <button className="btn-secondary text-xs py-1.5" onClick={() => setAdjusting(null)}>
                              Cancel
                            </button>
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

import { useState, useEffect } from 'react'
import { procurementApi, inventoryApi } from '@/services/api'
import { X, Search, Package, Save } from 'lucide-react'
import toast from 'react-hot-toast'

export default function CreateProcurementModal({ prefill, onClose, onSuccess }) {
  const [suppliers, setSuppliers] = useState([])
  const [products,  setProducts]  = useState([])
  const [loading,   setLoading]   = useState(true)

  const [formData, setFormData] = useState({
    supplier_id: prefill?.last_supplier_id || '',
    product_id:  prefill?.product_id || '',
    quantity:    prefill?.suggested_quantity || 10,
    unit_cost:   0,
    notes:       prefill ? `Auto-suggested based on low stock (${prefill.current_stock} remaining)` : ''
  })

  useEffect(() => {
    Promise.all([
      procurementApi.listSuppliers(),
      inventoryApi.list({ per_page: 100 })
    ]).then(([sData, pData]) => {
      setSuppliers(sData)
      setProducts(pData.items)
      
      // Update unit cost if product is selected
      if (formData.product_id) {
        const p = pData.items.find(x => x.id === formData.product_id)
        if (p) setFormData(prev => ({ ...prev, unit_cost: p.cost }))
      }
      
      setLoading(false)
    })
  }, [])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!formData.supplier_id || !formData.product_id) return toast.error('Please select both product and supplier')
    
    try {
      await procurementApi.createRequest(formData)
      toast.success('Procurement request created')
      onSuccess()
    } catch { toast.error('Failed to create request') }
  }

  const handleProductChange = (pid) => {
    const p = products.find(x => x.id === parseInt(pid))
    setFormData({
      ...formData,
      product_id: parseInt(pid),
      unit_cost: p ? p.cost : 0
    })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-bg-primary/80 backdrop-blur-sm">
      <div className="w-full max-w-lg bg-bg-secondary border border-border shadow-2xl rounded-2xl animate-fade-in overflow-hidden">
        <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-bg-hover/20">
          <div className="flex items-center gap-2">
            <Package className="w-5 h-5 text-brand-400" />
            <h2 className="text-lg font-semibold">New Procurement Request</h2>
          </div>
          <button onClick={onClose} className="p-2 rounded-xl hover:bg-bg-hover transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="space-y-1">
            <label className="text-xs font-bold text-text-muted uppercase">Select Product</label>
            <select
              className="select"
              value={formData.product_id}
              onChange={e => handleProductChange(e.target.value)}
              disabled={!!prefill}
            >
              <option value="">Choose product...</option>
              {products.map(p => <option key={p.id} value={p.id}>{p.name} ({p.sku})</option>)}
            </select>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-bold text-text-muted uppercase">Select Supplier</label>
            <select
              className="select"
              value={formData.supplier_id}
              onChange={e => setFormData({ ...formData, supplier_id: parseInt(e.target.value) })}
            >
              <option value="">Choose supplier...</option>
              {suppliers.map(s => <option key={s.id} value={s.id}>{s.name} · Lead: {s.lead_time_days}d</option>)}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-xs font-bold text-text-muted uppercase">Order Quantity</label>
              <input
                type="number" className="input" min="1"
                value={formData.quantity}
                onChange={e => setFormData({ ...formData, quantity: parseInt(e.target.value) || 1 })}
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-bold text-text-muted uppercase">Unit Cost (EGP)</label>
              <input
                type="number" className="input bg-bg-primary/50 text-text-muted" readOnly
                value={formData.unit_cost}
              />
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-bold text-text-muted uppercase">Notes / Instructions</label>
            <textarea
              className="input min-h-[80px] resize-none"
              placeholder="Any specific instructions for the supplier..."
              value={formData.notes}
              onChange={e => setFormData({ ...formData, notes: e.target.value })}
            />
          </div>

          <div className="pt-2">
            <div className="p-4 bg-bg-card rounded-xl border border-border mb-6">
              <div className="flex justify-between items-center">
                <span className="text-sm text-text-secondary">Estimated Total</span>
                <span className="text-xl font-bold text-text-primary">EGP {(formData.quantity * formData.unit_cost).toLocaleString()}</span>
              </div>
            </div>

            <div className="flex gap-3">
              <button type="button" onClick={onClose} className="btn-secondary flex-1">Cancel</button>
              <button type="submit" className="btn-primary flex-1">
                <Save className="w-4 h-4" /> Create Request
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  )
}
